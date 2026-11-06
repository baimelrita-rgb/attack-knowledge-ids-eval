"""A1 (PLAN_ROUND4.md): CARBANAKv2 uncontaminated Windows check. Predictions fixed in advance:
P1: fused finds more ground-truth nodes within 50 alerts than the learned detector (median over seeds 0-4);
P2: fused reaches the attack in fewer alerts than the learned detector in at least 4 of 5 seeds.
Also reports the A2 negative control (content-free rules) on CARBANAKv2.
Usage: python carbanak_eval.py OUT_JSON OUT_MD"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/stt-gnn-/dep/round4")
import negative_control as NC  # noqa: E402

RAW = "/home/user/stt-gnn-/dep/data_raw"
DS = "CARBANAKV2_EDR"


def main(out_json, out_md):
    att = json.load(open(f"{RAW}/reach_gt/{DS}/attacks.json"))
    gt = set().union(*[set(a["nids"]) for a in att.values()])
    pts = pd.read_parquet(f"{RAW}/reach_gt/{DS}/semantic.parquet")["points"]
    rows, rng = [], np.random.default_rng(0)
    for s in range(5):
        v = pd.read_parquet(f"{RAW}/reach_runs/velox_lite/{DS}/seed{s}/node_scores.parquet").set_index("index_id")["score"]
        pct = v.rank(pct=True)
        p = pts.reindex(v.index).fillna(0)
        r = {"seed": s}
        for m, sc in [("learned", v), ("knowledge", p + 1e-6 * pct), ("fused", pct + 0.1 * p)]:
            order = sc.sort_values(ascending=False).index.to_numpy()
            pos = pd.Series(np.arange(1, len(order) + 1), index=order)
            r[f"{m}_gt@50"] = int(len(set(order[:50]) & gt))
            r[f"{m}_gt@10"] = int(len(set(order[:10]) & gt))
            r[f"{m}_first_rank"] = int(pos.reindex([n for n in gt if n in pos.index]).min())
        y = v.index.isin(list(gt))
        from sklearn.metrics import roc_auc_score
        r["learned_auc"] = float(roc_auc_score(y, v.to_numpy()))
        nc = NC.run(DS, s, rng)
        r["nc_observed_gain"], r["nc_control_median"], r["nc_p"] = nc["observed_gain"], nc["control_median"], nc["p_one_sided"]
        rows.append(r)
        print(r, flush=True)
    df = pd.DataFrame(rows)
    p1 = bool(df["fused_gt@50"].median() > df["learned_gt@50"].median())
    p2_count = int((df["fused_first_rank"] < df["learned_first_rank"]).sum())
    res = {"per_seed": rows, "P1": p1, "P2_seeds": p2_count, "P2": p2_count >= 4}
    json.dump(res, open(out_json, "w"), indent=1)
    L = ["# A1: CARBANAKv2 (rules fixed before its ground truth was opened), Velox-lite seeds 0-4\n",
         "| Seed | learned AUC | GT@50 learned / knowledge / fused | alerts to attack: learned / fused | negative control: gain vs control median (p) |",
         "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['seed']} | {r['learned_auc']:.3f} | {r['learned_gt@50']} / {r['knowledge_gt@50']} / {r['fused_gt@50']} | "
                 f"{r['learned_first_rank']} / {r['fused_first_rank']} | {r['nc_observed_gain']:+d} vs {r['nc_control_median']:+.0f} ({r['nc_p']:.3f}) |")
    L += ["", f"P1 (fused > learned GT nodes within 50 alerts, median over seeds): {'holds' if p1 else 'does not hold'} "
          f"({df['fused_gt@50'].median():.0f} vs {df['learned_gt@50'].median():.0f}).",
          f"P2 (fused reaches the attack first in >= 4 of 5 seeds): {'holds' if res['P2'] else 'does not hold'} ({p2_count} of 5)."]
    open(out_md, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:])
