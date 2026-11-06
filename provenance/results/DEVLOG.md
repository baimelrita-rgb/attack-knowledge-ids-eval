# REACH Phase 1 development log (dev data only: ATLASv2-EDR, CARBANAKv2-EDR, LANL days 2-12)

## Disclosure
- ATLASv2 per-attack ground-truth nodes were listed (process paths and Velox ranks) before the semantic rules
  were written. Generic Sigma/ATT&CK patterns were used, but the list of "document parent" processes includes
  Firefox `plugin-container.exe`, chosen after seeing it among the ground-truth nodes. ATLASv2 results of the
  semantic prior are therefore optimistic. CARBANAKv2 ground truth has not been looked at.

## L1/L2 on ATLASv2 (Velox seed 0, best epoch 11; AUC 0.881, AP 0.0143, 0 TP at the PIDSMaker threshold)
| Round | Change | Attacks detected (of 10) at budget 10 / 25 / 50 / 100 / 250 / 500 nodes |
|---|---|---|
| baseline | Velox flat top-N | 1 / 1 / 1 / 2 / 2 / 4 |
| L2-r1 | incidents: expansion of seeds (window 30 min, top-1% neighbours, depth 2), no cap | 1 / 1 / 1 / 1 / 1 / 1 (worse: the first incident fills the budget) |
| L1-r2 | fused rank = Velox percentile + 0.1 x semantic points (`semantic.py`) | 7 / 10 / 10 / 10 / 10 / 10 |
| L1-r2 | lambda 0.25 / 0.5 / 1.0 | 3 / 2 / 2 at budget 10; 10 at budget >= 25 |
| L1-r2 | semantic points only (ties broken by Velox) | 2 / 10 / 10 / 10 / 10 / 10 |
Semantic prior: 401 of 66,897 processes get points; all 48 ground-truth nodes get points.

## L3 on LANL, dev days 2-12 (`lanl/l3_dev_r1.json`; tau 7 days, alpha 0.15; 194 first-compromise targets)
| Method | recall@10 | recall@50 | recall@100 | MRR |
|---|---|---|---|---|
| random | 0.001 | 0.004 | 0.008 | - |
| degree | 0.031 | 0.088 | 0.144 | 0.0126 |
| bfs1 | 0.026 | 0.082 | 0.088 | 0.0116 |
| ppr | 0.021 | 0.082 | 0.113 | 0.0103 |
Day 9 holds 170 of the 194 targets. The machine-level graph has no user identity; a user-level credential-exposure
graph (BloodHound-style sessions) is being built (`lanl/aggregate_auth_users.py`).

## L2-r3 on ATLASv2 (incidents with a per-incident cap; seed 0)
Attacks detected / ground-truth nodes found at budgets 10 / 25 / 50 / 100 / 250 / 500:
| Ranking | flat | incidents cap 3 | incidents cap 5 |
|---|---|---|---|
| Velox | 1/1, 1/1, 1/1, 2/2, 2/2, 4/5 | 1/1, 1/1, 1/1, 1/1, 2/2, 3/4 | same as cap 3 |
| fused (lambda 0.1) | 7/7, 10/15, 10/25, 10/30, 10/30, 10/34 | 3/5, 7/11, 10/19, 10/30, 10/33, 10/34 | 2/4, 5/7, 8/12, 10/28, 10/33, 10/34 |
Decision: incident expansion does not improve detection over the flat fused list; incidents are kept only as the
presentation layer (grouping + ATT&CK tags), and the detection comparison uses the flat fused ranking.

## L3 on LANL, dev days 2-12, rounds 2-3 (`lanl/l3_dev_r2.json`, `lanl/l3_dev_r3.json`)
User-level table: days 1-30, successful LogOn by non-machine accounts, 78,349,681 events -> 2,445,791 rows.
| Method | recall@10 | recall@50 | recall@100 |
|---|---|---|---|
| degree | 0.031 | 0.088 | 0.144 |
| ppr | 0.021 | 0.082 | 0.113 |
| cred (users with any session on/from a known host) | 0.031 | 0.098 | 0.144 |
| cred_rt (+ red-team accounts seen before) | 0.031 | 0.098 | 0.144 |
| cred_after (session on a host after its first red-team event) | 0.031 | **0.108** | **0.155** |
Diagnostics, day 9 (170 of 194 targets):
- The attacker logged on from C17693 with 43 accounts.
- 40 of the 43 had sessions on/from known hosts before day 9, but so did 9,008 users.
- The 284 hosts those 43 accounts accessed before day 9 contain 77 of the 170 targets.
- Exposure is real but diluted.
Decision: L3 development stops here (6 dev days, one day dominates). Test comparison: cred_after vs degree.

## Disk limit and Velox embedding size (2026-11-01)
- Velox's default `featurization.emb_dim = 128` stores two 128-d vectors per event in `feat_inference`.
  On CARBANAKv2 (17,143,304 events) this passed 8.1 GB and was growing when stopped; the environment has
  about 40 GB in total.
- Decision: all further Velox runs use `--featurization.emb_dim 32` (`run_seeds_small.sh`). The baseline is
  reported as "Velox (emb 32)".
- Check on ATLASv2, seed 0:

  | | AUC | AP | ADP | TP at threshold |
  |---|---|---|---|---|
  | emb 128 | 0.881 | 0.0143 | 0.057 | 0 |
  | emb 32 | 0.885 | 0.0160 | 0.109 | 1 |

- Fused ranking with emb 32, attacks detected at budgets 10 / 25 / 50 / 100 / 250 / 500:
  - lambda 0 (Velox only): 1 / 1 / 1 / 1 / 1 / 4;
  - lambda 0.1: 7 / 10 / 10 / 10 / 10 / 10;
  - lambda 0.25: 6 / 10 / 10 / 10 / 10 / 10.

## REACH v2 development (all data seen; `../data_raw/reach_runs/v2dev/`)
Attacks detected at 10 / 25 / 50 nodes:

| | Velox-lite | sum (lambda 0.1) | interleave | sum + propagation | interleave + propagation |
|---|---|---|---|---|---|
| OpTC h501 | 1/1/1 | 0/1/1 | 1/1/1 | 0/1/1 | 1/1/1 |
| OpTC h051 | 0/0/0 | 1/1/1 | 1/1/1 | 1/1/1 | 1/1/1 |
| OpTC h201 | 0/1/1 | 0/0/1 | 0/0/1 | 0/0/1 | 0/0/1 |
| ATLASv2 (10 attacks) | 0/0/0 | 7/8/9 | 1/4/8 | 5/8/9 | 1/4/7 |

Ground-truth nodes at 500 nodes with propagation (gamma 0.5, depth 2):
- higher on h201 (11-12 vs 8);
- lower on h051 (13-18 vs 27-30) and on ATLASv2.

Decision: propagation not used; interleave is the primary fusion for Phase 3, the sum is reported alongside.
