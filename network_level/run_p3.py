"""P3: tactic-channel detector (per-host one-sided ECOD + cross-fitted conformal) with the GNN lateral channel,
rare-destination/beacon C2 features and a volume channel, evaluated against a fixed baseline suite.

Usage: python run_p3.py HOST_HOUR_GNN_PARQUET OUT_DIR TRAIN_START TRAIN_END CAL_START CAL_END TEST_START TEST_END
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyod.models.ecod import ECOD
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

SEED = 42
BUDGET = 5
MIN_HOST_HOURS = 24

P2_CHANNELS = {
    "recon": ["recon_dst_ips", "recon_dst_ports", "recon_failed_share"],
    "c2": ["c2_new_ext_dsts", "c2_flows_new_ext", "c2_bytes_new_ext"],
    "lateral": ["lm_new_edges_out", "lm_new_edges_in", "lm_admin_flows"],
    "exfil": ["exf_bytes_out_ext", "exf_ratio_ext"],
}
P2_CHANNELS["residual"] = sum(P2_CHANNELS.values(), [])
P3_CHANNELS = {
    "recon": ["recon_dst_ips", "recon_dst_ports", "recon_failed_share"],
    "c2": ["c2_new_ext_dsts", "c2_flows_new_ext", "c2_bytes_new_ext", "c2_rare_flows", "c2_rare_dsts", "c2_beacon"],
    "lateral": ["lm_gnn_max_out", "lm_gnn_max_in", "lm_gnn_n_surprising_out", "lm_new_edges_out", "lm_new_edges_in"],
    "exfil": ["exf_bytes_out_ext", "exf_ratio_ext"],
    "volume": ["flows_out", "vol_bytes_out", "vol_bytes_in", "vol_flows_in"],
}
P3_CHANNELS["residual"] = sum(P3_CHANNELS.values(), []) + ["lm_admin_flows"]
ALL = P3_CHANNELS["residual"]
RATIO = {"recon_failed_share", "exf_ratio_ext", "c2_beacon"}


# ---------- tactic-channel model ----------
def tail_logp(ref, x):
    t = np.sort(ref)
    return -np.log10((1 + len(t) - np.searchsorted(t, x, side="left")) / (len(t) + 1))


AGG = "max"  # dev round P3-3: channel = most extreme feature (was sum, as in ECOD)
DUAL = False  # dev round P3-2 tried True (worse on Unraveled); kept False: a value must be rare for the host AND for the population (min of the two -log p)


def channel_scores(train, frame, channels, dual=None):
    dual = DUAL if dual is None else dual
    feats = sorted({f for c in channels.values() for f in c})
    out = pd.DataFrame(0.0, index=frame.index, columns=list(channels))
    counts = train.groupby("host").size()
    for host, rows in frame.groupby("host"):
        ref = train[train["host"] == host] if counts.get(host, 0) >= MIN_HOST_HOURS else train
        lp = pd.DataFrame({f: tail_logp(ref[f].to_numpy(), rows[f].to_numpy()) for f in feats}, index=rows.index)
        if dual:
            lp = np.minimum(lp, pd.DataFrame({f: tail_logp(train[f].to_numpy(), rows[f].to_numpy()) for f in feats},
                                             index=rows.index))
        for ch, cols in channels.items():
            # dev round P3-4: ties at the maximum broken by the channel mean
            out.loc[rows.index, ch] = (lp[cols].max(axis=1) + 0.01 * lp[cols].mean(axis=1)) if AGG == "max" \
                else lp[cols].sum(axis=1)
    return out


def conformal(cal, s):
    c = np.sort(cal)
    return (1 + len(c) - np.searchsorted(c, s, side="left")) / (len(c) + 1)


def channel_model(tr, ca, te, channels, dual=None):
    tdays = sorted(tr["day"].unique())
    half = tr["day"].isin(tdays[0::2])
    s_cal = pd.concat([channel_scores(tr[half], tr[~half], channels, dual), channel_scores(tr[~half], tr[half], channels, dual),
                       channel_scores(tr, ca, channels, dual)])
    s_te = channel_scores(tr, te, channels, dual)
    P = pd.DataFrame({ch: conformal(s_cal[ch].to_numpy(), s_te[ch].to_numpy()) for ch in channels}, index=te.index)
    score = -np.log10(np.minimum(P.min(axis=1) * len(channels), 1.0))
    return score, P.idxmin(axis=1), P, len(s_cal)


# ---------- pooled baselines ----------
def prep(df):
    x = df[ALL].astype(float).copy()
    for c in ALL:
        if c not in RATIO:
            x[c] = np.log1p(x[c].clip(lower=0))
    return x.to_numpy()


def pooled_baselines(tr, te):
    Xtr, Xte = prep(tr), prep(te)
    out = {}
    out["ecod_pooled"] = ECOD().fit(Xtr).decision_function(Xte)
    out["iforest_pooled"] = -IsolationForest(n_estimators=200, random_state=SEED).fit(Xtr).score_samples(Xte)
    sc = StandardScaler().fit(Xtr)
    ae = MLPRegressor(hidden_layer_sizes=(32, 8, 32), max_iter=300, random_state=SEED).fit(sc.transform(Xtr), sc.transform(Xtr))
    out["autoencoder_pooled"] = ((ae.predict(sc.transform(Xte)) - sc.transform(Xte)) ** 2).mean(axis=1)
    return out


# ---------- evaluation ----------
def auc(y, s):
    return float(roc_auc_score(y, s)) if len(set(y)) == 2 else float("nan")


def evaluate(te, col):
    pos = te["n_attack_flows"] > 0
    r = te.groupby("day")[col].rank(ascending=False, method="first")
    top = r <= BUDGET
    det = top[pos].groupby([te.loc[pos, "day"], te.loc[pos, "host"]]).any()
    hd = te.groupby(["day", "host"]).agg(s=(col, "max"), y=("n_attack_flows", lambda v: bool((v > 0).any())))
    return {"host_day_detection_at_5": float(det.mean()), "attack_hour_recall_at_5": float(top[pos].mean()),
            "false_alerts_per_day": float((top & ~pos).groupby(te["day"]).sum().mean()),
            "auc_host_hour": auc(pos, te[col]), "auc_host_day": auc(hd["y"], hd["s"])}


def random_detection(te):
    n_day = te.groupby("day").size()
    vals = []
    for (d, h), g in te[te["n_attack_flows"] > 0].groupby(["day", "host"]):
        n, k, miss = n_day[d], len(g), 1.0
        for i in range(min(BUDGET, n)):
            miss *= max(0.0, (n - k - i) / (n - i))
        vals.append(1 - miss)
    return float(np.mean(vals))


def main(path, out_dir, tr0, tr1, ca0, ca1, te0, te1):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    f = pd.read_parquet(path).reset_index(drop=True)
    f[ALL] = f[ALL].fillna(0.0)
    tr = f[(f["day"] >= tr0) & (f["day"] <= tr1)]
    ca = f[(f["day"] >= ca0) & (f["day"] <= ca1)]
    te = f[(f["day"] >= te0) & (f["day"] <= te1)].copy()
    assert tr["n_attack_flows"].sum() == 0 and ca["n_attack_flows"].sum() == 0

    te["model_p3"], te["top_channel"], P, n_cal = channel_model(tr, ca, te, P3_CHANNELS)
    te = te.join(P.add_prefix("p_"))
    te["ablation_p2"], _, _, _ = channel_model(tr, ca, te, P2_CHANNELS, dual=False)
    te["ablation_p3_host_only"], _, _, _ = channel_model(tr, ca, te, P3_CHANNELS, dual=False)
    for name, s in pooled_baselines(tr, te).items():
        te[name] = s
    # dev round P3-5: fusion of host-relative channels and the population-relative pooled ECOD
    # (mean of within-day percentile ranks; the continuous pooled score also breaks the conformal-floor ties)
    te["channels_only"] = te["model_p3"]
    te["model_p3"] = (te.groupby("day")["channels_only"].rank(pct=True) + te.groupby("day")["ecod_pooled"].rank(pct=True)) / 2
    te["volume"] = te["flows_out"]
    te["volume_host"] = channel_scores(tr, te, {"v": ["flows_out"]}, dual=False)["v"]
    te["ablation_gnn_only"] = te[["lm_gnn_max_out", "lm_gnn_max_in"]].max(axis=1)
    methods = ["model_p3", "channels_only", "volume", "volume_host", "ecod_pooled", "iforest_pooled", "autoencoder_pooled",
               "ablation_p2", "ablation_p3_host_only", "ablation_gnn_only"]
    res = {"seed": SEED, "budget_per_day": BUDGET, "split": {"train": [tr0, tr1], "cal": [ca0, ca1], "test": [te0, te1]},
           "n_train_host_hours": len(tr), "n_calibration_scores": n_cal, "n_test_host_hours": len(te),
           "positive_host_hours": int((te["n_attack_flows"] > 0).sum()),
           "positive_host_days": int(te[te["n_attack_flows"] > 0].groupby(["day", "host"]).ngroups),
           "random_host_day_detection_at_5": random_detection(te)}
    res["methods"] = {m: evaluate(te, m) for m in methods}
    pos = te[te["n_attack_flows"] > 0]
    res["within_host_hour_auc_model"] = {
        h: auc((g["n_attack_flows"] > 0), g["model_p3"]) for h, g in te[te["host"].isin(pos["host"].unique())].groupby("host")}
    res["top_channel_on_attack_hours"] = pd.crosstab(pos["tactics"].str.split(",").str[0], pos["top_channel"]).to_dict()
    te.drop(columns=[c for c in te.columns if c.startswith("p_")]).to_parquet(out / "test_scores.parquet", index=False)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    tab = pd.DataFrame(res["methods"]).T
    tab.to_csv(out / "methods.csv")
    print(json.dumps({k: v for k, v in res.items() if k not in ("methods",)}, indent=1))
    print(tab.round(3).to_string())


if __name__ == "__main__":
    main(*sys.argv[1:])
