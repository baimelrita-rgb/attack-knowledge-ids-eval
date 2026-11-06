# Pilot P1: label-free, tactic-channel detection on DEDALE (pre-registered)

Written and committed before any model was run on test data. Changes after the run are listed at the end
under "Deviations" with the reason; the gate below is not changed after seeing results.

## Question
Without any attack label in training, does a set of per-tactic anomaly channels, calibrated on benign
traffic, rank the compromised internal hosts among the top 10 hosts of each day?

## Data
- DEDALE `zeek_green_internal.zip`, all daily `conn_labeled.csv` (28 days, 16,274,434 flows).
- Entities: internal hosts, IPv4 in 172.16.0.0/16, that appear as source or destination.
- Window: 1 hour (UTC). Day: UTC calendar day.
- Train: 2024-12-24 .. 2025-01-02 (2024-12-23 is used only as novelty history).
  Calibration: 2025-01-03 .. 2025-01-05. Test: 2025-01-06 .. 2025-01-19.
  Train and calibration contain no attack flow (`out/green_internal_rows_by_day_label.csv`).
- Labels are read only to build the evaluation ground truth on test days.

## Ground truth
A test (host, day) is positive if the host is source or destination of at least one flow with `label == 1`
on that day. Expected hosts: 172.16.1.3, 172.16.1.2, 172.16.0.2 (from `out/green_internal_attack_endpoints.csv`).

## Features per (host, hour)  (log1p applied to counts and bytes)
"New" = not seen in any earlier day (online history, grows day by day, same rule in train, calibration, test).
External = destination outside 172.16.0.0/16. Admin ports = {22, 135, 139, 445, 3389, 5985, 5986}.
- Recon: distinct destination IPs; distinct destination ports; share of outgoing flows with conn_state in {S0, REJ}.
- C2: new external destinations; flows to new external destinations; bytes sent to new external destinations.
- Lateral movement: new (src, dst, port) internal admin-port edges as source; same as destination;
  flows on admin ports to internal peers.
- Exfiltration: bytes sent to external destinations; log ratio bytes sent / (bytes received + 1) to external destinations.
- Residual: all of the above together.

## Model
- One ECOD model (pyod) per channel, fitted on train host-hours pooled over hosts.
- Conformal p-value per channel: p = (1 + #{calibration scores >= s}) / (n_cal + 1).
- Hour score: p_min = min over the 5 channels, times 5 (Bonferroni), capped at 1.
- Host-day score: sum over the day's hours of -log10(p_min). Hours without traffic contribute 0.
- Per day, hosts are ranked by host-day score; the alert budget is the top 10.
- Seed: 42 (ECOD is deterministic; seed fixed for completeness).

## Baselines (same ranking, same budget)
- Volume: host-day score = number of flows with the host as source.
- Random: expected recall@10 = mean over positive host-days of min(1, 10 / hosts active that day).

## Gate P1 (all three must hold)
1. recall@10 over positive test host-days >= 0.5;
2. each of the 3 expected hosts is in the top 10 on at least one of its positive days;
3. recall@10 of the model > recall@10 of the volume baseline.

## Reported regardless of the gate
Per positive host-day: rank, score, channel with the smallest p-value, ground-truth techniques/tactics of that day;
number of top-10 slots per day taken by non-positive hosts; the same table for the volume baseline.

## If the gate fails
Report the result as measured. No feature, window or threshold is tuned on the test days.

## Deviations
(none yet)
Run on 2026-10-30; results and a post-hoc check in RESULTS_P1.md (gate formally passed; post-hoc check shows
the ranking reflects host role, not the attack).
