# E1 results: tactic-channel explanations vs baseline explainers (single run of the frozen code)

Numbers from `out_e1/results.json`; per-row explanations in `out_e1/explanations.csv`;
channels chosen per method in `out_e1/chosen_channels.txt`.

## Attribution accuracy (share of positive host-hours whose explained channel is a ground-truth channel)
| Dataset (n) | Ours | AE-error | SHAP-AE | SHAP-IF | Occlusion-AE | Random |
|---|---|---|---|---|---|---|
| DEDALE (12) | 0.583 | 0.750 | 0.750 | 0.500 | **0.833** | 0.354 |
| Unraveled (645) | 0.254 | **0.563** | 0.341 | 0.357 | 0.397 | 0.263 |
| OpTC days 1-2 (102) | 0.373 | 0.294 | 0.069 | **0.412** | 0.314 | 0.341 |
| **Pooled (759)** | 0.275 | **0.530** | 0.311 | 0.366 | 0.393 | 0.275 |
| OpTC day 3 (1,328; not primary) | 0.205 | 0.390 | 0.005 | 0.292 | 0.302 | 0.251 |
Best baseline pooled: AE-error; ours - AE-error = -0.255, bootstrap 95% CI [-0.395, -0.114].

## Gate E1: FAILED
1. pooled: ours > every baseline with CI > 0 — **no** (ours equals random, 0.275).
2. ours best on >= 2 of 3 datasets — **no** (best on none).
3. faithfulness — formally "yes", but **the metric is invalid as defined**: the normalised drop divides by the
   largest occlusion drop, which is close to zero for many rows; means of -2.7 (ours) and about -1e11 (baselines)
   are artefacts, not evidence. The item is not counted.

## Other measurements
- "Unexplained" rate: DEDALE positive 0.54 vs negative 0.82; Unraveled 0.54 vs 0.95; OpTC 0.91 vs 0.99.
  The channel p-values are lower on attack hours, but at the 0.05 level most attack hours stay "unexplained".
- Among host-hours in the top 5% of the AE score (Unraveled n = 161), all explainers are below random (0.07-0.11 vs 0.26).
- SHAP-AE on OpTC: 0.069 (days 1-2) and 0.005 (day 3), far below random.

## Reading
- The calibrated tactic channels do not identify the attack stage better than chance on these data.
- A simple explainer, the autoencoder's reconstruction error grouped into the same four ATT&CK channels, is the
  best pooled explainer (0.530) and roughly doubles random accuracy; it was a baseline here, not a
  pre-registered method, so its advantage needs confirmation on data not used for this comparison.
- KernelSHAP on the autoencoder is close to or below random for tactic attribution on Unraveled and OpTC.
