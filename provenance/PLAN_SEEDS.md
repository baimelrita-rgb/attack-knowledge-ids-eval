# Additional seeds for the Velox-lite test runs (added 2026-11-01, before any extra seed was run)

Reason: every test dataset was run with one seed (seed 0); PIDSMaker reports seed instability, so a single run says
nothing about variability.

## What is run
- Velox-lite with seeds 1, 2, 3, 4 on the six test datasets: OpTC h501, h051, h201, DARPA TC E3 CADETS, THEIA,
  CLEARSCOPE. Code and settings are unchanged (`velox_lite.py`, emb 32, 3 epochs, <= 4M training events sampled).
  The seed controls the training-event sample, word2vec, and network initialisation.
- Seed 0 results are the ones already reported. The knowledge points are deterministic and computed once per dataset.

## What does not change
- The pre-registered gates are evaluated on seed 0 only, as committed. Extra seeds are reported as variability and
  are not used to re-decide any gate.
- Fusion parameters stay fixed: lambda = 0.1 (sum); interleave as defined in PREREG_PHASE3.md.

## Reporting
For each dataset and method: median and min-max over the five seeds of attacks detected and ground-truth nodes
found at 10 / 25 / 50 / 100 / 250 / 500 nodes, and AUC of Velox-lite. Pooled over the three E3 datasets and over
the three OpTC hosts, per seed, with the gate quantities of PREREG_PHASE2.md and PREREG_PHASE3.md recomputed per
seed (descriptive only).
