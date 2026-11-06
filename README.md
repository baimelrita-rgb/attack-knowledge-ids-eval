# When does attack knowledge help learned intrusion detectors? — code, pre-registrations and results

Companion material for the paper *When Does Attack Knowledge Help Learned Intrusion Detectors? A Pre-registered
Evaluation of Detection, Explanation and Blast-Radius Prediction on Public Attack Datasets* (prepared for submission to ACM Digital Threats: Research and Practice).

Every experiment followed the same order:
1. a plan and a pass/fail gate were written (`preregistrations/`);
2. development data only were used to build and tune (development logs in each `results/` folder);
3. the code was frozen;
4. one test run was made, and its result reported against the gate, whether it passed or failed.

No raw data is included; all datasets are public and the download steps are below.

The package is meant as infrastructure for further research on ML-based threat detection: the same protocol,
baselines, gates and controls can be applied to new detectors, knowledge sources and explanation methods (see
"Extending the study" below).

## Map: paper → code → results
| Paper | Code | Results | Pre-registration |
|---|---|---|---|
| RQ1, Table "OpTC host-day AUC"; P1–P3 text | `network_level/` (`features*.py`, `gnn_edges.py`, `run_p2.py`, `run_p3.py`, `optc/`) | `network_level/results/RESULTS_P1.md`, `RESULTS_P2.md`, `RESULTS_P3_OPTC.md` | `preregistrations/PILOT*.md` |
| RQ2, Table "attacks within 10/25/50 alerts", Figure 1 | `provenance/` (`velox_lite.py`, `semantic.py`, `semantic_linux.py`, `reach_v2.py`, `eval_ranking.py`, `eval_phase3.py`) | `provenance/results/RESULTS_PHASE2.md`, `RESULTS_PHASE3.md`, `results_*.json`, `DEVLOG.md` | `preregistrations/PREREG_PHASE2.md`, `PREREG_PHASE3.md` |
| RQ3, Table "attribution accuracy" | `explanation/explain_e1.py` | `explanation/results/RESULTS_E1.md`, `results.json` | `preregistrations/PLAN_E1.md` |
| RQ4, Table "LANL" | `blast_radius/` (`aggregate_auth.py`, `aggregate_auth_users.py`, `blast_radius.py`) | `blast_radius/RESULTS_L3_LANL.md`, `l3_*.json` | `preregistrations/PREREG_PHASE2.md` (L3 section) |
| RQ2 mechanism analysis, Table "mechanism" | `mechanism/mechanism.py` | `mechanism/RESULTS_MECHANISM.md`, `results_mechanism.json` | `preregistrations/PLAN_MECHANISM.md` |
| RQ2 negative control and Holm correction | `round4/negative_control.py`, `round4/holm.py` | `round4/RESULTS_NEGATIVE_CONTROL.md`, `results_holm.json` | `preregistrations/PLAN_ROUND4.md` |
| RQ4 bootstrap intervals | `stats/rq4_bootstrap.py` | `stats/rq4_bootstrap.json` | — |
| Dataset audits (Appendix) | `audits/` | `audits/*/RECON.md`, `audits/CHOICE.md` | — |
| Figure 1 | `paper/figures/make_fig_budget.py` | `paper/figures/fig_budget.pdf` | — |

## Environment
- **Hardware:** CPU only, 4 cores, 15 GB RAM, about 40 GB of disk.
- **Python 3.13** and the packages in `requirements.txt` (exact versions used).
- **PIDSMaker** at commit 438a05a7c55256f639e5b5945cf4828fe3ee078e, with `provenance/pidsmaker_numpy2.patch` applied
  (`np.trapz` → `np.trapezoid`). Set `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` so torch can reload PIDSMaker's own
  pickled graphs, and `NLTK_ALLOW_PROXIED_URLOPEN=1` if NLTK data must be fetched through a proxy.
- **PostgreSQL 17** for the PIDSMaker dumps (pg_restore ≥ 17). Where the PGDG repository is unavailable, the PyPI
  package `postgresql-binaries==17.11.0` contains the server binaries.
- **Paths:** scripts use absolute paths under `/home/user/...` (the original environment); adjust them to your layout.

## Data (public; download separately)
| Dataset | Source | Used for |
|---|---|---|
| DEDALE | Recherche Data Gouv, DOI 10.57745/Y5JLDG (`audits/dedale/download_dedale.py`) | RQ1, RQ3 |
| Unraveled | public S3 bucket `dapt2021` (`audits/unraveled/download_unraveled.py`) | RQ1, RQ3 |
| DARPA OpTC (Zeek `bro/` conn logs, red-team report) | DARPA OpTC Google Drive folder (see `network_level/optc/`) | RQ1, RQ3 |
| ATLASv2-EDR, CARBANAKv2-EDR, OpTC h201/h501/h051, DARPA TC E3 (CADETS, THEIA, CLEARSCOPE) | PIDSMaker database dumps (PIDSMaker documentation) | RQ2 |
| LANL Comprehensive Multi-Source Cyber-Security Events | https://csr.lanl.gov/data/cyber1/ (short form required) | RQ4 |

