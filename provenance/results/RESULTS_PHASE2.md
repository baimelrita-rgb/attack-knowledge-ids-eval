# REACH Phase 2 results: OpTC h501, h051, h201 (single run of the frozen configuration, seed 0)

Pre-registration: PREREG_PHASE2.md (lambda 0.1; Velox replaced by Velox-lite, deviation 2).
Numbers from `results_optc_*_eval.json`. Ranked population = nodes with >= 1 test event (about 1.4-1.5M per host).

| Host | Attack nodes (process / netflow / file) | Method | Attack detected at 10 / 25 / 50 / 100 nodes | Attack nodes found at 10 / 50 / 100 / 500 | AUC | AP |
|---|---|---|---|---|---|---|
| h501 | 749 (23 / 700 / 26) | Velox-lite | 1 / 1 / 1 / 1 | 2 / 2 / 2 / 4 | 0.723 | 0.0072 |
| | | knowledge only | 0 / 1 / 1 / 1 | 0 / 2 / 2 / 6 | 0.723 | 0.0065 |
| | | REACH fused | 0 / 1 / 1 / 1 | 0 / 2 / 2 / 6 | 0.723 | 0.0065 |
| h051 | 114 (59 / 49 / 6) | Velox-lite | 0 / 0 / 0 / 1 | 0 / 0 / 1 / 25 | 0.858 | 0.0225 |
| | | knowledge only | 1 / 1 / 1 / 1 | 3 / 4 / 7 / 30 | 0.871 | 0.0346 |
| | | REACH fused | 1 / 1 / 1 / 1 | 3 / 4 / 4 / 27 | 0.859 | 0.0315 |
| h201 | 2,905 (42 / 2,858 / 5) | Velox-lite | 0 / 1 / 1 / 1 | 0 / 1 / 1 / 6 | 0.732 | 0.0206 |
| | | knowledge only | 0 / 0 / 1 / 1 | 0 / 1 / 4 / 8 | 0.732 | 0.0206 |
| | | REACH fused | 0 / 0 / 1 / 1 | 0 / 1 / 4 / 8 | 0.732 | 0.0206 |

## Gate (PREREG_PHASE2.md): FAILED
1. Fused detects >= Velox-lite at 25 and 50 nodes on all hosts, and more on at least one: **no**.
   On h201 at 25 nodes: fused 0, Velox-lite 1. More on h051 (1 vs 0 at 25 and 50).
2. Fused finds more attack nodes than Velox-lite at 50, pooled: yes (7 vs 3).
3. Fused >= knowledge only at 50, pooled: yes (7 vs 7).

## Reading
- The knowledge prior scores processes only. On OpTC the ground truth is dominated by network-connection nodes
  (h501 700/749, h201 2,858/2,905). Only 2/23, 7/59 and 5/42 of the ground-truth processes get points.
- Where processes dominate the attack (h051), knowledge finds the attack at 10 nodes; Velox-lite needs 100.
- Pooled over the three hosts, at 100 nodes: fused 10 attack nodes, knowledge only 15, Velox-lite 4.
- AUC is unchanged by fusion (the prior moves only a few hundred processes among about 1.4M nodes).
- Velox-lite is weaker than PIDSMaker's Velox on ATLASv2 (AUC 0.836 vs 0.864), so Velox numbers here may
  understate the original system.
