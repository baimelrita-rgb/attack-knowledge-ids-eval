"""Aggregate seed round 2 (PLAN_SEEDS2.md).

Usage: python aggregate_seeds2.py OUT_JSON OUT_MD
Reads data_raw/seeds2/seed<s>/{p3_optc,p3_unraveled}/results.json and e1/results.json, plus the stored originals.
"""
import json
import sys
from pathlib import Path

import numpy as np

RAW = Path(__file__).resolve().parent.parent / "data_raw/seeds2"
SEEDS = [42, 0, 1, 2, 3, 4]
P3M = ["model_p3", "channels_only", "ablation_gnn_only", "ecod_pooled", "iforest_pooled", "autoencoder_pooled"]
E1M = ["ours", "ae_error", "shap_ae", "shap_if", "occlusion_ae", "random"]


def s(v):
    return {"values": v, "median": float(np.median(v)), "min": float(min(v)), "max": float(max(v))}


def fmt(x):
    return f"{x['median']:.3f} [{x['min']:.3f}-{x['max']:.3f}]"


def main(out_json, out_md):
    have = [k for k in SEEDS if (RAW / f"seed{k}/e1/results.json").exists()]
    res, L = {"seeds": have}, [f"# Seed round 2 (seeds {have}; original seed 42 re-run)\n"]
    for ds in ["optc", "unraveled"]:
        L += [f"\n## RQ1 {ds}: host-day AUC and host-day detection at 5 alerts/day, median [min-max]\n",
              "| Method | host-day AUC | detection@5 |", "|---|---|---|"]
        for m in P3M:
            a = [json.load(open(RAW / f"seed{k}/p3_{ds}/results.json"))["methods"][m] for k in have]
            res[f"p3_{ds}_{m}"] = {"auc_host_day": s([x["auc_host_day"] for x in a]),
                                   "det5": s([x["host_day_detection_at_5"] for x in a])}
            L.append(f"| {m} | {fmt(res[f'p3_{ds}_{m}']['auc_host_day'])} | {fmt(res[f'p3_{ds}_{m}']['det5'])} |")
        best = []
        for k in have:
            r = json.load(open(RAW / f"seed{k}/p3_{ds}/results.json"))["methods"]
            best.append(max(P3M, key=lambda m: r[m]["auc_host_day"]))
        res[f"p3_{ds}_best_per_seed"] = best
        L.append(f"\nBest method per seed: {best}\n")
    e1 = {k: json.load(open(RAW / f"seed{k}/e1/results.json")) for k in have}
    for ds in ["dedale", "unraveled", "optc", "pooled"]:
        L += [f"\n## RQ3 attribution accuracy, {ds} (n = {e1[have[0]]['accuracy'][ds]['n']})\n",
              "| Method | accuracy |", "|---|---|"]
        for m in E1M:
            res[f"e1_{ds}_{m}"] = s([e1[k]["accuracy"][ds][m] for k in have])
            L.append(f"| {m} | {fmt(res[f'e1_{ds}_{m}'])} |")
        bestm = [max(E1M[:-1], key=lambda m: e1[k]["accuracy"][ds][m]) for k in have]
        res[f"e1_{ds}_best_per_seed"] = bestm
        L.append(f"\nBest explainer per seed: {bestm}\n")
    res["e1_gate_per_seed"] = {k: e1[k]["gate"] for k in have}
    L += ["\n## RQ3 gate per seed (descriptive)\n", "| seed | G1 | G2 | G3 | pass |", "|---|---|---|---|---|"]
    for k in have:
        g = e1[k]["gate"]
        L.append(f"| {k} | {g['1_pooled_beats_all_and_ci_low_gt_0']} | {g['2_beats_all_on_2_of_3_datasets']} | "
                 f"{g['3_faithfulness_ge_ae_error_and_shap_ae']} | {g['pass']} |")
    json.dump(res, open(out_json, "w"), indent=1)
    open(out_md, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:])
