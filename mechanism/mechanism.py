"""RQ2 mechanism analysis (PLAN_MECHANISM.md). Usage: python mechanism.py OUT_JSON OUT_MD"""
import itertools
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

RAW = "/home/user/stt-gnn-/dep/data_raw"
DS = ["ATLASV2_EDR", "OPTC_H501", "OPTC_H051", "OPTC_H201", "CADETS_E3", "THEIA_E3", "CLEARSCOPE_E3"]
WIN_PC = {"ATLASV2_EDR", "OPTC_H051"}  # Windows, process-centric ground truth
K = 50


def load_gt(ds):
    att = json.load(open(f"{RAW}/reach_gt/{ds}/attacks.json"))
    kind = pd.read_parquet(f"{RAW}/reach_gt/{ds}/nodes.parquet", columns=["index_id", "kind"]).set_index("index_id")["kind"]
    pts = pd.read_parquet(f"{RAW}/reach_gt/{ds}/semantic.parquet")["points"]
    return att, kind, pts


def orders(ds, seed, pts):
    v = pd.read_parquet(f"{RAW}/reach_runs/velox_lite/{ds}/seed{seed}/node_scores.parquet").set_index("index_id")["score"]
    pct = v.rank(pct=True)
    p = pts.reindex(v.index).fillna(0)
    return {"learned": v.sort_values(ascending=False).index.to_numpy(),
            "knowledge": (p + 1e-6 * pct).sort_values(ascending=False).index.to_numpy(),
            "fused": (pct + 0.1 * p).sort_values(ascending=False).index.to_numpy()}, v.index


def exact_spearman(x, y):
    rho = spearmanr(x, y).correlation
    perms = [spearmanr(x, list(p)).correlation for p in itertools.permutations(y)]
    return float(rho), float(np.mean([abs(r) >= abs(rho) - 1e-12 for r in perms]))


