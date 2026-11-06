# Pilot P2 results: Unraveled test (single run of the frozen code, commit d75eb3a)

Numbers from `out_p2_unraveled/results.json` and the two `stage_vs_channel_*.csv` files.
Test 2021-06-08 .. 2021-07-06: 23,655 host-hours, 1,230 host-days, 60 positive host-days, 646 positive host-hours.

## Primary gate (hour level, budget B = 5 host-hours per day): FAILED (item 1)
| | Model | Volume | Host prior | Random (expected) |
|---|---|---|---|---|
| Host-day detection at B = 5 | **0.250** | 0.100 | 0.000 | 0.066 |
| Attack-hour recall at B = 5 | 0.033 | 0.020 | 0.000 | - |
| False alerts per day (of 5) | 4.28 | 4.55 | 5.00 | - |
| Host-hour AUC (secondary) | 0.761 | **0.805** | 0.370 | 0.5 |
1. detection >= 0.5 and >= 2x random: **no** (0.250; 3.8x random).
2. above volume and host prior: yes.
3. within-host hour AUC > 0.5 for the majority: yes (10.1.3.8 0.846; 10.1.3.17 0.785; 10.1.4.16 0.784; 10.1.5.21 0.503).

Detected host-days by host: 10.1.3.8 13/22; 10.1.3.17 1/12; 10.1.5.21 1/21; 10.1.4.16 0/5.

## Secondary (host-day level)
Host-day AUC: model 0.606 (95% bootstrap CI 0.550-0.661), volume 0.730, host prior 0.333.
recall@5 host-days 0.383 vs random 0.118.

## Explanation: channel of the attack hour vs ground-truth Stage (all 646 attack hours)
| Stage | c2 | exfil | recon | residual | lateral |
|---|---|---|---|---|---|
| Data Exfiltration | 0 | 233 | 36 | 0 | 0 |
| Establish Foothold | 0 | 104 | 133 | 0 | 0 |
| Lateral Movement | 2 | 84 | 29 | 6 | 0 |
| Reconnaissance | 8 | 7 | 1 | 0 | 0 |
| Cover up | 0 | 2 | 1 | 0 | 0 |
- Data Exfiltration hours are attributed to the exfil channel in 233 of 269.
- The lateral channel never fires: Unraveled's lateral movement uses ports 3306 and 80
  (`../audit/unraveled/out/attack_endpoints.csv`), outside the fixed admin-port list.

## What this shows
- There is attack signal beyond host identity (within-host AUC 0.78-0.85 for 3 of 4 hosts; host prior detects 0).
- The detector is not strong enough: 25% of attacked host-days at 5 alerts/day, and a plain volume ranking has
  a higher AUC.
- Hand-defined channel features are brittle (admin-port list; one C2 beacon per day is invisible).
