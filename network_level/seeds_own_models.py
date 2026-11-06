"""Seed round 2 (PLAN_SEEDS2.md): GNN lateral channel + run_p3 + explain_e1 with SEED = s.

Usage: python seeds_own_models.py SEED [check]
  per seed: regenerates lm_gnn_* for DEDALE, Unraveled, OpTC into data_raw/seeds2/seed<s>/,
  runs run_p3 on OpTC (test) and Unraveled (dev), then explain_e1 on the three datasets.
  'check' only regenerates the GNN columns and compares them with the stored tables.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "explain"))  # release layout: ../explanation
sys.path.insert(0, str(HERE.parent / "explanation"))
import gnn_edges as G  # noqa: E402
import run_p3 as R  # noqa: E402

RAW = HERE.parent / "data_raw"
GNN_COLS = ["lm_gnn_max_out", "lm_gnn_n_surprising_out", "lm_gnn_max_in"]
DS = {  # edges, host-hour input, frozen final table, GNN train range
    "dedale": (RAW / "pilot/dedale_p3_edges.parquet", RAW / "pilot/dedale_p3_host_hour.parquet",
               RAW / "pilot/dedale_p3_gnn.parquet", ("2024-12-24", "2025-01-02")),
    "unraveled": (RAW / "pilot/unraveled_p3_edges.parquet", RAW / "pilot/unraveled_p3_host_hour.parquet",
                  RAW / "pilot/unraveled_p3_gnn.parquet", ("2021-05-28", "2021-06-04")),
    "optc": (RAW / "optc/optc_edges.parquet", RAW / "optc/optc_host_hour.parquet",
             RAW / "optc/optc_final.parquet", ("2019-09-16", "2019-09-19")),
}
P3_SPLITS = {"optc": ("2019-09-16", "2019-09-19", "2019-09-20", "2019-09-22", "2019-09-23", "2019-09-25"),
             "unraveled": ("2021-05-28", "2021-06-04", "2021-06-05", "2021-06-07", "2021-06-08", "2021-07-06")}


def gnn_tables(seed, out):
    G.SEED = seed
    paths, diffs = {}, {}
    for name, (edges, hh, final, (t0, t1)) in DS.items():
        tmp = out / f"{name}_gnn_raw.parquet"
        G.main(str(edges), str(hh), str(tmp), t0, t1)
        g = pd.read_parquet(tmp).set_index(["host", "hour"])[GNN_COLS]
        f = pd.read_parquet(final)
        old = f.set_index(["host", "hour"])[GNN_COLS]
        new = g.reindex(old.index).fillna(0.0)
        diffs[name] = float(np.nanmax(np.abs(new.to_numpy() - old.to_numpy())))
        f = f.drop(columns=GNN_COLS).set_index(["host", "hour"]).join(new).reset_index()[list(f.columns)]
        p = out / f"{name}_final.parquet"
        f.to_parquet(p, index=False)
        paths[name] = p
    return paths, diffs


def main(seed, mode="full"):
    seed = int(seed)
    out = RAW / f"seeds2/seed{seed}"
    out.mkdir(parents=True, exist_ok=True)
    paths, diffs = gnn_tables(seed, out)
    print("max |new - stored| per dataset:", diffs, flush=True)
    (out / "gnn_diff_vs_stored.json").write_text(json.dumps(diffs))
    if mode == "check":
        return
    R.SEED = seed
    for name, sp in P3_SPLITS.items():
        R.main(str(paths[name]), str(out / f"p3_{name}"), *sp)
    import explain_e1 as E
    E.SEED = seed
    for name in E.DATASETS:
        p, tr, ca, te = E.DATASETS[name]
        E.DATASETS[name] = (paths[name], tr, ca, te)
    E.main(str(out / "e1"))


if __name__ == "__main__":
    main(*sys.argv[1:])
