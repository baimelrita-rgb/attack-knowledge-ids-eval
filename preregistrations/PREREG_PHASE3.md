# REACH Phase 3 (test on DARPA TC E3: CLEARSCOPE, CADETS, THEIA): pre-registration

Committed 2026-11-01, before any E3 data is downloaded or loaded.

## Development summary (all data seen so far: ATLASv2, CARBANAKv2, OpTC h201/h501/h051)
Development results in `../data_raw/reach_runs/v2dev/*.json` (summarised in DEVLOG.md).
- Graph propagation of suspicion (gamma 0.5, depth 2) was mixed and is not used.
- Interleaving was robust at 10 nodes on OpTC (catches whatever either ranking catches early) but weaker than the
  additive sum on ATLASv2.

## Methods (frozen)
1. Velox-lite (`velox_lite.py`, seed 0).
2. Knowledge only: `semantic_linux.py` points, ties broken by the Velox-lite percentile.
3. Sum: Velox-lite percentile + 0.1 x points.
4. **Interleave (primary)**: alternate the Velox-lite ranking and the knowledge ranking, Velox-lite first.

## Allowed adaptation at load time (no ground truth involved)
Column names of the E3 node tables and the process-creation operation names may be mapped to the code's fields
from the table schemas / operation list only. Every such change is recorded here before running any method.

## Metrics
Per dataset and pooled (6 attacks: CADETS 3, THEIA 2, CLEARSCOPE 1, per PIDSMaker's configuration):
- attacks detected and ground-truth nodes found at 10 / 25 / 50 / 100 / 250 / 500 nodes;
- AUC and AP of Velox-lite.

## Gate G-E3 (all must hold)
1. Pooled attacks detected at 25 nodes: interleave > Velox-lite.
2. Pooled ground-truth nodes found at 50 nodes: interleave > Velox-lite.
3. Pooled attacks detected at 25 nodes: interleave >= knowledge only.
- 2026-11-01: bug fix in semantic_linux.py (empty process-creation table dropped the columns); no change to the rules. CLEARSCOPE_E3 has no EVENT_FORK/CLONE/EXECUTE rows, so only node rules apply there.
