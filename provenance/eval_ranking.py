"""Evaluate node rankings: Velox (or Velox-lite) scores, knowledge only, and REACH fused (pre-registered lambda).

Usage: python eval_ranking.py SCORES GT_DIR OUT_JSON [LAMBDA]
SCORES: a parquet with index_id, score (velox_lite.py) or a PIDSMaker edge_scores pickle (node score = max edge loss).
Ranked population = nodes with at least one test event. Metrics: attacks detected and ground-truth nodes found at
budgets 10 / 25 / 50 / 100 / 250 / 500, AUC and AP of the node ranking.
"""
import json
import os
import sys

os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

BUDGETS = [10, 25, 50, 100, 250, 500]


def load_scores(path):
    if path.endswith(".parquet"):
        d = pd.read_parquet(path)
        return d.set_index("index_id")["score"]
    import torch
    e = torch.load(path, map_location="cpu")
    return pd.concat([e[["srcnode", "loss"]].rename(columns={"srcnode": "n"}),
                      e[["dstnode", "loss"]].rename(columns={"dstnode": "n"})]).groupby("n")["loss"].max()


def metrics(rank, att, gt):
    out = {}
    order = rank.sort_values(ascending=False).index
    for b in BUDGETS:
        sel = set(order[:b])
        out[f"attacks@{b}"] = sum(1 for v in att.values() if sel & set(v["nids"]))
        out[f"gt_nodes@{b}"] = len(sel & gt)
    y = rank.index.isin(list(gt)).astype(int)
    out["auc"] = float(roc_auc_score(y, rank.to_numpy())) if 0 < y.sum() < len(y) else None
    out["ap"] = float(average_precision_score(y, rank.to_numpy())) if y.sum() else None
    out["gt_in_population"] = int(y.sum())
    out["population"] = int(len(y))
    return out


def main(scores_path, gt_dir, out, lam="0.1"):
    s = load_scores(scores_path)
    att = json.load(open(os.path.join(gt_dir, "attacks.json")))
    gt = set().union(*[set(v["nids"]) for v in att.values()])
    pts = pd.read_parquet(os.path.join(gt_dir, "semantic.parquet"))["points"].reindex(s.index).fillna(0)
    pct = s.rank(pct=True)
    res = {"lambda": float(lam), "attacks": len(att), "gt_nodes": len(gt),
           "velox": metrics(s, att, gt),
           "knowledge_only": metrics(pts + 1e-6 * pct, att, gt),
           "fused": metrics(pct + float(lam) * pts, att, gt)}
    json.dump(res, open(out, "w"), indent=1)
    for k in ["velox", "knowledge_only", "fused"]:
        m = res[k]
        print(f"{k:15s} AUC {m['auc']:.3f} AP {m['ap']:.4f} | attacks@10/25/50/100: "
              f"{m['attacks@10']}/{m['attacks@25']}/{m['attacks@50']}/{m['attacks@100']} | gt@50: {m['gt_nodes@50']} gt@100: {m['gt_nodes@100']}")


if __name__ == "__main__":
    main(*sys.argv[1:])
