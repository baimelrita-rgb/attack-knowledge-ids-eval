# Pilot P2: per-host tactic channels, test on Unraveled (pre-registered)

Committed together with the frozen code (`flows.py`, `features.py`, `run_p2.py`) before any model run on
Unraveled. Unraveled was used before only for label/count descriptives (`../audit/unraveled/`) and for the
host/day ground-truth table quoted below. The gate is not changed after the run.

## Why P2
P1 (RESULTS_P1.md) ranked host types, not attacks: one model pooled over hosts, a sum over hours, and no
negative control. DEDALE is now development data only.

## Development log on DEDALE (all rounds, in order; dev results in `out_p2_dev_dedale/`)
1. Per-host one-sided ECOD (each host compared with its own training hours; fallback to all hosts if < 24 hours),
   max-hour daily score, host-day gate. Host-day AUC 0.396; server no longer ranked 1st (median rank 31).
   Diagnosis: 246 of 3,770 test host-hours tied at the conformal floor (only 420 calibration hours).
2. Cross-fitted calibration (training days split by parity; 3,407 calibration scores). Floor ties 16;
   host-day AUC 0.539 (95% CI 0.364-0.708). Lateral-movement hours of both clients rank 1st of 364 on 2025-01-08.
   7 of 11 positive host-days contain only C2 beacons (1-2 flows), which a flow-aggregate detector cannot see.
3. Primary evaluation moved to host-hours under a daily alert budget B = 5 (gate written in code before this
   round's run). DEDALE dev: host-day detection 0.364 (4/11) vs random 0.042, volume 0.182, host prior 0.182;
   within-host hour AUC client1 0.916, client2 0.557. Dev gate: item 1 fails (0.364 < 0.5), items 2-3 pass.
No further change after round 3.

## Model (frozen)
Features per (host, hour) as in PILOT.md (online novelty history). Channels: recon, c2, lateral, exfil, residual.
Per-host one-sided ECOD channel scores; conformal p-values from cross-fitted calibration; hour score =
-log10(min channel p x 5); daily alert list = top B = 5 host-hours of the day.

## Data: Unraveled
- Captures net1011x .. net1015x (one per internal /24 subnet); each capture describes the hosts of its subnet.
  netgw excluded (gateway, NAT). Internal network 10.1.0.0/16; 55 internal hosts, 35-54 active per day.
- 2021-05-26 and 2021-05-27 dropped entirely (they contain attack flows and precede any attack-free day).
- Train 2021-05-28 .. 2021-06-04; calibration 2021-06-05 .. 2021-06-07 (no attack flow on these days);
  test 2021-06-08 .. 2021-07-06.
- Ground truth: a (host, hour) is positive if the host is source or destination of a flow with Stage != Benign.
  Positive hosts in test: 10.1.3.8, 10.1.3.17, 10.1.5.21, 10.1.4.16.

## Gate P2 (primary, hour level; all three must hold)
1. Host-day detection at B = 5 (share of positive host-days with at least one attack hour in the day's top 5)
   >= 0.5 and >= 2 x the random expectation;
2. host-day detection at B = 5 above both the volume baseline (flows out per host-hour) and the host-prior
   baseline (host's mean calibration score, constant per host);
3. within-host control: among positive hosts with >= 3 attack hours, the majority have hour-level AUC > 0.5
   (attack hours vs the same host's other test hours).
Secondary, reported: host-day AUC with bootstrap CI, recall@5 host-days, channel of the best hour per positive
host-day vs ground-truth Activity/Stage, false alerts per day.

## If the gate fails
Report as measured; no tuning on Unraveled.
