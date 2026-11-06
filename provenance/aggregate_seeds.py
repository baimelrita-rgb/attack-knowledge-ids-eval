"""Aggregate Velox-lite seeds 0-4 (PLAN_SEEDS.md): per dataset, median [min-max] over seeds, and the gate quantities per seed.

Usage: python aggregate_seeds.py OUT_JSON OUT_MD
Reads: reach_runs/velox_lite/<DATASET>/seed<k>/{eval.json | eval_phase3.json}
"""
import glob
import json
import os
import sys

import numpy as np

R = "/home/user/stt-gnn-/dep/data_raw/reach_runs/velox_lite"
OPTC = ["OPTC_H501", "OPTC_H051", "OPTC_H201"]
E3 = ["CLEARSCOPE_E3", "CADETS_E3", "THEIA_E3"]
BUDGETS = [10, 25, 50, 100]
# eval.json (OpTC): keys velox / knowledge_only / fused, with attacks@k and gt_nodes@k.
# eval_phase3.json (E3): keys velox / knowledge / sum / interleave, with attacks@k and gt@k.
OPTC_METHODS = {"velox": "learned", "knowledge_only": "knowledge", "fused": "sum"}
E3_METHODS = {"velox": "learned", "knowledge": "knowledge", "sum": "sum", "interleave": "interleave"}


def load(ds):
    out = {}
    for k in range(5):
        p = "eval.json" if ds in OPTC else "eval_phase3.json"
        f = f"{R}/{ds}/seed{k}/{p}"
        if os.path.exists(f):
            out[k] = json.load(open(f))
    return out


def get(r, method, kind, b, optc):
    key = f"attacks@{b}" if kind == "attacks" else (f"gt_nodes@{b}" if optc else f"gt@{b}")
    return r[method][key]


def summarise(vals):
    return {"median": float(np.median(vals)), "min": float(np.min(vals)), "max": float(np.max(vals)), "n": len(vals)}


def main(out_json, out_md):
    res, lines = {}, []
    for group, names, methods, optc in [("OpTC (Windows)", OPTC, OPTC_METHODS, True), ("DARPA TC E3", E3, E3_METHODS, False)]:
        lines.append(f"\n## {group}: median [min-max] over seeds\n")
        for ds in names:
            runs = load(ds)
            if not runs:
                continue
            res[ds] = {"seeds": sorted(runs)}
            lines.append(f"### {ds} (seeds {sorted(runs)})\n")
            lines.append("| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |")
            lines.append("|---|---|---|---|---|---|---|")
            for mk, name in methods.items():
                row = []
                for kind, b in [("attacks", 10), ("attacks", 25), ("attacks", 50), ("attacks", 100), ("gt", 50), ("gt", 100)]:
                    v = [get(r, mk, kind, b, optc) for r in runs.values()]
                    s = summarise(v)
                    res[ds][f"{name}_{kind}@{b}"] = s
                    row.append(f"{s['median']:.0f} [{s['min']:.0f}-{s['max']:.0f}]")
                lines.append(f"| {name} | " + " | ".join(row) + " |")
            auc = [r["velox"]["auc"] if optc else r["_meta"]["velox_auc"] for r in runs.values()]
            res[ds]["velox_auc"] = summarise(auc)
            lines.append(f"\nVelox-lite AUC: median {np.median(auc):.3f} [{min(auc):.3f}-{max(auc):.3f}]\n")
    # per-seed gate quantities
    gates = {}
    for k in range(5):
        e3 = [load(d).get(k) for d in E3]
        if all(x is not None for x in e3):
            tot = lambda m, kind, b: sum(get(x, m, kind, b, False) for x in e3)  # noqa: E731
            g1 = tot("interleave", "attacks", 25) > tot("velox", "attacks", 25)
            g2 = tot("interleave", "gt", 50) > tot("velox", "gt", 50)
            g3 = tot("interleave", "attacks", 25) >= tot("knowledge", "attacks", 25)
            gates[f"E3_seed{k}"] = {"G1": bool(g1), "G2": bool(g2), "G3": bool(g3), "pass": bool(g1 and g2 and g3),
                                    "pooled_attacks@50": {m: tot(m, "attacks", 50) for m in E3_METHODS}}
        op = [load(d).get(k) for d in OPTC]
        if all(x is not None for x in op):
            ok1 = all(get(x, "fused", "attacks", b, True) >= get(x, "velox", "attacks", b, True) for x in op for b in (25, 50))
            more = any(get(x, "fused", "attacks", b, True) > get(x, "velox", "attacks", b, True) for x in op for b in (25, 50))
            pooled = lambda m: sum(get(x, m, "gt", 50, True) for x in op)  # noqa: E731
            gates[f"OpTC_seed{k}"] = {"G1": bool(ok1 and more), "G2": bool(pooled("fused") > pooled("velox")),
                                      "G3": bool(pooled("fused") >= pooled("knowledge_only")),
                                      "pooled_gt@50": {m: pooled(m) for m in OPTC_METHODS}}
    res["gates_per_seed"] = gates
    lines.append("\n## Gate quantities per seed (descriptive; the pre-registered decision is seed 0)\n")
    lines.append("| Phase / seed | G1 | G2 | G3 | pooled values |")
    lines.append("|---|---|---|---|---|")
    for k, v in gates.items():
        pooled = v.get("pooled_attacks@50") or v.get("pooled_gt@50")
        lines.append(f"| {k} | {v['G1']} | {v['G2']} | {v['G3']} | {pooled} |")
    json.dump(res, open(out_json, "w"), indent=1)
    open(out_md, "w").write("# Velox-lite over seeds 0-4\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:])
