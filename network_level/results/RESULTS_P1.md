# Pilot P1 results (DEDALE green_internal)

Numbers from `out/results.json`, `out/positive_host_days.csv`, `out/within_host_check.txt`.
Code: `features.py`, `run_p1.py`; pyod 3.6.7, pandas 3.0.5, seed 42.

## Pre-registered gate: formally PASSED
| | Model | Volume baseline | Random (expected) |
|---|---|---|---|
| recall@10 (11 positive host-days) | 0.727 | 0.364 | 0.438 |
| recall@3 | 0.545 | 0.182 | 0.259 |
| mean rank | 6.9 | 17.4 | - |
All 3 compromised hosts appear in the model's top 10 on at least one positive day.

## Post-hoc check: the pass is NOT evidence of detection
Within-host comparison (`out/within_host_check.txt`):
| Host | Role | Median rank, attack days | Median rank, other test days | Days in top 10, attack / other |
|---|---|---|---|---|
| 172.16.0.2 | internal server, LM target | 1 | 1 | 2/2, 12/12 |
| 172.16.1.2 | client1, compromised via PrintNightmare | 3 | 3 | 5/6, 6/8 |
| 172.16.1.3 | client2, first victim | 13 | 14 | 1/3, 2/7 |

- The server ranks 1st on every test day with or without attack. It never initiates flows (`flows_out` = 0 in all
  162 train/calibration host-hours), so its all-zero feature vector is rare among the pooled client host-hours and
  gets p = 0.014 in every hour; summing over its ~13 hours per day puts it first.
- client1 ranks in the top 3 on most days, attacked or not; its scores are not higher on attack days.
- client2 is not in the top 10 on the day of initial access (rank 16) nor the next day (rank 13).
The model ranks host types, not attacks. Gate P1 did not control for this: it had no within-host or
attack-free-day comparison, and with 32 hosts a top-10 budget is about one third of the network.

## Causes (design, identified after the run)
1. One model pooled over all hosts: host role (server vs client) dominates the score.
2. Host-day score = sum over hours: favours hosts with more active hours.
3. Gate without a negative control (same host on attack-free days).

## Deviations from PILOT.md
None in the run. The within-host table, recall@3, recall@1 and mean rank were added after seeing results.

## Consequence
DEDALE's single campaign has now been used for evaluation; a corrected design cannot be tested on it again
without the result being contaminated. A follow-up must be pre-registered and tested on data not yet used for
any model run (Unraveled), with DEDALE as development data.