def main(out_json, out_md):
    res, L = {"per_dataset": {}, "per_attack": []}, ["# RQ2 mechanism analysis (exploratory; PLAN_MECHANISM.md)\n"]
    for ds in DS:
        att, kind, pts = load_gt(ds)
        gt = set().union(*[set(a["nids"]) for a in att.values()])
        r = {"gt_nodes": len(gt)}
        per_seed = []
        for s in range(5):
            o, pop = orders(ds, s, pts)
            popset = set(pop)
            gtp = {n for n in gt if n in popset and kind.get(n) == "process"}
            row = {}
            for m, ordr in o.items():
                top = set(ordr[:K])
                row[f"{m}_gt@{K}"] = len(top & gt)
                row[f"{m}_gtproc@{K}"] = len(top & gtp)
                pos = pd.Series(np.arange(1, len(ordr) + 1), index=ordr)
                for a, v in att.items():
                    ids = [n for n in v["nids"] if n in popset]
                    first = int(pos.reindex(ids).min()) if ids else len(ordr)
                    res["per_attack"].append({"dataset": ds, "seed": s, "attack": a, "method": m, "first_rank": first})
            procs = kind.reindex(list(pop))
            procs = procs[procs == "process"].index
            row["coverage_gt_proc"] = float(np.mean([pts.get(n, 0) > 0 for n in gtp])) if gtp else 0.0
            row["selectivity"] = float((pts.reindex(procs).fillna(0) > 0).mean())
            row["gt_proc_share"] = len(gtp) / max(1, len([n for n in gt if n in popset]))
            v = pd.read_parquet(f"{RAW}/reach_runs/velox_lite/{ds}/seed{s}/node_scores.parquet").set_index("index_id")["score"]
            y = v.index.isin(list(gt))
            from sklearn.metrics import roc_auc_score
            row["learned_auc"] = float(roc_auc_score(y, v.to_numpy())) if 0 < y.sum() < len(y) else float("nan")
            per_seed.append(row)
        df = pd.DataFrame(per_seed)
        r.update({c: float(df[c].median()) for c in df.columns})
        r["gain_gt@50"] = r[f"fused_gt@{K}"] - r[f"learned_gt@{K}"]
        res["per_dataset"][ds] = r
        print(ds, {k: round(v, 3) for k, v in r.items()}, flush=True)
    # CARBANAKv2: coverage and selectivity only (no learned detector)
    att, kind, pts = load_gt("CARBANAKV2_EDR")
    gt = set().union(*[set(a["nids"]) for a in att.values()])
    gtp = [n for n in gt if kind.get(n) == "process"]
    procs = kind[kind == "process"].index
    res["carbanakv2"] = {"coverage_gt_proc": float(np.mean([pts.get(n, 0) > 0 for n in gtp])),
                         "selectivity": float((pts.reindex(procs).fillna(0) > 0).mean()), "gt_proc_share": len(gtp) / len(gt)}
    pdx = pd.DataFrame(res["per_dataset"]).T
    res["H2_coverage_vs_gain"] = exact_spearman(list(pdx["coverage_gt_proc"]), list(pdx["gain_gt@50"]))
    res["H3_auc_vs_gain"] = exact_spearman(list(pdx["learned_auc"]), list(pdx["gain_gt@50"]))
    res["procshare_vs_gain"] = exact_spearman(list(pdx["gt_proc_share"]), list(pdx["gain_gt@50"]))
    # H4: per attack, median first rank over seeds; paired fused vs learned
    pa = pd.DataFrame(res["per_attack"]).groupby(["dataset", "attack", "method"])["first_rank"].median().unstack()
    pa["group"] = ["win_process_centric" if d in WIN_PC else "other" for d in pa.index.get_level_values(0)]
    res["H4"] = {}
    for g, sub in pa.groupby("group"):
        d = (sub["fused"] - sub["learned"]).to_numpy()
        try:
            p = float(wilcoxon(sub["fused"], sub["learned"]).pvalue) if np.any(d != 0) else 1.0
        except ValueError:
            p = float("nan")
        res["H4"][g] = {"n_attacks": int(len(sub)), "fused_better": int((d < 0).sum()), "learned_better": int((d > 0).sum()),
                        "ties": int((d == 0).sum()), "median_first_rank_fused": float(sub["fused"].median()),
                        "median_first_rank_learned": float(sub["learned"].median()),
                        "median_first_rank_knowledge": float(sub["knowledge"].median()), "wilcoxon_p": p}
    res["per_attack_medians"] = {f"{a}|{b}": {m: float(pa.loc[(a, b), m]) for m in ["learned", "knowledge", "fused"]}
                                 for a, b in pa.index}
    # report
    L += ["## Per dataset (median over five seeds; ground-truth nodes within 50 alerts)\n",
          "| Dataset | GT process share | rule coverage of GT processes | selectivity | learned AUC | learned | knowledge | fused | gain | GT processes@50 learned / knowledge / fused |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for ds, r in res["per_dataset"].items():
        L.append(f"| {ds} | {r['gt_proc_share']:.2f} | {r['coverage_gt_proc']:.2f} | {r['selectivity']:.4f} | {r['learned_auc']:.3f} | "
                 f"{r['learned_gt@50']:.0f} | {r['knowledge_gt@50']:.0f} | {r['fused_gt@50']:.0f} | {r['gain_gt@50']:+.0f} | "
                 f"{r['learned_gtproc@50']:.0f} / {r['knowledge_gtproc@50']:.0f} / {r['fused_gtproc@50']:.0f} |")
    c = res["carbanakv2"]
    L.append(f"| CARBANAKV2_EDR (rules only) | {c['gt_proc_share']:.2f} | {c['coverage_gt_proc']:.2f} | {c['selectivity']:.4f} | - | - | - | - | - | - |")
    L += ["\n## Correlations over the seven datasets (exact permutation p, two-sided)\n",
          f"- H2 coverage of GT processes vs gain: rho = {res['H2_coverage_vs_gain'][0]:.2f}, p = {res['H2_coverage_vs_gain'][1]:.3f}",
          f"- H3 learned AUC vs gain: rho = {res['H3_auc_vs_gain'][0]:.2f}, p = {res['H3_auc_vs_gain'][1]:.3f}",
          f"- GT process share vs gain: rho = {res['procshare_vs_gain'][0]:.2f}, p = {res['procshare_vs_gain'][1]:.3f}",
          "\n## H4: alerts needed to reach each attack (median over seeds)\n",
          "| Group | attacks | fused better | learned better | ties | median rank fused | learned | knowledge | Wilcoxon p |",
          "|---|---|---|---|---|---|---|---|---|"]
    for g, h in res["H4"].items():
        L.append(f"| {g} | {h['n_attacks']} | {h['fused_better']} | {h['learned_better']} | {h['ties']} | {h['median_first_rank_fused']:.0f} | "
                 f"{h['median_first_rank_learned']:.0f} | {h['median_first_rank_knowledge']:.0f} | {h['wilcoxon_p']:.3f} |")
    L += ["\n### Per attack\n", "| Dataset | attack | learned | knowledge | fused |", "|---|---|---|---|---|"]
    for k, v in res["per_attack_medians"].items():
        a, b = k.split("|")
        L.append(f"| {a} | {b} | {v['learned']:.0f} | {v['knowledge']:.0f} | {v['fused']:.0f} |")
    res.pop("per_attack")
    json.dump(res, open(out_json, "w"), indent=1)
    open(out_md, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:])
