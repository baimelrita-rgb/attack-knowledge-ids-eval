"""REACH v2: knowledge suspicion propagated along provenance edges + interleaved fusion with a learned detector.

propagate(db, points, bounds, gamma, depth):
    points: semantic points per process (semantic.py). In the test period, every event whose source carries
    suspicion s passes gamma * s to its destination (connection, file or process); repeated `depth` times
    (a node keeps the max of what it receives and its own points). Edge direction as stored by PIDSMaker
    (source = acting process).
interleave(a, b): alternate the two rankings (a first), skipping nodes already taken.

Usage (dev evaluation): python reach_v2.py DATASET_KEY DB SCORES_PARQUET GT_DIR OUT_JSON [GAMMA DEPTH]
"""
import json
import sys

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, "/home/user/ext/PIDSMaker")
from pidsmaker.config.config import DATASET_DEFAULT_CONFIG  # noqa: E402

from velox_lite import day_bounds_ns, where  # noqa: E402

BUDGETS = [10, 25, 50, 100, 250, 500]


def propagate(db, points, bounds, gamma=0.5, depth=2):
    con = psycopg2.connect(database=db, host="localhost", user="postgres", password="postgres")
    cur = con.cursor()
    s = points[points > 0].astype(float).to_dict()
    frontier = dict(s)
    for _ in range(depth):
        if not frontier:
            break
        ids = list(frontier)
        cur.execute(f"select src_index_id, dst_index_id from event_table where ({where(bounds)}) "
                    f"and src_index_id = any(%s)", ([str(i) for i in ids],))
        rows = cur.fetchall()
        nxt = {}
        for a, b in rows:
            a, b = int(a), int(b)
            v = gamma * frontier.get(a, 0.0)
            if v > s.get(b, 0.0) + 1e-12:
                s[b] = v
                nxt[b] = max(nxt.get(b, 0.0), v)
        frontier = nxt
    con.close()
    return pd.Series(s)


def interleave(a, b):
    out, seen = [], set()
    ia, ib = iter(a), iter(b)
    turn = 0
    while True:
        src = ia if turn % 2 == 0 else ib
        for n in src:
            if n not in seen:
                seen.add(n)
                out.append(n)
                break
        else:
            other = ib if src is ia else ia
            rest = [n for n in other if n not in seen]
            return out + rest
        turn += 1
        if len(out) >= 2000:
            return out


def evaluate(order, att, gt):
    r = {}
    for k in BUDGETS:
        sel = set(order[:k])
        r[f"attacks@{k}"] = sum(1 for v in att.values() if sel & set(v["nids"]))
        r[f"gt@{k}"] = len(sel & gt)
    return r


def main(key, db, scores, gt_dir, out, gamma="0.5", depth="2"):
    cfgd = DATASET_DEFAULT_CONFIG[key]
    te = day_bounds_ns(cfgd["test_dates"], cfgd.get("timezone", "UTC"))
    v = pd.read_parquet(scores).set_index("index_id")["score"] if scores.endswith(".parquet") else None
    att = json.load(open(f"{gt_dir}/attacks.json"))
    gt = set().union(*[set(x["nids"]) for x in att.values()])
    pts = pd.read_parquet(f"{gt_dir}/semantic.parquet")["points"]
    prop = propagate(db, pts, te, float(gamma), int(depth)).reindex(v.index).fillna(0)
    raw = pts.reindex(v.index).fillna(0)
    pct = v.rank(pct=True)
    orders = {
        "velox": list(v.sort_values(ascending=False).index[:2000]),
        "knowledge": list((raw + 1e-6 * pct).sort_values(ascending=False).index[:2000]),
        "knowledge_prop": list((prop + 1e-6 * pct).sort_values(ascending=False).index[:2000]),
        "fused_sum": list((pct + 0.1 * raw).sort_values(ascending=False).index[:2000]),
        "fused_sum_prop": list((pct + 0.1 * prop).sort_values(ascending=False).index[:2000]),
    }
    orders["interleave"] = interleave(orders["velox"], orders["knowledge"])
    orders["interleave_prop"] = interleave(orders["velox"], orders["knowledge_prop"])
    res = {m: evaluate(o, att, gt) for m, o in orders.items()}
    res["_meta"] = {"gamma": float(gamma), "depth": int(depth), "propagated_nodes": int((prop > 0).sum()),
                    "gt": len(gt), "gt_with_prop": int(sum(1 for n in gt if prop.get(n, 0) > 0))}
    json.dump(res, open(out, "w"), indent=1)
    print(res["_meta"])
    for m in orders:
        print(f"{m:16s}", " ".join(f"{res[m][f'attacks@{k}']}/{res[m][f'gt@{k}']}" for k in BUDGETS))


if __name__ == "__main__":
    main(*sys.argv[1:])
