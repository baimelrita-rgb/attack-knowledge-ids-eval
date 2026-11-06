"""A4 (PLAN_ROUND4.md): Holm correction over the five mechanism tests. Usage: python holm.py MECH_JSON OUT_JSON"""
import json
import sys


def main(path, out):
    r = json.load(open(path))
    p = {"H2 coverage vs gain": r["H2_coverage_vs_gain"][1], "H3 learned AUC vs gain": r["H3_auc_vs_gain"][1],
         "process share vs gain": r["procshare_vs_gain"][1], "H4 Windows process-centric": r["H4"]["win_process_centric"]["wilcoxon_p"],
         "H4 other": r["H4"]["other"]["wilcoxon_p"]}
    items = sorted(p.items(), key=lambda kv: kv[1])
    m, adj, run = len(items), {}, 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        adj[k] = {"p": v, "p_holm": run}
    json.dump(adj, open(out, "w"), indent=1)
    for k, v in adj.items():
        print(f"{k:28s} p={v['p']:.4f} holm={v['p_holm']:.4f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
