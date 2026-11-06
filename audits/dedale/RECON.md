# DEDALE: Phase 1 recon against gate G0

Date: 2026-10-30. Source: Recherche Data Gouv, DOI 10.57745/Y5JLDG (dataset v2.1).
All numbers below are copied from `out/*.csv` produced by `recon_dedale.py`; nothing is estimated.

## Inputs
- Files and checksums: `MANIFEST.json` (MD5 checked against `file_list.csv`, all 8 OK; SHA-256 recorded).
  Zeek archives audited: `zeek_orange_dmz.zip`, `zeek_router1.zip` (interfaces green, orange, red),
  `zeek_green_internal.zip`, `zeek_orange_servers.zip`. pcap and CICFlowMeter archives not downloaded.
- Network labels: column `label` (0 benign, 1 attack, 2 attack-related) plus `tactic`, `technique`, `step`
  in each daily `conn_labeled.csv`. They are assigned by the authors' script from hard-coded attack-step
  timestamps (`gitlab.inria.fr/mlanvin/dedale_labeling`, commit f148722eb5908fc17841dc3c8be1591c5c3e59a6,
  `network_log_labeling/labelling_script_on_single_conn.log.py`, 17 `set_labels` calls).
- Host labels (`system_logs_labels.zip`): 4 JSONL files of malicious events, classes "1" and "1 and 2";
  no technique field (29,758 lines in total).

## Counts per capture point (`out/*_summary.csv`)
| Capture point | Days | Flows | label != 0 | Attack days | Benign flows on attack days | Benign source IPs |
|---|---|---|---|---|---|---|
| green_internal | 28 | 16,274,434 | 93 | 8 | 4,826,033 | 94 |
| orange_servers | 28 | 17,191,119 | 9 | 2 | 1,716,563 | 38 |
| orange_dmz | 28 | 839,054 | 2 | 1 | 45,132 | 75 |
| router1_green | 28 | 11,398,227 | 81 | 8 | 3,336,725 | 70 |
| router1_orange | 28 | 836,963 | 2 | 1 | 44,993 | 76 |
| router1_red | 28 | 11,790,693 | 1 | 1 | 573,712 | 56 |

## Flows per technique, largest capture point (green_internal, `out/green_internal_technique_profile.csv`)
| Technique | Flows | Days | 1-h windows | Distinct dst ports |
|---|---|---|---|---|
| T1104 | 38 | 2 | 2 | 1 (443) |
| T1102 | 19 | 8 | 9 | 1 (443) |
| T1005 | 5 | 1 | 1 | 1 (22) |
| T1210 | 4 | 1 | 1 | 3 |
| T1041 | 2 | 1 | 1 | 1 (443) |
| T1105 | 1 | 1 | 1 | 1 (80) |
| T1135 | 1 | 1 | 1 | 1 (445) |
| T1566 | 1 | 1 | 1 | 1 (993) |
| label 2, no technique | 22 | 1 | 1 | 1 (80) |

## Gate G0
| Requirement | Result | Evidence |
|---|---|---|
| R1 technique labels per flow | pass | `technique` column, 8 ATT&CK techniques |
| R2 dst-port lookup not within 0.05 of GBDT | not measurable | at most 38 flows per technique; every technique except T1210 uses a single dst port |
| R3 benign and attack flows share days | pass | benign flows on attack days, table above |
| R4 >= 4 techniques with >= 50 flows and >= 3 windows in every split | **fail** | 0 techniques reach 50 flows at any capture point (maximum 38, T1104) |
| R5 >= 20 hosts with benign traffic | pass | 94 benign source IPs (green_internal) |

The dataset contains one attack campaign, so no split by campaign exists, and the attack touches
at most 7 hosts at any capture point (`attack_hosts_src_or_dst` in `out/*_summary.csv`).

**G0: DEDALE fails (R4).** Its network part cannot train or test a per-technique detector.
What DEDALE does support: 2 attack-free weeks plus 2 weeks of benign traffic on 38-94 hosts (enough room
to inject attacks for Predict), and one real, documented multi-step chain (phishing -> C2 -> PrintNightmare
lateral movement -> collection -> exfiltration) with timestamps.
