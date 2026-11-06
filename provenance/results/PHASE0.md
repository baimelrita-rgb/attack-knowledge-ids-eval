# REACH Phase 0 (feasibility) — result: gate F0 PASSED

Date 2026-10-31. Plan: `PHD/EXPERIMENT_PLAN_REACH_CPU.md`.

## Environment (CPU only)
- 4 cores, 15 GB RAM, no GPU; Python 3.13, torch 2.15 (CPU use), torch_geometric 2.8.1, torch_scatter, pyod 3.6.7.
- PIDSMaker commit 438a05a7c55256f639e5b5945cf4828fe3ee078e (2026-10-02), cloned to /home/user/ext/PIDSMaker.
- PostgreSQL 17.11 binaries from the PyPI package `postgresql-binaries==17.11.0` (the PGDG apt repository is blocked;
  the PIDSMaker dumps need pg_restore >= 17). Server on port 5432, data dir /home/user/ext/pgdata17.
- Local compatibility changes (no change to method or metrics):
  - `pidsmaker_numpy2.patch`: `np.trapz` -> `np.trapezoid` (removed in NumPy 2);
  - `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` so torch can reload graphs that the pipeline itself saved
    (torch >= 2.6 default);
  - NLTK `punkt`/`punkt_tab` downloaded with `NLTK_ALLOW_PROXIED_URLOPEN=1`.

## Data
- `atlasv2_edr.dump` (183,333,724 bytes) from the PIDSMaker Drive folder; restored in 11 s.
  event_table 2,703,140 rows; subject (process) 66,897 with path and command line; file 569,643; netflow 27,357.
- LANL: `redteam.txt.gz` (749 compromise events); `auth.txt.gz` (7,626,505,158 bytes) downloading.

## F0 run: Velox, ATLASv2-EDR, default config, CPU, one seed (`velox_atlasv2_dev_seed_default.log`)
- Wall time about 20 min (feature inference about 6 min, 50 epochs x about 6 s, evaluation).
- Node-level metrics at the pipeline's threshold:
  - TP 0, FP 0, TN 152,386, FN 48;
  - AUC 0.86774, AP 0.01409, ADP 0.107;
  - attacks detected at threshold: 0.0%.
- Ranking metrics with all attacks detected: 27 true positives at 12,762 false positives.
These are development-data numbers for the baseline; ATLASv2 is not one of the datasets in the Velox paper.
