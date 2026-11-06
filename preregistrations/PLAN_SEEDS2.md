# Additional seeds, round 2: our own network-level models and the development learned detector
(written 2026-11-02, before any run of this round)

Reason: the threats-to-validity section states that our own models (RQ1 tactic channels + GNN, RQ3 explainers) and
the development datasets were run with one seed. This round repeats them.

## What is run
1. **RQ1, OpTC (test) and Unraveled/DEDALE (development).** For seeds s = 0..4: re-train the GNN lateral channel
   (`gnn_edges.py`, unchanged except `SEED = s`; the seed controls the embedding/MLP initialisation and the negative
   sampling), replace the three `lm_gnn_*` columns of the frozen feature tables, and re-run `run_p3.py` with
   `SEED = s` (autoencoder and Isolation Forest baselines). The tactic channels (ECOD tails + conformal p-values) are
   deterministic given the features. Reported: host-day AUC and host-day detection at 5 alerts/day of every method.
2. **RQ3, explanation study.** For the same seeds and the same per-seed feature tables, re-run `explain_e1.py` with
   `SEED = s` (autoencoder, Isolation Forest, KernelSHAP sampling, bootstrap). Reported: attribution accuracy per
   dataset and method, median [min-max] over seeds, and the three E1 gate conditions per seed.
3. **RQ2 development, ATLASv2.** Velox-lite seeds 1-4 (seed 0 already reported), fused with lambda = 0.1, evaluated
   with `eval_ranking.py`. CARBANAKv2 has no learned-detector result in the paper (only the deterministic rule
   coverage), so nothing seed-dependent is repeated there.

## Sanity check
Before the new seeds, the GNN is re-run with the original seed 42 and must reproduce the stored `lm_gnn_*` columns
(otherwise the difference is reported as a deviation).

## What does not change
- Features, splits, channels, fusion, budgets and code are frozen; only the seed changes.
- Pre-registered gate decisions stay as committed (original seed: 42 for RQ1/RQ3, 0 for Velox-lite). The new seeds
  are descriptive; they are not used to re-decide any gate.

## Sanity-check result (recorded before the new seeds were run)
OpTC (test): seed 42 reproduces the stored `lm_gnn_*` columns exactly (max abs difference 0.0).
DEDALE and Unraveled (development): not bit-identical (Spearman 0.88-0.9998 per column; tables written on
2026-10-30 in an earlier container, probably a different torch build/thread count). Deviation: seed 42 is therefore
re-run in full in this round as well, and the development-data comparison across seeds uses the regenerated tables.
Update (same day, before any seed other than 42 finished): two consecutive seed-42 runs in this container also
differ from each other on DEDALE/Unraveled (max abs difference 4.4 and 9.0 on DEDALE), while OpTC is identical.
The GNN training on these two graphs is not deterministic run to run on this CPU (multi-threaded scatter/aggregation),
so the original tables are one draw of this variation. Reported as such.
