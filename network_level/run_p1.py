"""Pilot P1: ECOD tactic channels + conformal calibration + daily host ranking. See PILOT.md.

Usage: python run_p1.py FEATURES_PARQUET OUT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyod
from pyod.models.ecod import ECOD

TRAIN = ("2024-12-24", "2025-01-02")
CAL = ("2025-01-03", "2025-01-05")
TEST = ("2025-01-06", "2025-01-19")
CHANNELS = {
    "recon": ["recon_dst_ips", "recon_dst_ports", "recon_failed_share"],
    "c2": ["c2_new_ext_dsts", "c2_flows_new_ext", "c2_bytes_new_ext"],
    "lateral": ["lm_new_edges_out", "lm_new_edges_in", "lm_admin_flows"],
    "exfil": ["exf_bytes_out_ext", "exf_ratio_ext"],
}
CHANNELS["residual"] = sum(CHANNELS.values(), [])
LOG = ["recon_dst_ips", "recon_dst_ports", "c2_new_ext_dsts", "c2_flows_new_ext", "c2_bytes_new_ext",
       "lm_new_edges_out", "lm_new_edges_in", "lm_admin_flows", "exf_bytes_out_ext"]
K = 10
SEED = 42


def between(df, a, b):
    return df[(df["day"] >= a) & (df["day"] <= b)]


def rank_days(hd, col):
    hd = hd.copy()
    hd["rank"] = hd.groupby("day")[col].rank(ascending=False, method="first").astype(int)
    return hd


def evaluate(hd, active):
    pos = hd[hd["positive"]].copy()
    pos["active_hosts"] = pos["day"].map(active)
    return {
        "positive_host_days": int(len(pos)),
        "recall_at_10": float((pos["rank"] <= K).mean()),
        "recall_at_3": float((pos["rank"] <= 3).mean()),
        "recall_at_1": float((pos["rank"] <= 1).mean()),
        "mean_rank": float(pos["rank"].mean()),
        "hosts_in_top10_on_some_positive_day": sorted(pos.loc[pos["rank"] <= K, "host"].unique().tolist()),
    }, pos


def main(feat_path, out_dir):
    np.random.seed(SEED)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    f = pd.read_parquet(feat_path)
    f[LOG] = np.log1p(f[LOG])
    tr, ca, te = between(f, *TRAIN), between(f, *CAL), between(f, *TEST)
    assert tr["n_attack_flows"].sum() == 0 and ca["n_attack_flows"].sum() == 0

    pvals = {}
    for ch, cols in CHANNELS.items():
        m = ECOD().fit(tr[cols].to_numpy())
        cal = np.sort(m.decision_function(ca[cols].to_numpy()))
        s = m.decision_function(te[cols].to_numpy())
        n_ge = len(cal) - np.searchsorted(cal, s, side="left")
        pvals[ch] = (1 + n_ge) / (len(cal) + 1)
    P = pd.DataFrame(pvals, index=te.index)
    te = te.join(P.add_prefix("p_"))
    te["p_min"] = np.minimum(P.min(axis=1) * len(CHANNELS), 1.0)
    te["top_channel"] = P.idxmin(axis=1)
    te["hour_score"] = -np.log10(te["p_min"])
    te.to_parquet(out / "test_host_hours.parquet", index=False)

    hd = te.groupby(["day", "host"]).agg(
        score=("hour_score", "sum"), volume=("flows_out", "sum"), positive=("n_attack_flows", lambda s: (s > 0).any()),
        techniques=("techniques", lambda s: ",".join(sorted({t for x in s.dropna() for t in x.split(",")}))),
    ).reset_index()
    # channel of the host-day's best hour
    best = te.loc[te.groupby(["day", "host"])["hour_score"].idxmax(), ["day", "host", "top_channel", "hour_score"]]
    hd = hd.merge(best.rename(columns={"hour_score": "max_hour_score"}), on=["day", "host"])
    active = hd.groupby("day")["host"].nunique().to_dict()

    res = {"pyod": pyod.__version__, "pandas": pd.__version__, "seed": SEED, "n_train_host_hours": len(tr),
           "n_cal_host_hours": len(ca), "n_test_host_hours": len(te)}
    tables = []
    for name, col in [("model", "score"), ("volume", "volume")]:
        r = rank_days(hd, col)
        res[name], pos = evaluate(r, active)
        pos.insert(0, "method", name)
        tables.append(pos)
        r.to_csv(out / f"host_day_ranks_{name}.csv", index=False)
    pos_all = pd.concat(tables)
    pos_all.to_csv(out / "positive_host_days.csv", index=False)
    pos = pos_all[pos_all["method"] == "model"]
    res["random_expected_recall_at_10"] = float(np.mean([min(1.0, K / active[d]) for d in pos["day"]]))
    res["random_expected_recall_at_3"] = float(np.mean([min(1.0, 3 / active[d]) for d in pos["day"]]))
    res["active_hosts_per_test_day"] = {d: int(v) for d, v in active.items()}
    fp = rank_days(hd, "score")
    res["model_top10_slots_on_non_positive_hosts_per_day"] = (
        fp[(fp["rank"] <= K) & ~fp["positive"]].groupby("day").size().reindex(sorted(active), fill_value=0).to_dict())

    m, v = res["model"], res["volume"]
    res["gate"] = {
        "1_recall_at_10_ge_0.5": m["recall_at_10"] >= 0.5,
        "2_all_3_hosts_in_top10": set(m["hosts_in_top10_on_some_positive_day"]) >= {"172.16.1.3", "172.16.1.2", "172.16.0.2"},
        "3_model_gt_volume": m["recall_at_10"] > v["recall_at_10"],
    }
    res["gate"]["pass"] = all(res["gate"].values())
    (out / "results.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(pos_all[["method", "day", "host", "rank", "active_hosts", "score", "volume", "top_channel", "techniques"]].to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
