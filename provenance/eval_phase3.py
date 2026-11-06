"""Phase 3 evaluation (frozen methods of PREREG_PHASE3.md): Velox-lite, knowledge only, sum, interleave.

Usage: python eval_phase3.py SCORES_PARQUET GT_DIR OUT_JSON
"""
import json
import sys

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from reach_v2 import BUDGETS, evaluate, interleave


def main(scores, gt_dir, out):
    v = pd.read_parquet(scores).set_index("index_id")["score"]
    att = json.load(open(f"{gt_dir}/attacks.json"))
    gt = set().union(*[set(x["nids"]) for x in att.values()])
    pts = pd.read_parquet(f"{gt_dir}/semantic.parquet")["points"].reindex(v.index).fillna(0)
    pct = v.rank(pct=True)
    o = {"velox": list(v.sort_values(ascending=False).index[:2000]),
         "knowledge": list((pts + 1e-6 * pct).sort_values(ascending=False).index[:2000]),
         "sum": list((pct + 0.1 * pts).sort_values(ascending=False).index[:2000])}
    o["interleave"] = interleave(o["velox"], o["knowledge"])
    res = {m: evaluate(x, att, gt) for m, x in o.items()}
    y = v.index.isin(list(gt)).astype(int)
    res["_meta"] = {"attacks": len(att), "gt": len(gt), "gt_in_population": int(y.sum()), "population": len(v),
                    "velox_auc": float(roc_auc_score(y, v)) if 0 < y.sum() < len(y) else None,
                    "velox_ap": float(average_precision_score(y, v)) if y.sum() else None,
                    "processes_with_points": int((pts > 0).sum())}
    json.dump(res, open(out, "w"), indent=1)
    print(res["_meta"])
    for m in o:
        print(f"{m:11s}", " ".join(f"{res[m][f'attacks@{k}']}/{res[m][f'gt@{k}']}" for k in BUDGETS))


if __name__ == "__main__":
    main(*sys.argv[1:])
