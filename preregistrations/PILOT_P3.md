# P3: final model (frozen) and pre-registered test on DARPA OpTC

Development used DEDALE and Unraveled only (both already seen). The final test is OpTC, on which no model has run.
Code frozen in this commit: `flows.py`, `features.py`, `features_p3.py`, `gnn_edges.py`, `run_p3.py`.

## Model
1. Host-hour features (`features.py`, `features_p3.py`): recon; C2 (new external destinations, rare destinations
   = contacted by <= 2 internal hosts before, beacon regularity over 72 h); lateral movement (GNN edge surprise,
   new admin-port edges); exfiltration; volume.
2. GNN lateral channel (`gnn_edges.py`): GraphSAGE encoder on the internal host graph of the training days,
   MLP decoder over (src, dst, port); edge surprise = -log p; training days scored by cross-fitted models.
3. Tactic channels (`run_p3.py`): each feature scored against the host's own training hours (one-sided empirical
   tail); channel score = most extreme feature (+0.01 x mean); conformal p-values from cross-fitted calibration;
   hour score = -log10(min channel p x 6).
4. Fusion: mean of within-day percentile ranks of the channel score and of a pooled ECOD on all features.
5. Explanation = channel with the smallest p-value in the hour.

## Development log (P3), all rounds
| Round | Change | DEDALE det@5 / AUC hour / AUC day | Unraveled det@5 / AUC hour / AUC day | Kept |
|---|---|---|---|---|
| 1 | P3 features, GNN, volume channel (sum over features) | 0.182 / 0.646 / 0.492 | 0.283 / 0.866 / 0.748 | base |
| 2 | dual reference (rare for host and population) | 0.182 / 0.671 / 0.512 | 0.217 / 0.821 / 0.789 | no |
| 3 | channel = max over features | 0.273 / 0.743 / 0.672 | 0.150 / 0.906 / 0.883 | yes |
| 4 | tie-break by channel mean | 0.273 / 0.743 / 0.664 | 0.133 / 0.906 / 0.881 | yes (no effect) |
| 5 | fusion with pooled ECOD | 0.273 / 0.774 / 0.652 | 0.283 / 0.899 / 0.818 | yes |
Final dev results with all baselines: `out_p3_dev_dedale/methods.csv`, `out_p3_dev_unraveled/methods.csv`.
On DEDALE (11 positive host-days) pooled ECOD is better than the model on all three metrics
(0.455 / 0.806 / 0.688); on Unraveled (60) the model is better than every baseline on all three.

## Baselines (fixed)
volume (flows out), volume_host (per-host tail of flows out), ecod_pooled, iforest_pooled, autoencoder_pooled
(MLP 32-8-32); ablations: channels_only, ablation_p2, ablation_p3_host_only, ablation_gnn_only.

## Metrics
Primary: host-day AUC (day score = max hour score). Secondary: host-hour AUC; host-day detection at 5 alerts/day.
Uncertainty: bootstrap over test days (1000, seed 42) of the AUC difference model - best baseline.

## Gate P3 on OpTC (all must hold)
1. Model host-day AUC > host-day AUC of every baseline (point estimate);
2. bootstrap 95% CI of (model - best baseline) host-day AUC has a lower bound > 0;
3. host-day detection at 5 alerts/day >= that of every baseline.

## OpTC split (to be fixed from documented dates only, before any model run)
Train/calibration = days before the first red-team event in `optc_redteam.csv`; test = red-team days.
Ground truth: a (host, hour) is positive if the host is source or target of a red-team event in that hour.
The exact dates and the host mapping are written here, and committed, before running the model.

## OpTC data check (2026-10-30, before any model run on OpTC)
- `bro/<date>/conn.HH...log.gz`: hourly Zeek conn logs, file hours in UTC. Sample 2019-09-23 10:00-11:00 UTC:
  1,716,249 flows; internal->external 1,372,574; external->internal 343,602; internal->internal **60** (all port 0/ICMP);
  676 internal source hosts. The Zeek sensor sees north-south traffic only: OpTC lateral movement
  (SMB/WMI/RDP between hosts) is not visible in `bro`, so the GNN lateral channel cannot be tested on it.
- Host mapping (verified on eCAR FLOW events of 6 host ranges, ~150 hosts, 0 mismatches):
  SysClientNNNN -> 142.20.(56 + (NNNN+1) // 256).((NNNN+1) % 256); DC1 -> 142.20.61.130 (red-team report agent table).
- eCAR timestamps are UTC-04:00; the red-team report timeline is in the same local time.
- eCAR (host sensor, includes internal flows): one 25-host folder for 2019-09-23 is ~110 MB compressed for one of
  its two files; the full evaluation + benign eCAR is far larger than `bro`.

## OpTC test, option 1 (Zeek `bro` conn logs), fixed before any model run
- Data: `bro/<UTC date>/conn.HH:00:00-HH+1:00:00.log.gz`, streamed hour by hour (`optc/optc_features.py`).
  Internal hosts 142.20.56.0/21. Feature code identical to development; novelty/rarity history frozen per UTC day
  as in development; flows logged > 1 h after their start are dropped and counted (`*_ingest_log.csv`).
- Split (UTC days): train 2019-09-16 .. 2019-09-19; calibration 2019-09-20 .. 2019-09-22;
  test 2019-09-23 .. 2019-09-25 (red-team days per the report).
- Ground truth, a (host, UTC hour) is positive if either
  (a) the host has >= 1 flow with a documented attacker server in that hour
      (132.197.158.98 day 1, 202.6.172.98 day 2, 53.192.68.50 day 3; red-team report), or
  (b) the host is named in a report timeline entry in that hour (`optc/timeline_gt.py`, local time UTC-4 -> UTC;
      101 entries, 70 host-hours, 30 hosts).
  If train/calibration days contain flows to these IPs, they are reported and those host-hours removed from
  train/calibration (the model must not train on attack hours).
- The GNN lateral channel is computed but expected to be inactive (no internal edges visible).
- Gate: as above (P3 gate items 1-3), budget 5 alerts/day.
