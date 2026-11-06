"""E1: tactic-channel explanations vs SHAP / AE-error / occlusion explainers. See PLAN_E1.md.

Usage: python explain_e1.py OUT_DIR
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pilot"))
from run_p3 import ALL, P3_CHANNELS, SEED, channel_model, prep  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data_raw"
TACTIC = ["recon", "c2", "lateral", "exfil"]
DATASETS = {
    "dedale": (RAW / "pilot/dedale_p3_gnn.parquet", ("2024-12-24", "2025-01-02"), ("2025-01-03", "2025-01-05"), ("2025-01-06", "2025-01-19")),
    "unraveled": (RAW / "pilot/unraveled_p3_gnn.parquet", ("2021-05-28", "2021-06-04"), ("2021-06-05", "2021-06-07"), ("2021-06-08", "2021-07-06")),
    "optc": (RAW / "optc/optc_final.parquet", ("2019-09-16", "2019-09-19"), ("2019-09-20", "2019-09-22"), ("2019-09-23", "2019-09-25")),
}
DEDALE_MAP = {"TA0043": "recon", "TA0007": "recon", "TA0011": "c2", "TA0008": "lateral", "TA0010": "exfil"}
UNRAVELED_MAP = {"Reconnaissance": "recon", "Establish Foothold": "c2", "Lateral Movement": "lateral", "Data Exfiltration": "exfil"}
OPTC_KW = [("recon", r"ping sweep|arp scan|port scan|scan"), ("lateral", r"pivot|invoke_wmi|wmi|rdp|spread|psexec"),
           ("exfil", r"exfiltrat|netcat|nc\.exe")]
TIMELINE = Path(__file__).resolve().parent.parent / "pilot/optc/timeline_host_hours.csv"


def ground_truth(name, rows):
    out = []
    if name == "optc":
        tl = pd.read_csv(TIMELINE)
        tl_map = tl.groupby(["host_ip", "utc_hour"])["entry"].apply(lambda s: " ".join(s).lower()).to_dict()
    for _, r in rows.iterrows():
        tac = str(r["tactics"]) if pd.notna(r["tactics"]) else ""
        if name == "dedale":
            g = {DEDALE_MAP[t] for t in tac.split(",") if t in DEDALE_MAP}
        elif name == "unraveled":
            g = {UNRAVELED_MAP[t] for t in tac.split(",") if t in UNRAVELED_MAP}
        else:
            g = {"c2"} if "C2" in tac else set()
            text = tl_map.get((r["host"], r["hour"]), "")
            g |= {ch for ch, pat in OPTC_KW if re.search(pat, text)}
        out.append(g)
    return out


def channel_idx():
    return {ch: [ALL.index(f) for f in P3_CHANNELS[ch]] for ch in TACTIC}


def pick(attr, idx):
    """channel with the largest mean |attribution| over its features"""
    m = np.stack([np.abs(attr[:, idx[ch]]).mean(axis=1) for ch in TACTIC], axis=1)
    return [TACTIC[i] for i in m.argmax(axis=1)]


def run_dataset(name):
    path, trs, cas, tes = DATASETS[name]
    f = pd.read_parquet(path).reset_index(drop=True)
    f[ALL] = f[ALL].fillna(0.0)
    tr = f[(f["day"] >= trs[0]) & (f["day"] <= trs[1])]
    ca = f[(f["day"] >= cas[0]) & (f["day"] <= cas[1])]
    te = f[(f["day"] >= tes[0]) & (f["day"] <= tes[1])].copy()

    _, _, P, _ = channel_model(tr, ca, te, P3_CHANNELS)
    Pt = P[TACTIC]
    te["ours"] = Pt.idxmin(axis=1)
    te["unexplained"] = (Pt.min(axis=1) * len(TACTIC)) > 0.05

    Xtr, Xte = prep(tr), prep(te)
    sc = StandardScaler().fit(Xtr)
    Ztr, Zte = sc.transform(Xtr), sc.transform(Xte)
    ae = MLPRegressor(hidden_layer_sizes=(32, 8, 32), max_iter=300, random_state=SEED).fit(Ztr, Ztr)
    ae_score = lambda Z: ((ae.predict(Z) - Z) ** 2).mean(axis=1)  # noqa: E731
    te["ae_score"] = ae_score(Zte)
    iso = IsolationForest(n_estimators=200, random_state=SEED).fit(Xtr)

    pos = te[te["n_attack_flows"] > 0].copy()
    pos["gt"] = ground_truth(name, pos)
    pos = pos[pos["gt"].map(len) > 0]
    if name == "optc":
        pos["primary"] = pos["day"] <= "2019-09-24"
    else:
        pos["primary"] = True
    idx = channel_idx()
    Zp, Xp = sc.transform(prep(pos)), prep(pos)

    pos["ae_error"] = pick((ae.predict(Zp) - Zp) ** 2, idx)
    bg = shap.kmeans(Ztr, 20)
    np.random.seed(SEED)
    ke = shap.KernelExplainer(ae_score, bg)
    pos["shap_ae"] = pick(np.asarray(ke.shap_values(Zp, nsamples=200, silent=True)), idx)
    pos["shap_if"] = pick(np.asarray(shap.TreeExplainer(iso).shap_values(Xp)), idx)
    med = np.median(Xtr, axis=0)
    base = ae_score(Zp)
    drops = {}
    for ch in TACTIC:
        Xo = Xp.copy()
        Xo[:, idx[ch]] = med[idx[ch]]
        drops[ch] = base - ae_score(sc.transform(Xo))
    D = pd.DataFrame(drops, index=pos.index)
    pos["occlusion_ae"] = D.idxmax(axis=1)
    maxdrop = D.max(axis=1)
    for m in ["ours", "ae_error", "shap_ae", "shap_if"]:
        chosen = np.array([D.loc[i, c] for i, c in zip(pos.index, pos[m])])
        pos[f"faith_{m}"] = np.where(maxdrop > 0, chosen / maxdrop.where(maxdrop > 0), np.nan)
    pos["random_acc"] = pos["gt"].map(lambda g: len(g & set(TACTIC)) / len(TACTIC))
    q = te.groupby("day")["ae_score"].transform(lambda s: s.quantile(0.95))
    pos["ae_top5pct"] = pos["ae_score"] >= q.loc[pos.index]
    pos["dataset"] = name
    unexpl = {"positive": float(te.loc[te["n_attack_flows"] > 0, "unexplained"].mean()),
              "negative": float(te.loc[te["n_attack_flows"] == 0, "unexplained"].mean())}
    return pos, unexpl


METHODS = ["ours", "ae_error", "shap_ae", "shap_if", "occlusion_ae"]


def acc(df):
    r = {m: float(np.mean([c in g for c, g in zip(df[m], df["gt"])])) for m in METHODS}
    r["random"] = float(df["random_acc"].mean())
    r["n"] = int(len(df))
    return r


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    parts, unexpl = [], {}
    for name in DATASETS:
        p, u = run_dataset(name)
        parts.append(p)
        unexpl[name] = u
        print(name, len(p), flush=True)
    allp = pd.concat(parts)
    prim = allp[allp["primary"]]
    res = {"accuracy": {n: acc(prim[prim["dataset"] == n]) for n in DATASETS}}
    res["accuracy"]["pooled"] = acc(prim)
    res["accuracy"]["optc_day3"] = acc(allp[(allp["dataset"] == "optc") & ~allp["primary"]])
    res["accuracy_top5pct_ae"] = {n: acc(prim[(prim["dataset"] == n) & prim["ae_top5pct"]]) for n in DATASETS}
    res["faithfulness_mean"] = {m: float(prim[f"faith_{m}"].mean()) for m in ["ours", "ae_error", "shap_ae", "shap_if"]}
    res["unexplained_rate"] = unexpl
    pooled = res["accuracy"]["pooled"]
    best = max((m for m in METHODS if m != "ours"), key=lambda m: pooled[m])
    rng = np.random.default_rng(SEED)
    groups = prim.groupby(["dataset", "host", "day"]).indices
    keys = list(groups)
    hit_o = np.array([c in g for c, g in zip(prim["ours"], prim["gt"])], dtype=float)
    hit_b = np.array([c in g for c, g in zip(prim[best], prim["gt"])], dtype=float)
    diffs = []
    for _ in range(1000):
        sel = np.concatenate([groups[keys[i]] for i in rng.integers(0, len(keys), len(keys))])
        diffs.append(hit_o[sel].mean() - hit_b[sel].mean())
    res["best_baseline_pooled"] = best
    res["diff_ours_minus_best_ci95"] = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
    others = [m for m in METHODS if m != "ours"] + ["random"]
    wins = sum(all(res["accuracy"][n]["ours"] > res["accuracy"][n][m] for m in others) for n in DATASETS)
    res["gate"] = {
        "1_pooled_beats_all_and_ci_low_gt_0": all(pooled["ours"] > pooled[m] for m in others) and res["diff_ours_minus_best_ci95"][0] > 0,
        "2_beats_all_on_2_of_3_datasets": wins >= 2,
        "3_faithfulness_ge_ae_error_and_shap_ae": res["faithfulness_mean"]["ours"] >= max(res["faithfulness_mean"]["ae_error"], res["faithfulness_mean"]["shap_ae"]),
    }
    res["gate"]["pass"] = all(res["gate"].values())
    gt_counts = prim.assign(gt=prim["gt"].map(lambda g: ",".join(sorted(g)))).groupby(["dataset", "gt"]).size()
    res["ground_truth_counts"] = {f"{a}|{b}": int(v) for (a, b), v in gt_counts.items()}
    allp.assign(gt=allp["gt"].map(lambda g: ",".join(sorted(g))))[
        ["dataset", "day", "host", "hour", "gt", "primary", "ae_top5pct"] + METHODS + [c for c in allp.columns if c.startswith("faith_")]
    ].to_csv(out / "explanations.csv", index=False)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])
