"""Seed stability of the pooled baselines on OpTC (RQ1): autoencoder and Isolation Forest, seeds 0-4.

Everything except the seed matches run_p3.py (same features, same split, same host-day AUC definition).
Usage: python seeds_network_baselines.py FEATURES_PARQUET OUT_JSON
"""
import json
import sys

import numpy as np
import pandas as pd

import run_p3 as R

TR, CA, TE = ("2019-09-16", "2019-09-19"), ("2019-09-20", "2019-09-22"), ("2019-09-23", "2019-09-25")


def host_day_auc(te, col):
    hd = te.groupby(["day", "host"]).agg(s=(col, "max"), y=("n_attack_flows", lambda v: bool((v > 0).any())))
    return R.auc(hd["y"], hd["s"])


def main(path, out):
    f = pd.read_parquet(path).reset_index(drop=True)
    f[R.ALL] = f[R.ALL].fillna(0.0)
    tr = f[(f["day"] >= TR[0]) & (f["day"] <= TR[1])]
    te = f[(f["day"] >= TE[0]) & (f["day"] <= TE[1])].copy()
    res = {}
    for seed in range(5):
        R.SEED = seed
        b = R.pooled_baselines(tr, te)
        for name in ("autoencoder_pooled", "iforest_pooled", "ecod_pooled"):
            te[name] = b[name]
            res.setdefault(name, []).append(host_day_auc(te, name))
        print(seed, {k: round(v[-1], 3) for k, v in res.items()}, flush=True)
    summ = {k: {"values": v, "median": float(np.median(v)), "min": float(min(v)), "max": float(max(v))} for k, v in res.items()}
    json.dump(summ, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
