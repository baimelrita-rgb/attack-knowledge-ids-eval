"""ATLASv2 (development) Velox-lite seeds 0-4 (PLAN_SEEDS2.md item 3). Usage: python aggregate_atlas_seeds.py OUT_JSON OUT_MD"""
import json
import sys

import numpy as np

R = "/home/user/stt-gnn-/dep/data_raw/reach_runs/velox_lite/ATLASV2_EDR"


def main(out_json, out_md):
    runs = {k: json.load(open(f"{R}/seed{k}/eval.json")) for k in range(5)}
    res, L = {}, ["# ATLASv2 (development): Velox-lite seeds 0-4, lambda = 0.1\n",
                  "| Method | attacks@10 | attacks@25 | attacks@50 | GT nodes@50 | AUC |", "|---|---|---|---|---|---|"]
    for m in ["velox", "knowledge_only", "fused"]:
        row = []
        for key in ["attacks@10", "attacks@25", "attacks@50", "gt_nodes@50", "auc"]:
            v = [runs[k][m][key] for k in runs]
            res[f"{m}_{key}"] = {"values": v, "median": float(np.median(v)), "min": float(min(v)), "max": float(max(v))}
            f = ".3f" if key == "auc" else ".0f"
            row.append(f"{np.median(v):{f}} [{min(v):{f}}-{max(v):{f}}]")
        L.append(f"| {m} | " + " | ".join(row) + " |")
    L.append(f"\nPer seed fused attacks@10: {[runs[k]['fused']['attacks@10'] for k in runs]} of {runs[0]['attacks']}")
    json.dump(res, open(out_json, "w"), indent=1)
    open(out_md, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:])
