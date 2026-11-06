# E1: tactic-channel explanations for any detector — pre-registered plan

Paper direction (decided 2026-10-31 after the P3 OpTC result): detection by a standard detector (the strongest on
the test data was a pooled autoencoder); the contribution is the explanation layer: ATT&CK-tactic channels with
calibrated p-values and an explicit "unexplained" output. This file is committed before any E1 run.

## What has already been seen (disclosure)
- Channels, features and calibration are frozen from P3 (`../pilot/run_p3.py`, `../pilot/features*.py`); nothing
  in them is changed for E1.
- Already looked at: crosstab of top channel vs Stage on Unraveled attack hours in P2 (exfil 233/269 correct,
  lateral channel never top), top channel per day on OpTC positives in P3 (counts only, no accuracy computed).

## Explanation output (ours)
For a host-hour: the four tactic channels {recon, c2, lateral, exfil} with conformal p-values (P3 model:
per-host one-sided tail, max-feature channel score, cross-fitted calibration). Explanation = channel with the
smallest p; "unexplained" if min p x 4 > 0.05. Volume and residual channels are not tactics and are not outputs.

## Baseline explainers (each produces a channel by grouping feature attributions over the same 4 channels'
feature lists and taking the channel with the largest mean attribution)
- AE-error: per-feature reconstruction error of the pooled autoencoder (P3 baseline, same training).
- SHAP-AE: KernelSHAP on the autoencoder score (background: 20 k-means centres of the training rows,
  nsamples = 200, seed 42).
- SHAP-IF: TreeSHAP on the pooled Isolation Forest.
- Occlusion-AE: channel whose features, replaced by their training medians, lower the AE score most.
- Random: uniform over the 4 channels (expected accuracy computed exactly).

## Ground truth channel per positive host-hour (fixed mapping)
- DEDALE (`tactics` column, ATT&CK tactic IDs): TA0043/TA0007 -> recon; TA0011 -> c2; TA0008 -> lateral;
  TA0010 -> exfil; TA0001, TA0009 and label-2 rows -> no channel.
- Unraveled (`Stage`): Reconnaissance -> recon; Establish Foothold -> c2; Lateral Movement -> lateral;
  Data Exfiltration -> exfil; Cover up -> no channel.
- OpTC: host-hours with flows to a documented attacker server -> c2; report-timeline entries by keyword:
  "ping sweep|arp scan|port scan|scan" -> recon; "pivot|invoke_wmi|wmi|rdp|spread|psexec" -> lateral;
  "exfiltrat|netcat|nc.exe" -> exfil. Primary OpTC evaluation: 2019-09-23 and 2019-09-24 only (day 3's ground
  truth is dominated by the hijacked-name artifact, 1,001 of 1,017 hosts); day 3 reported separately.
A host-hour can have several ground-truth channels; an explanation is correct if it is one of them.
Host-hours with no mapped channel are excluded from accuracy.

## Metrics
1. Attribution accuracy on all positive host-hours with a mapped channel (test period).
   Secondary: the same restricted to host-hours in the top 5% of the AE score of their day.
2. Faithfulness (AE detector): normalised drop = (AE score drop when the explained channel is occluded) /
   (largest drop over the 4 channels). Occlusion-AE is 1 by construction and is not compared on this metric.
3. "Unexplained" rate on positive vs negative host-hours.
Uncertainty: bootstrap over host-days (1,000, seed 42) of the accuracy difference ours - best baseline.

## Gate E1 (all must hold)
1. Pooled over the three datasets (OpTC days 1-2), our accuracy > every baseline's, and the bootstrap 95% CI of
   (ours - best baseline) has a lower bound > 0;
2. our accuracy > every baseline's on at least 2 of the 3 datasets;
3. our mean normalised faithfulness >= that of AE-error and SHAP-AE.
