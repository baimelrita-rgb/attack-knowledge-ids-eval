"""Pilot P2: per-host one-sided ECOD tactic channels + conformal calibration + max-hour daily score.
See PILOT_P2.md.

Usage: python run_p2.py FEATURES_PARQUET OUT_DIR TRAIN_START TRAIN_END CAL_START CAL_END TEST_START TEST_END

Per-host one-sided ECOD: for each feature, the host's own training hours give an empirical upper-tail
probability p_f(x) = (1 + #{train hours of this host with value >= x}) / (n + 1); hosts with fewer than
MIN_HOST_HOURS training hours use all training host-hours instead. Channel score = sum of -log10 p_f over the
channel's features (ECOD's aggregation, right tail only). Channel scores are calibrated into conformal p-values
on the calibration host-hours (pooled over hosts).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

CHANNELS = {
    "recon": ["recon_dst_ips", "recon_dst_ports", "recon_failed_share"],
    "c2": ["c2_new_ext_dsts", "c2_flows_new_ext", "c2_bytes_new_ext"],
    "lateral": ["lm_new_edges_out", "lm_new_edges_in", "lm_admin_flows"],
    "exfil": ["exf_bytes_out_ext", "exf_ratio_ext"],
}
CHANNELS["residual"] = sum(CHANNELS.values(), [])
FEATS = CHANNELS["residual"]
MIN_HOST_HOURS = 24
SEED = 42
N_BOOT = 1000
BUDGET = 5  # host-hour alerts per day


def tail_logp(train_vals, x):
    """-log10 of the one-sided empirical upper-tail p-value of each x against train_vals."""
    t = np.sort(train_vals)
    n_ge = len(t) - np.searchsorted(t, x, side="left")
    return -np.log10((1 + n_ge) / (len(t) + 1))


def channel_scores(train, frame):
    """Per-host one-sided ECOD channel scores for every row of frame."""
    out = pd.DataFrame(0.0, index=frame.index, columns=list(CHANNELS))
    counts = train.groupby("host").size()
    for host, rows in frame.groupby("host"):
        ref = train[train["host"] == host] if counts.get(host, 0) >= MIN_HOST_HOURS else train
        lp = pd.DataFrame({f: tail_logp(ref[f].to_numpy(), rows[f].to_numpy()) for f in FEATS}, index=rows.index)
        for ch, cols in CHANNELS.items():
            out.loc[rows.index, ch] = lp[cols].sum(axis=1)
    return out


def conformal(cal_scores, scores):
    c = np.sort(cal_scores)
    n_ge = len(c) - np.searchsorted(c, scores, side="left")
    return (1 + n_ge) / (len(c) + 1)


def auc(df, col):
    return float(roc_auc_score(df["positive"], df[col])) if df["positive"].nunique() == 2 else float("nan")


def main(feat_path, out_dir, tr0, tr1, ca0, ca1, te0, te1):
    rng = np.random.default_rng(SEED)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    f = pd.read_parquet(feat_path)
    f = f.reset_index(drop=True)
    tr = f[(f["day"] >= tr0) & (f["day"] <= tr1)]
    ca = f[(f["day"] >= ca0) & (f["day"] <= ca1)]
    te = f[(f["day"] >= te0) & (f["day"] <= te1)].copy()
    assert tr["n_attack_flows"].sum() == 0 and ca["n_attack_flows"].sum() == 0

    # Cross-fitted calibration (dev round 2): training days split into two halves by day parity; host profiles
    # built on one half score the other half. Calibration set = these out-of-sample training scores plus the
    # calibration days scored against all training days.
    tdays = sorted(tr["day"].unique())
    half = tr["day"].isin(tdays[0::2])
    s_cf = pd.concat([channel_scores(tr[half], tr[~half]), channel_scores(tr[~half], tr[half])])
    s_ca, s_te = channel_scores(tr, ca), channel_scores(tr, te)
    s_ca = pd.concat([s_cf, s_ca])
    P = pd.DataFrame({ch: conformal(s_ca[ch].to_numpy(), s_te[ch].to_numpy()) for ch in CHANNELS}, index=te.index)
    te = te.join(P.add_prefix("p_"))
    te["p_min"] = np.minimum(P.min(axis=1) * len(CHANNELS), 1.0)
    te["top_channel"] = P.idxmin(axis=1)
    te["hour_score"] = -np.log10(te["p_min"])
    te.to_parquet(out / "test_host_hours.parquet", index=False)

    hd = te.groupby(["day", "host"]).agg(
        max_hour=("hour_score", "max"), mean_hour=("hour_score", "mean"), volume=("flows_out", "sum"),
        positive=("n_attack_flows", lambda s: bool((s > 0).any())),
        techniques=("techniques", lambda s: ",".join(sorted({t for x in s.dropna() for t in x.split(",")}))),
    ).reset_index()
    hd["score"] = hd["max_hour"] + 1e-3 * hd["mean_hour"]
    best = te.loc[te.groupby(["day", "host"])["hour_score"].idxmax(), ["day", "host", "top_channel"]]
    hd = hd.merge(best, on=["day", "host"])
    # host-prior baseline: same model, host's mean daily score over the calibration days (constant per host)
    ca2 = ca.copy()
    Pc = pd.DataFrame({ch: conformal(s_ca[ch].to_numpy(), s_ca.loc[ca.index, ch].to_numpy()) for ch in CHANNELS},
                      index=ca.index)
    ca2["hs"] = -np.log10(np.minimum(Pc.min(axis=1) * len(CHANNELS), 1.0))
    prior = ca2.groupby(["day", "host"])["hs"].max().groupby("host").mean()
    hd["host_prior"] = hd["host"].map(prior).fillna(0.0)
    hd["rank"] = hd.groupby("day")["score"].rank(ascending=False, method="first").astype(int)
    hd.to_csv(out / "host_days.csv", index=False)

    res = {"seed": SEED, "split": {"train": [tr0, tr1], "cal": [ca0, ca1], "test": [te0, te1]},
           "n_train_host_hours": len(tr), "n_cal_host_hours": len(ca), "n_calibration_scores": len(s_ca), "n_test_host_hours": len(te),
           "n_test_host_days": len(hd), "n_positive_host_days": int(hd["positive"].sum())}
    res["auc"] = {c: auc(hd, c) for c in ["score", "volume", "host_prior"]}
    days = hd["day"].unique()
    boots = []
    for _ in range(N_BOOT):
        pick = rng.choice(days, len(days), replace=True)
        b = pd.concat([hd[hd["day"] == d] for d in pick])
        if b["positive"].nunique() == 2:
            boots.append(auc(b, "score"))
    res["auc_score_ci95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    pos = hd[hd["positive"]]
    active = hd.groupby("day")["host"].nunique()
    res["recall_at_5"] = float((pos["rank"] <= 5).mean())
    res["random_expected_recall_at_5"] = float(np.mean([min(1.0, 5 / active[d]) for d in pos["day"]]))
    within = {}
    for host, g in hd[hd["host"].isin(pos["host"].unique())].groupby("host"):
        n_pos, n_neg = int(g["positive"].sum()), int((~g["positive"]).sum())
        within[host] = {"pos_days": n_pos, "neg_days": n_neg,
                        "auc": auc(g, "score") if (n_pos >= 3 and n_neg >= 3) else None,
                        "median_rank_pos": float(g.loc[g["positive"], "rank"].median()),
                        "median_rank_neg": float(g.loc[~g["positive"], "rank"].median()) if n_neg else None}
    res["within_host"] = within
    elig = [v["auc"] for v in within.values() if v["auc"] is not None]
    # Hour-level evaluation under a daily alert budget B (primary, dev round 3).
    te["positive"] = te["n_attack_flows"] > 0
    te["volume_h"] = te["flows_out"]
    te["host_prior_h"] = te["host"].map(prior).fillna(0.0)
    hour_res = {}
    for name, col in [("model", "hour_score"), ("volume", "volume_h"), ("host_prior", "host_prior_h")]:
        r = te.groupby("day")[col].rank(ascending=False, method="first")
        top = r <= BUDGET
        det = te.assign(top=top)[te["positive"]].groupby(["day", "host"])["top"].any()
        hour_res[name] = {"host_day_detection_at_B": float(det.mean()),
                          "attack_hour_recall_at_B": float(top[te["positive"]].mean()),
                          "false_alerts_per_day": float((top & ~te["positive"]).groupby(te["day"]).sum().mean()),
                          "auc_host_hour": auc(te, col)}
    n_day = te.groupby("day").size()
    pos_h = te[te["positive"]]
    # random: probability that at least one of the host-day's attack hours is among B random picks of the day
    rand = []
    for (d, h), g in pos_h.groupby(["day", "host"]):
        n, k = n_day[d], len(g)
        miss = 1.0
        for i in range(min(BUDGET, n)):
            miss *= max(0.0, (n - k - i) / (n - i))
        rand.append(1 - miss)
    hour_res["random_expected_host_day_detection_at_B"] = float(np.mean(rand))
    hour_res["budget_B_per_day"] = BUDGET
    hour_res["positive_host_days"] = int(len(rand))
    hour_res["positive_host_hours"] = int(len(pos_h))
    wh = {}
    for host, g in te[te["host"].isin(pos_h["host"].unique())].groupby("host"):
        wh[host] = {"attack_hours": int(g["positive"].sum()), "other_hours": int((~g["positive"]).sum()),
                    "auc": auc(g, "hour_score") if g["positive"].sum() >= 3 else None}
    hour_res["within_host_hour_auc"] = wh
    res["hour_level"] = hour_res
    hm, elig_h = hour_res["model"], [v["auc"] for v in wh.values() if v["auc"] is not None]
    res["gate_hour_level"] = {
        "1_detection_ge_0.5_and_ge_2x_random": hm["host_day_detection_at_B"] >= 0.5
        and hm["host_day_detection_at_B"] >= 2 * hour_res["random_expected_host_day_detection_at_B"],
        "2_detection_gt_volume_and_host_prior": hm["host_day_detection_at_B"] > hour_res["volume"]["host_day_detection_at_B"]
        and hm["host_day_detection_at_B"] > hour_res["host_prior"]["host_day_detection_at_B"],
        "3_majority_within_host_hour_auc_gt_0.5": bool(elig_h) and sum(a > 0.5 for a in elig_h) > len(elig_h) / 2,
    }
    res["gate_hour_level"]["pass"] = all(res["gate_hour_level"].values())
    res["gate"] = {
        "1_auc_ge_0.70_and_ci_low_gt_0.5": res["auc"]["score"] >= 0.70 and res["auc_score_ci95"][0] > 0.5,
        "2_auc_gt_volume_and_host_prior": res["auc"]["score"] > res["auc"]["volume"] and res["auc"]["score"] > res["auc"]["host_prior"],
        "3_majority_within_host_auc_gt_0.5": bool(elig) and sum(a > 0.5 for a in elig) > len(elig) / 2,
    }
    res["gate"]["pass"] = all(res["gate"].values())  # host-day gate (secondary since dev round 3)
    res["channel_of_best_hour_on_positive_host_days"] = pos["top_channel"].value_counts().to_dict()
    (out / "results.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
