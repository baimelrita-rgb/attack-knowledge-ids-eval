"""GNN lateral-movement channel: link prediction on the internal host graph (any port).

Encoder: learnable host embeddings + 2 GraphSAGE-mean layers over the undirected training host graph.
Decoder: MLP([h_src, h_dst, port_embedding]) -> logit that the (src, dst, port) triple occurs.
Trained on the unique triples of the training days (positives) against corrupted triples (negatives).
Edge surprise = -log sigmoid(logit). Training days are scored out-of-sample by cross-fitting (two models trained
on the two day-parity halves); all other days are scored by a model trained on all training days.

Usage: python gnn_edges.py EDGES_PARQUET HOST_HOUR_PARQUET OUT_PARQUET TRAIN_START TRAIN_END
Adds lm_gnn_max_out, lm_gnn_max_in, lm_gnn_n_surprising_out to the host-hour table.
"""
import sys

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

SEED = 42
DIM = 32
EPOCHS = 300
NEG_DST, NEG_PORT = 3, 2
MIN_PORT_FLOWS = 20


def port_bucket(port, vocab):
    if port in vocab:
        return port
    try:
        return "other_low" if int(port) < 1024 else "other_high"
    except ValueError:
        return "other_high"


class LinkGNN(nn.Module):
    def __init__(self, n_nodes, n_ports, adj):
        super().__init__()
        self.adj = adj
        self.emb = nn.Embedding(n_nodes, DIM)
        self.l1 = nn.Linear(2 * DIM, DIM)
        self.l2 = nn.Linear(2 * DIM, DIM)
        self.port = nn.Embedding(n_ports, 8)
        self.dec = nn.Sequential(nn.Linear(2 * DIM + 8, 32), nn.ReLU(), nn.Linear(32, 1))

    def encode(self):
        x = self.emb.weight
        h = torch.relu(self.l1(torch.cat([x, self.adj @ x], 1)))
        return self.l2(torch.cat([h, self.adj @ h], 1))

    def forward(self, s, d, p):
        h = self.encode()
        return self.dec(torch.cat([h[s], h[d], self.port(p)], 1)).squeeze(1)


def fit(train_edges, hosts, ports):
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    hi = {h: i for i, h in enumerate(hosts)}
    pi = {p: i for i, p in enumerate(ports)}
    tri = train_edges[["src", "dst", "pb"]].drop_duplicates()
    s = tri["src"].map(hi).to_numpy()
    d = tri["dst"].map(hi).to_numpy()
    p = tri["pb"].map(pi).to_numpy()
    n = len(hosts)
    a = torch.zeros(n, n)
    a[s, d] = 1.0
    a[d, s] = 1.0
    a += torch.eye(n)
    a = a / a.sum(1, keepdim=True)
    pos = set(zip(s, d, p))
    neg = []
    for si, di, pi_ in zip(s, d, p):
        for _ in range(NEG_DST):
            neg.append((si, rng.integers(n), pi_))
        for _ in range(NEG_PORT):
            neg.append((si, di, rng.integers(len(ports))))
    neg = [t for t in neg if t not in pos and t[0] != t[1]]
    S = torch.tensor(np.r_[s, [t[0] for t in neg]].astype(np.int64))
    D = torch.tensor(np.r_[d, [t[1] for t in neg]].astype(np.int64))
    P = torch.tensor(np.r_[p, [t[2] for t in neg]].astype(np.int64))
    Y = torch.tensor(np.r_[np.ones(len(s)), np.zeros(len(neg))], dtype=torch.float32)
    m = LinkGNN(n, len(ports), a)
    opt = torch.optim.Adam(m.parameters(), lr=0.01, weight_decay=1e-4)
    lossf = nn.BCEWithLogitsLoss()
    for _ in range(EPOCHS):
        opt.zero_grad()
        loss = lossf(m(S, D, P), Y)
        loss.backward()
        opt.step()
    m.eval()
    return m, hi, pi, float(loss)


def surprise(model, hi, pi, edges, unknown_value):
    known = edges["src"].isin(hi) & edges["dst"].isin(hi)
    out = np.full(len(edges), unknown_value, dtype=float)
    if known.any():
        e = edges[known]
        with torch.no_grad():
            z = model(torch.tensor(e["src"].map(hi).to_numpy()), torch.tensor(e["dst"].map(hi).to_numpy()),
                      torch.tensor(e["pb"].map(pi).to_numpy()))
            out[known.to_numpy()] = (-torch.nn.functional.logsigmoid(z)).numpy()
    return out


def main(edges_path, hh_path, out_path, tr0, tr1):
    e = pd.read_parquet(edges_path)
    tr_mask = (e["day"] >= tr0) & (e["day"] <= tr1)
    pc = e[tr_mask].groupby("dst_port")["n"].sum()
    vocab = set(pc[pc >= MIN_PORT_FLOWS].index)
    e["pb"] = e["dst_port"].map(lambda p: port_bucket(p, vocab))
    ports = sorted(set(e["pb"]))
    train = e[tr_mask]
    hosts = sorted(set(train["src"]) | set(train["dst"]))
    tdays = sorted(train["day"].unique())
    even = e["day"].isin(tdays[0::2])
    odd = e["day"].isin(tdays[1::2])

    full, hi, pi, loss_full = fit(train, hosts, ports)
    mA, hiA, piA, lossA = fit(e[even], hosts, ports)  # trained on even days, scores odd days
    mB, hiB, piB, lossB = fit(e[odd], hosts, ports)
    # value for edges with a host never seen in training: the largest out-of-sample surprise on training days
    s_odd = surprise(mA, hiA, piA, e[odd], np.nan)
    s_even = surprise(mB, hiB, piB, e[even], np.nan)
    unk = float(np.nanmax(np.r_[s_odd, s_even]))
    e["surprise"] = surprise(full, hi, pi, e, unk)
    e.loc[odd, "surprise"] = np.nan_to_num(s_odd, nan=unk)
    e.loc[even, "surprise"] = np.nan_to_num(s_even, nan=unk)
    t95 = float(np.percentile(e.loc[even | odd, "surprise"], 95))
    e["surprising"] = e["surprise"] > t95

    o = e.groupby(["src", "hour"]).agg(lm_gnn_max_out=("surprise", "max"), lm_gnn_n_surprising_out=("surprising", "sum"))
    o.index.names = ["host", "hour"]
    i = e.groupby(["dst", "hour"])["surprise"].max().rename("lm_gnn_max_in")
    i.index.names = ["host", "hour"]
    hh = pd.read_parquet(hh_path).set_index(["host", "hour"])
    hh = hh.join(o, how="left").join(i, how="left")
    new_cols = ["lm_gnn_max_out", "lm_gnn_n_surprising_out", "lm_gnn_max_in"]
    hh[new_cols] = hh[new_cols].fillna(0.0)
    hh.reset_index().to_parquet(out_path, index=False)
    e.to_parquet(out_path.replace(".parquet", "_edge_scores.parquet"), index=False)
    print({"hosts": len(hosts), "ports": len(ports), "train_triples": int(len(train[["src", "dst", "pb"]].drop_duplicates())),
           "final_bce": {"full": loss_full, "even": lossA, "odd": lossB}, "t95": t95, "unknown_value": unk})


if __name__ == "__main__":
    main(*sys.argv[1:])
