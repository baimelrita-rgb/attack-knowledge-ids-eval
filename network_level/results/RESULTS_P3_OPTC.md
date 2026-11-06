# P3 on DARPA OpTC (Zeek conn logs): result against the pre-registered gate

Single run of the frozen P3 code on OpTC (`out_p3_optc/results.json`, `out_p3_optc/methods.csv`).
Data: 10 UTC days 2019-09-16 .. 2019-09-25 (2019-09-25 ends at 18:00 UTC in the source), read from the
user's Drive copies of `bro/<date>/conn.*` (flow counts identical to the originals for the hours checked).
Train 09-16..19, calibration 09-20..22, test 09-23..25. 1,037 internal hosts.

## Ground truth (`optc/gt_report.json`)
- Host-hours with flows to documented attacker servers: 1,451; report-timeline host-hours: 70 (68 have traffic).
- 26 host-hours with flows to attacker servers on train/calibration days (09-16, 09-19, 09-20) were removed,
  as pre-registered.
- Test positives: 1,430 host-hours, 1,035 host-days. 2019-09-25: 1,001 of 1,017 hosts are positive, because on day 3 the
  attacker server (53.192.68.50) was reached through hijacked names (notepadplus-sourceforge.net, microsoft.com).

## Gate: FAILED
| Method | Host-day AUC (primary) | Host-hour AUC | Detection at 5/day |
|---|---|---|---|
| **model_p3** | 0.673 | 0.898 | 0.008 |
| autoencoder_pooled | **0.960** | **0.987** | 0.009 |
| ecod_pooled | 0.896 | 0.937 | 0.003 |
| iforest_pooled | 0.876 | 0.930 | 0.000 |
| volume | 0.296 | 0.259 | 0.001 |
| volume_host | 0.291 | 0.308 | 0.001 |
| channels_only (ablation) | 0.707 | 0.876 | 0.005 |
| ablation_gnn_only | 0.513 | 0.511 | 0.001 |
1. model > every baseline (host-day AUC): **no** (0.673 < 0.960, 0.896, 0.876).
2. CI of (model - best baseline) > 0: **no** (point difference -0.287).
3. detection at 5/day >= every baseline: **no** (0.008 < 0.009).

## Post-hoc, per test day (`out_p3_optc/per_day_posthoc.txt`; not part of the gate)
| Day | Positive hosts / hosts | model_p3 | autoencoder | iforest | ecod | volume |
|---|---|---|---|---|---|---|
| 09-23 (red team day 1) | 22 / 1,017 | 0.584 | **0.897** | 0.697 | 0.673 | 0.473 |
| 09-24 (red team day 2) | 12 / 986 | 0.716 | **0.953** | 0.906 | 0.852 | 0.360 |
| 09-25 (day 3) | 1,001 / 1,017 | 0.879 | 0.888 | 0.040 | 0.441 | 0.912 |
On the two days with a meaningful ground truth, the pooled autoencoder is best and the model is below all
three pooled detectors. The GNN channel is inactive, as expected (only ICMP internal flows are visible).

## Across the three datasets (host-day AUC, model vs best baseline)
| Dataset | Role | Model | Best baseline |
|---|---|---|---|
| DEDALE | dev | 0.652 | 0.688 (ecod_pooled) |
| Unraveled | dev | 0.818 | 0.750 (volume) |
| OpTC | test | 0.673 | 0.960 (autoencoder_pooled) |