## Reproducing each result
### RQ2: provenance, test phases
1. Restore a PIDSMaker dump into PostgreSQL 17 (database names as in PIDSMaker's `config.py`).
2. Compute the ground truth and the knowledge points:
   - `python provenance/dump_gt.py <DATASET_KEY> <db> <gt_dir>`;
   - knowledge points via `semantic.py` (Windows) or `semantic_linux.py` (Linux/FreeBSD/Android).
3. Run the learned detector: `python provenance/velox_lite.py <DATASET_KEY> <db> <out_dir> 0`.
4. Evaluate:
   - `python provenance/eval_ranking.py <out_dir>/node_scores.parquet <gt_dir> <out.json> 0.1` (Phase 2);
   - `python provenance/eval_phase3.py ...` (Phase 3).

### RQ4: blast radius
1. Aggregate the LANL logons:
   - `zcat auth.txt.gz | python blast_radius/aggregate_auth.py`, or stream as in the paper;
   - user-level: the awk-prefiltered stream into `aggregate_auth_users.py`.
2. Rank the next targets:
   `python blast_radius/blast_radius.py auth_daily.parquet redteam.txt.gz 13 30 out.json 7 0.15 auth_users_daily.parquet`.

### RQ1 and RQ3: network level
- `network_level/features_p3.py`, then `gnn_edges.py`, then `run_p3.py`; argument order is in each script's docstring.
- `explanation/explain_e1.py OUT_DIR` re-runs the explanation study from the feature tables.

## Seeds
RQ1 baselines on OpTC (5 seeds): `network_level/seeds_network_baselines.py`, `network_level/results/seeds_baselines.json`.
RQ3 per-dataset accuracy with bootstrap intervals: `explanation/results/accuracy_ci.json`.

The pre-registered gate decisions use seed 0. Velox-lite was then repeated with seeds 1-4 on the six test datasets
(`preregistrations/PLAN_SEEDS.md`, `provenance/run_all_extra_seeds.sh`, `provenance/aggregate_seeds.py`); results in
`provenance/results/RESULTS_SEEDS.md` and `provenance/results/seeds/`. The gate outcome is the same in all five seeds.

Seed round 2 (`preregistrations/PLAN_SEEDS2.md`, written before the runs):
- RQ1 and RQ3, full pipeline with six seeds (the original seed 42 re-run, and 0-4); each seed re-trains the GNN
  channel, the pooled autoencoder and Isolation Forest, and redraws the KernelSHAP samples:
  `network_level/seeds_own_models.py SEED`, then `network_level/aggregate_seeds2.py`. Results in
  `network_level/results/RESULTS_SEEDS2.md`, `results_seeds2.json` and `results/seeds2/seed<s>/`.
- ATLASv2 (development), Velox-lite seeds 0-4: `provenance/aggregate_atlas_seeds.py`; results in
  `provenance/results/RESULTS_ATLAS_SEEDS.md` and `provenance/results/seeds/ATLASV2_EDR_seed<s>_*.json`.
- Note: on our CPU the GNN training is bit-reproducible on OpTC but not between runs on DEDALE and Unraveled.

## Extending the study
- **A new provenance detector.** Write a parquet file with columns `index_id`, `score` (higher = more anomalous) and
  `n_test_events` for the nodes active in the test period, then run `provenance/eval_ranking.py` (OpTC, Phase-2
  fusion) or `provenance/eval_phase3.py` (DARPA TC E3). Placing the file at
  `reach_runs/velox_lite/<DATASET>/seed<k>/node_scores.parquet` lets `mechanism/mechanism.py` and
  `round4/negative_control.py` analyse it unchanged (paths are set at the top of each script).
- **A new knowledge source** (for example rules derived from threat intelligence). Write `semantic.parquet` (index
  `index_id`, column `points`) in the dataset's ground-truth folder; the negative control then tests whether its gain
  exceeds that of the same points on random processes.
- **A new network-level detector or explainer.** Add a scoring function next to `pooled_baselines` in
  `network_level/run_p3.py`, or an attribution method next to the explainers in `explanation/explain_e1.py`; both
  evaluate on the same splits, budgets and ground-truth stages.
- **A new dataset.** Follow `audits/` for the ground-truth audit and write a plan and gate in `preregistrations/`
  before opening its test split.

## Deviations (recorded before the affected runs)
- **Velox:** run with embedding size 32, and replaced by Velox-lite on OpTC and E3 because of the disk limit.
  Validation on ATLASv2: AUC 0.836 (Velox-lite) vs 0.864 (PIDSMaker's Velox).
- **λ = 0.1:** set by the pre-registered default rule after both CARBANAKv2 Velox runs failed on disk.
- **LANL split:** changed to days 2–12 / 13–30 because the red-team events end on day 30.
- **Faithfulness metric:** the explanation study's faithfulness metric was ill-defined and is not reported.
- Full details are in each `results/` folder.

## Licence
Code: MIT (see `LICENSE`). Third-party datasets keep their own licences and terms of use.
The OpTC red-team report text in `network_level/optc/redteam_report.txt` is DARPA material approved for public release.
