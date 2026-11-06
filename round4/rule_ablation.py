"""A3 (PLAN_ROUND4.md): leave-one-family-out ablation of the Windows rule prior on CARBANAKv2.

Usage:
  python rule_ablation.py components DB OUT_PARQUET   # per-family points from the database (once)
  python rule_ablation.py evaluate COMPONENTS_PARQUET OUT_JSON OUT_MD
Families (by ATT&CK technique of the node rules, plus the two process-creation edge rules of semantic.py):
  execution (T1059.*), proxy/LOLBin execution (T1218.*, T1047, T1053.005, T1197, T1105), discovery (T1033, T1087,
  T1016, T1082, T1057), other node rules (T1547.001, T1490, T1569.002, T1021.001, T1003.001, T1566.001),
  document-parent edge (+2), interpreter-to-LOLBin edge (+1).
Metric per seed: fused (percentile + 0.1 x points) ground-truth nodes within 50 alerts and alerts to the attack.
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/stt-gnn-/dep/reach")
RAW = "/home/user/stt-gnn-/dep/data_raw"
DS = "CARBANAKV2_EDR"
FAMILY = {"T1059": "execution", "T1218": "proxy_lolbin", "T1047": "proxy_lolbin", "T1053": "proxy_lolbin",
          "T1197": "proxy_lolbin", "T1105": "proxy_lolbin", "T1033": "discovery", "T1087": "discovery",
          "T1016": "discovery", "T1082": "discovery", "T1057": "discovery"}


def components(db, out):
    import psycopg2
    import semantic as S
    from l2_explain import RULES
    con = psycopg2.connect(database=db, host="localhost", user="postgres", password="postgres")
    procs = pd.read_sql("select index_id, path, cmd from subject_node_table", con)
    procs["index_id"] = procs["index_id"].astype("int64")
    text = procs["path"].fillna("") + " " + procs["cmd"].fillna("")
    comp = pd.DataFrame(0.0, index=procs["index_id"], columns=["execution", "proxy_lolbin", "discovery", "other_node",
                                                              "doc_parent_edge", "interp_lolbin_edge"])
    for p, tech in RULES:
        fam = FAMILY.get(tech.split(".")[0], "other_node")
        comp[fam] += text.str.contains(p, regex=True).to_numpy().astype(float)
    ops = ",".join(f"'{o}'" for o in S.CREATE_OPS["edr"])
    ev = pd.read_sql(f"select distinct src_index_id, dst_index_id from event_table where operation in ({ops})", con).astype("int64")
    path = procs.set_index("index_id")["path"].fillna("")
    ev = ev[ev["src_index_id"].isin(path.index) & ev["dst_index_id"].isin(path.index)]
    par, chi = path.reindex(ev["src_index_id"]).to_numpy(), path.reindex(ev["dst_index_id"]).to_numpy()
    doc = [bool(S.DOC_PARENTS.search(a) and (S.INTERPRETERS.search(b) or S.LOLBINS.search(b))) for a, b in zip(par, chi)]
    il = [bool(S.INTERPRETERS.search(a) and S.LOLBINS.search(b)) for a, b in zip(par, chi)]
    for mask, w, col in [(doc, 2.0, "doc_parent_edge"), (il, 1.0, "interp_lolbin_edge")]:
        sel = ev[mask]
        for c in ["src_index_id", "dst_index_id"]:
            add = sel.groupby(c).size().clip(upper=1) * w
            comp[col] = comp[col].add(add, fill_value=0).reindex(comp.index).fillna(comp[col])
    con.close()
    stored = pd.read_parquet(f"{RAW}/reach_gt/{DS}/semantic.parquet")["points"]
    total = comp.sum(axis=1)
    diff = float((total.reindex(stored.index).fillna(0) - stored).abs().max())
    print("max |sum of families - stored points| =", diff)
    comp.reset_index().to_parquet(out, index=False)


def fused_eval(scores, pts, gt, att):
    pct = scores.rank(pct=True)
    p = pts.reindex(scores.index).fillna(0)
    order = (pct + 0.1 * p).sort_values(ascending=False).index.to_numpy()
    pos = pd.Series(np.arange(1, len(order) + 1), index=order)
    first = min(int(pos.reindex([n for n in a["nids"] if n in pos.index]).min()) for a in att.values())
    return int(len(set(order[:50]) & gt)), first


def evaluate(comp_path, out_json, out_md):
    comp = pd.read_parquet(comp_path).set_index("index_id")
    att = json.load(open(f"{RAW}/reach_gt/{DS}/attacks.json"))
    gt = set().union(*[set(a["nids"]) for a in att.values()])
    variants = {"all rules": list(comp.columns)}
    for c in comp.columns:
        variants[f"without {c}"] = [x for x in comp.columns if x != c]
    res = {}
    for s in range(5):
        sc = pd.read_parquet(f"{RAW}/reach_runs/velox_lite/{DS}/seed{s}/node_scores.parquet").set_index("index_id")["score"]
        order = sc.sort_values(ascending=False).index.to_numpy()
        lpos = pd.Series(np.arange(1, len(order) + 1), index=order)
        learned = (int(len(set(order[:50]) & gt)), min(int(lpos.reindex([n for n in a["nids"] if n in lpos.index]).min()) for a in att.values()))
        res.setdefault("learned only", []).append(learned)
        for name, cols in variants.items():
            res.setdefault(name, []).append(fused_eval(sc, comp[cols].sum(axis=1), gt, att))
    L = ["# A3 rule ablation on CARBANAKv2 (fused = percentile + 0.1 x points; medians over seeds 0-4)\n",
         "| Variant | GT nodes within 50 alerts | alerts to reach the attack |", "|---|---|---|"]
    out = {}
    for k, v in res.items():
        g, f = [x[0] for x in v], [x[1] for x in v]
        out[k] = {"gt@50": g, "first_rank": f}
        L.append(f"| {k} | {np.median(g):.0f} [{min(g)}-{max(g)}] | {np.median(f):.0f} [{min(f)}-{max(f)}] |")
    json.dump(out, open(out_json, "w"), indent=1)
    open(out_md, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    {"components": components, "evaluate": evaluate}[sys.argv[1]](*sys.argv[2:])
