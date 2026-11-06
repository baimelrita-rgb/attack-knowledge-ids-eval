"""RQ4: 95% bootstrap intervals (resampling test days, 10,000 draws) for recall@k of each method and for its
difference from the degree baseline. Usage: python rq4_bootstrap.py L3_TEST_JSON OUT_JSON"""
import json
import sys

import numpy as np

METHODS = ["degree", "bfs1", "ppr", "cred", "cred_after"]


def main(path, out):
    days = json.load(open(path))["days"]
    T = np.array([d["targets"] for d in days], float)
    rng = np.random.default_rng(0)
    idx = rng.integers(0, len(days), (10000, len(days)))
    res = {"n_days": len(days), "n_targets": int(T.sum())}
    for k in (10, 50, 100):
        H = {m: np.array([d[m][f"hits@{k}"] for d in days], float) for m in METHODS}
        for m in METHODS:
            rec = H[m][idx].sum(1) / T[idx].sum(1)
            res[f"{m}_recall@{k}"] = [float(H[m].sum() / T.sum()), *np.percentile(rec, [2.5, 97.5]).tolist()]
            if m != "degree":
                dif = (H[m][idx].sum(1) - H["degree"][idx].sum(1)) / T[idx].sum(1)
                res[f"{m}_minus_degree@{k}"] = [float((H[m].sum() - H["degree"].sum()) / T.sum()),
                                                *np.percentile(dif, [2.5, 97.5]).tolist()]
    json.dump(res, open(out, "w"), indent=1)
    for k, v in res.items():
        print(k, [round(x, 3) for x in v] if isinstance(v, list) else v)


if __name__ == "__main__":
    main(*sys.argv[1:])
