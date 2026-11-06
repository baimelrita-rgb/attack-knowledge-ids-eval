# Choice of dataset D for Detect -> Explain (gate G0), 2026-10-30

Each row is copied from that dataset's RECON.md; nothing is estimated.

| Dataset | R1 technique labels | R3 benign & attack share days | R4 >= 4 techniques, >= 50 flows, >= 3 windows, every split | R5 >= 20 benign hosts | G0 |
|---|---|---|---|---|---|
| UWF-ZeekData24 (`analysis_uwf/RECON.md`, other branch) | yes (5 techniques) | **no**: 0 shared days (benign Oct-Nov 2024, attacks Feb-Mar 2024) | not run | not run | fail (R3) |
| DEDALE (`dedale/RECON.md`) | yes (8 techniques) | yes | **no**: max 38 flows per technique, 1 campaign | yes (94) | fail (R4) |
| Unraveled (`unraveled/RECON.md`) | yes, names (13 values) | yes | **no**: 0 activities in all 3 chronological splits; 1 source IP per activity; no activity in both groups | yes | fail (R4) |

Result: no audited dataset passes G0. Per PAPER_PLAN_WAY3.md, the decision on how to continue is the user's.
