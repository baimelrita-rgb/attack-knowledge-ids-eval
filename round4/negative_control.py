"""A2 (PLAN_ROUND4.md): content-free rule control. The observed rule points are re-assigned to random processes of the
test population (same multiset of point values, same number of marked processes), 1,000 draws per dataset and seed.
Metric: gain = fused minus learned ground-truth nodes within 50 alerts (fusion = percentile + 0.1 x points).
Usage: python negative_control.py OUT_JSON OUT_MD [DATASETS...]"""
import json
import sys

import numpy as np
import pandas as pd

RAW = "/home/user/stt-gnn-/dep/data_raw"
DS = ["ATLASV2_EDR", "OPTC_H501", "OPTC_H051", "OPTC_H201", "CADETS_E3", "THEIA_E3", "CLEARSCOPE_E3"]
K, DRAWS, LAM = 50, 1000, 0.1


def top_fused(pct, order, pts_idx, pts_val):
    """indices of the top-K fused nodes; only nodes with points can move above their learned rank."""
    marked = np.zeros(len(pct), bool)
    marked[pts_idx] = True
    rest = order[~marked[order]][:K]
    cand = np.r_[pts_idx, rest]
    sc = np.r_[pct[pts_idx] + LAM * pts_val, pct[rest]]
    return cand[np.argsort(-sc, kind="stable")[:K]]


def run(ds, seed, rng):
    v = pd.read_parquet(f"{RAW}/reach_runs/velox_lite/{ds}/seed{seed}/node_scores.parquet")
    ids = v["index_id"].to_numpy()
    pct = v["score"].rank(pct=True).to_numpy()
    order = np.argsort(-v["score"].to_numpy(), kind="stable")
    att = json.load(open(f"{RAW}/reach_gt/{ds}/attacks.json"))
    gt = set().union(*[set(a["nids"]) for a in att.values()])
    isgt = np.isin(ids, list(gt))
    kind = pd.read_parquet(f"{RAW}/reach_gt/{ds}/nodes.parquet", columns=["index_id", "kind"]).set_index("index_id")["kind"]
    isproc = (kind.reindex(ids) == "process").to_numpy()
    pts = pd.read_parquet(f"{RAW}/reach_gt/{ds}/semantic.parquet")["points"].reindex(ids).fillna(0).to_numpy()
    pidx = np.flatnonzero(pts > 0)
    learned = int(isgt[order[:K]].sum())
    obs = int(isgt[top_fused(pct, order, pidx, pts[pidx])].sum()) - learned
    procs = np.flatnonzero(isproc)
    ctrl = []
    for _ in range(DRAWS if len(pidx) else 1):
        r = rng.choice(procs, size=len(pidx), replace=False) if len(pidx) else pidx
        ctrl.append(int(isgt[top_fused(pct, order, r, rng.permutation(pts[pidx]))].sum()) - learned)
    ctrl = np.array(ctrl)
    return {"observed_gain": obs, "control_median": float(np.median(ctrl)), "control_p95": float(np.percentile(ctrl, 95)),
            "p_one_sided": float((1 + (ctrl >= obs).sum()) / (1 + len(ctrl))) if len(pidx) else 1.0, "marked": int(len(pidx))}


def main(out_json, out_md, *ds):
    rng = np.random.default_rng(0)
    res = {}
    for d in (ds or DS):
        res[d] = {}
        for s in range(5):
            res[d][s] = run(d, s, rng)
            print(d, s, res[d][s], flush=True)
    L = ["# A2 negative control: content-free rules (1,000 draws per dataset and seed)\n",
         "| Dataset | observed gain (median over seeds) | control gain median / 95th pct (median over seeds) | one-sided p per seed |",
         "|---|---|---|---|"]
    for d, r in res.items():
        L.append(f"| {d} | {np.median([x['observed_gain'] for x in r.values()]):+.0f} | "
                 f"{np.median([x['control_median'] for x in r.values()]):+.1f} / {np.median([x['control_p95'] for x in r.values()]):+.1f} | "
                 + ", ".join(f"{x['p_one_sided']:.3f}" for x in r.values()) + " |")
    json.dump(res, open(out_json, "w"), indent=1)
    open(out_md, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:])
