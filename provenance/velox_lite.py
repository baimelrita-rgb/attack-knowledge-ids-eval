"""Velox-lite: a disk-light re-implementation of PIDSMaker's Velox for the CPU environment.

Same ingredients as PIDSMaker `velox` (orthrus_non_snooped with encoder "none"):
- node features = word2vec over node labels (PIDSMaker's own `tokenize_label`; subject: type, path, cmd;
  file: type, path; netflow: type, remote ip, remote port), trained on nodes seen on the train dates only,
  + one-hot node type;
- a linear layer (node_out_dim 128), src/dst projections (x2), dropout 0.5, linear + ReLU, linear -> edge type;
- loss = cross-entropy of the event type; node score = max loss over its test events (as source or destination).
Differences, forced by the disk/CPU limits:
- features are computed on the fly, never stored per event;
- word2vec epochs 10 (PIDSMaker: 50); emb 32;
- training on at most MAX_TRAIN events sampled uniformly from the train dates, 3 epochs, Adam lr 1e-3.

Usage: python velox_lite.py DATASET_KEY DB OUT_DIR [SEED]
Writes OUT_DIR/node_scores.parquet (index_id, score, n_test_events) and OUT_DIR/meta.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import pytz
import torch
import torch.nn as nn
from gensim.models import Word2Vec

sys.path.insert(0, "/home/user/ext/PIDSMaker")
from pidsmaker.config.config import DATASET_DEFAULT_CONFIG  # noqa: E402
from pidsmaker.utils.utils import tokenize_label  # noqa: E402

EMB = 32
W2V_EPOCHS = 10
MAX_TRAIN = 4_000_000
EPOCHS = 3
BATCH = 8192
CHUNK = 2_000_000


def day_bounds_ns(dates, tz):
    z = pytz.timezone(tz)
    out = []
    for d in dates:
        start = z.localize(pd.Timestamp(d).to_pydatetime())
        out.append((int(start.timestamp() * 1e9), int((start + pd.Timedelta(days=1)).timestamp() * 1e9)))
    return out


def where(bounds):
    return " or ".join(f"(timestamp_rec >= {a} and timestamp_rec < {b})" for a, b in bounds)


def main(key, db, out, seed="0"):
    seed = int(seed)
    torch.manual_seed(seed)
    np.random.seed(seed)
    t0 = time.time()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cfgd = DATASET_DEFAULT_CONFIG[key]
    tz = cfgd.get("timezone", "UTC")
    tr, va, te = (day_bounds_ns(cfgd[k], tz) for k in ["train_dates", "val_dates", "test_dates"])
    con = psycopg2.connect(database=db, host="localhost", user="postgres", password="postgres")

    sub = pd.read_sql("select index_id, path, cmd from subject_node_table", con)
    fil = pd.read_sql("select index_id, path from file_node_table", con)
    net = pd.read_sql("select index_id, dst_addr, dst_port from netflow_node_table", con)
    labels, ntype = {}, {}
    for r in sub.itertuples(index=False):
        labels[int(r.index_id)] = tokenize_label(f"{r.path} {r.cmd}", "subject"); ntype[int(r.index_id)] = 0
    for r in fil.itertuples(index=False):
        labels[int(r.index_id)] = tokenize_label(f"{r.path}", "file"); ntype[int(r.index_id)] = 1
    for r in net.itertuples(index=False):
        labels[int(r.index_id)] = tokenize_label(f"{r.dst_addr} {r.dst_port}", "netflow"); ntype[int(r.index_id)] = 2
    n_nodes = max(labels) + 1
    print("nodes", len(labels), time.time() - t0, flush=True)

    ops = pd.read_sql("select distinct operation from event_table", con)["operation"].sort_values().tolist()
    op_id = {o: i for i, o in enumerate(ops)}

    # training events (sample) and the nodes seen on train dates
    cnt = pd.read_sql(f"select count(*) from event_table where {where(tr)}", con).iloc[0, 0]
    frac = min(1.0, MAX_TRAIN / max(cnt, 1))
    ev = pd.read_sql(f"select src_index_id, dst_index_id, operation from event_table where ({where(tr)}) and random() < {frac}", con)
    ev = ev.astype({"src_index_id": "int64", "dst_index_id": "int64"})
    train_nodes = pd.unique(np.r_[ev["src_index_id"].to_numpy(), ev["dst_index_id"].to_numpy()])
    print("train events", cnt, "sampled", len(ev), "train nodes", len(train_nodes), time.time() - t0, flush=True)

    w2v = Word2Vec([labels[n] for n in train_nodes if n in labels and labels[n]], vector_size=EMB, window=5, min_count=1,
                   sg=1, negative=5, epochs=W2V_EPOCHS, workers=3, seed=seed)
    X = np.zeros((n_nodes, EMB + 3), dtype=np.float32)
    for n, toks in labels.items():
        vs = [w2v.wv[t] for t in toks if t in w2v.wv]
        if vs:
            X[n, :EMB] = np.mean(vs, axis=0)
        X[n, EMB + ntype[n]] = 1.0
    X = torch.from_numpy(X)
    print("word2vec done", time.time() - t0, flush=True)

    class M(nn.Module):
        def __init__(self, d_in, n_cls):
            super().__init__()
            self.lin = nn.Linear(d_in, 128)
            self.ps, self.pd = nn.Linear(128, 256), nn.Linear(128, 256)
            self.mlp = nn.Sequential(nn.Dropout(0.5), nn.Linear(512, 256), nn.ReLU(), nn.Linear(256, n_cls))

        def forward(self, s, d):
            return self.mlp(torch.cat([self.ps(self.lin(X[s])), self.pd(self.lin(X[d]))], 1))

    model = M(EMB + 3, len(ops))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    S = torch.from_numpy(ev["src_index_id"].to_numpy())
    D = torch.from_numpy(ev["dst_index_id"].to_numpy())
    Y = torch.from_numpy(ev["operation"].map(op_id).to_numpy())
    lossf = nn.CrossEntropyLoss()
    for ep in range(EPOCHS):
        perm = torch.randperm(len(S))
        tot = 0.0
        for i in range(0, len(S), BATCH):
            b = perm[i:i + BATCH]
            opt.zero_grad()
            loss = lossf(model(S[b], D[b]), Y[b])
            loss.backward()
            opt.step()
            tot += float(loss) * len(b)
        print(f"epoch {ep} loss {tot / len(S):.4f}", time.time() - t0, flush=True)
    model.eval()

    # stream test events, node score = max per-event loss
    score = np.zeros(n_nodes, dtype=np.float32)
    n_ev = np.zeros(n_nodes, dtype=np.int64)
    cur = con.cursor(name="test_stream")
    cur.itersize = CHUNK
    cur.execute(f"select src_index_id, dst_index_id, operation from event_table where {where(te)}")
    lossn = nn.CrossEntropyLoss(reduction="none")
    total = 0
    while True:
        rows = cur.fetchmany(CHUNK)
        if not rows:
            break
        a = np.array([[int(r[0]), int(r[1]), op_id[r[2]]] for r in rows], dtype=np.int64)
        total += len(a)
        with torch.no_grad():
            for i in range(0, len(a), 65536):
                c = torch.from_numpy(a[i:i + 65536])
                l = lossn(model(c[:, 0], c[:, 1]), c[:, 2]).numpy()
                np.maximum.at(score, c[:, 0].numpy(), l)
                np.maximum.at(score, c[:, 1].numpy(), l)
                np.add.at(n_ev, c[:, 0].numpy(), 1)
                np.add.at(n_ev, c[:, 1].numpy(), 1)
        print("test events", total, time.time() - t0, flush=True)
    idx = np.nonzero(n_ev)[0]
    pd.DataFrame({"index_id": idx, "score": score[idx], "n_test_events": n_ev[idx]}).to_parquet(out / "node_scores.parquet", index=False)
    json.dump({"dataset": key, "seed": seed, "train_events": int(cnt), "sampled": int(len(ev)), "test_events": int(total),
               "ops": ops, "emb": EMB, "w2v_epochs": W2V_EPOCHS, "epochs": EPOCHS, "seconds": time.time() - t0},
              open(out / "meta.json", "w"), indent=1)
    print("done", time.time() - t0, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
