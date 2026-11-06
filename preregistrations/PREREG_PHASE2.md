# REACH Phase 2 (test): pre-registration (FINAL)

Status: final, committed 2026-11-01 before any OpTC data is loaded and before any LANL test day (13-30) is evaluated.
Draft written 2026-10-31 (git history).

Deviation from the draft: lambda was to be chosen on CARBANAKv2. The Velox run on CARBANAKv2 failed twice on the
disk limit: the first run was stopped during feat_inference; the second failed in evaluation after its graph files
had been removed to free space. lambda = 0.1 by the draft's tie rule. ATLASv2 (dev, contaminated) also favoured 0.1.

## Methods compared (node ranking on each OpTC host)
1. Velox (PIDSMaker default config except `featurization.emb_dim = 32`, required by the disk limit; seeds as compute allows, at least seed 0; CPU).
2. Knowledge only: semantic points (`semantic.py`, family "optc"), ties broken by the Velox percentile.
3. REACH fused: Velox percentile + lambda x semantic points.
   - lambda = 0.1.

## Fixed before OpTC is loaded
- `semantic.py` rules and the process-creation operation names for OpTC, `CREATE_OPS["optc"]`. If the OpTC event
  table uses another name for process creation, the mapping is corrected once, from the table's operation list
  only, before looking at any ground truth, and the change is recorded.
- No change to Velox's configuration.

## Metrics (per host, median over seeds)
- Attacks detected and ground-truth nodes found at budgets of 10 / 25 / 50 / 100 nodes.
- AP and AUC of the node ranking.
- PIDSMaker's own metrics for Velox.

## Gate G1/G2 (all must hold)
1. REACH fused detects at least as many attacks as Velox at 25 and at 50 nodes on all three hosts, and more on at
   least one.
2. REACH fused finds more ground-truth nodes than Velox at 50 nodes, pooled over the three hosts.
3. REACH fused finds at least as many ground-truth nodes as knowledge-only at 50 nodes, pooled
   (both components contribute).

## L3 blast radius on LANL (test days 13-30)
- Methods: `blast_radius.py` with tau = 7 days, alpha = 0.15, user table `auth_users_daily.parquet`;
  compared: random, degree, bfs1, ppr, cred_after.
- Gate G3: cred_after recall@50 > degree recall@50 AND cred_after recall@100 > degree recall@100, pooled over the
  test days.

## Run order
1. LANL test (cheap).
2. OpTC h501, h051, h201: one at a time, each restored from its dump, Velox (emb 32) seed 0; more seeds if time and
   disk allow. A host that cannot be run on this machine is reported as such.

## Deviation 2 (2026-11-01, before any OpTC run of any method)
PIDSMaker's Velox cannot run on OpTC here: an estimated 22 GB of artifacts for h501 (28M events) against
15 GB of free disk. Velox is replaced by Velox-lite (`velox_lite.py`), a disk-light re-implementation with the
same features, model and node score; the differences are listed in its docstring.

Validation on ATLASv2 (development data), seed 0, evaluated with `eval_ranking.py`:
| | AUC | AP | fused attacks@10/25/50 |
|---|---|---|---|
| PIDSMaker Velox (emb 32) | 0.864 | 0.0173 | 7/10/10 |
| Velox-lite | 0.836 | 0.0047 | 7/8/9 |

Velox-lite is weaker than PIDSMaker's Velox; it is reported as "Velox-lite". The gates are unchanged, with
Velox-lite in place of Velox.
