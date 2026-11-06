# Unraveled (DAPT2021): Phase 1 recon against gate G0

Date: 2026-10-30. Source: public S3 bucket `dapt2021.s3.amazonaws.com`, prefix `processed/network-flows/`
(173 NFStream CSV files, 3,723,532,930 bytes). Paper: Myneni et al., Computer Networks 2023, DOI 10.1016/j.comnet.2023.109688.
All numbers below are copied from `out/*.csv` (`recon_unraveled.py`, `split_check.py`); nothing is estimated.

## Inputs and integrity
- `MANIFEST.json`: size checked for all 173 files; MD5 = S3 ETag for the 103 single-part uploads (all OK);
  the other 70 are multipart uploads (no MD5 published), SHA-256 recorded.
- Labels: last 4 columns `Activity`, `Stage`, `DefenderResponse`, `Signature`.
- **Malformed rows: 13,169** (`malformed_rows` in `out/summary.csv`) have more fields than the header, because of
  unquoted commas in `user_agent` and fingerprint fields. A plain CSV reader shifts their labels (values such as
  "text/html" or "15" in `Activity`). The recon reads leading fields by position and the 4 labels from the end.

## Counts per capture point (`out/summary.csv`)
| Capture | Day folders | Flows | Attack flows (Stage != Benign) | Attack hosts | Benign source IPs |
|---|---|---|---|---|---|
| net1011x | 27 | 1,792,756 | 0 | 0 | 3,063 |
| net1012x | 28 | 734,331 | 0 | 0 | 529 |
| net1013x | 29 | 1,072,368 | 34,122 | 4 | 274 |
| net1014x | 29 | 210,371 | 2,948 | 2 | 37 |
| net1015x | 29 | 175,662 | 1,156 | 3 | 29 |
| netgw | 26 | 2,891,669 | 59,017 | 8 | 2,793 |

Attack flows by group (`Signature`): APT 63,125; AA 34,111. Stages: Reconnaissance 34,796; Lateral Movement 27,445;
Establish Foothold 27,118; Data Exfiltration 7,522; Cover up 362.

## Activities (`out/activity_profile.csv`)
13 distinct `Activity` values at attack rows, written as ATT&CK technique or sub-technique names without IDs
(e.g. "Encrypted Channel: Symmetric Cryptography", "Remote System Discovery", "Exfiltration over C2 channel")
plus two non-technique values ("Maintain Access", "Remove Traces").
Every activity has 1 source IP at every capture point except Remote System Discovery at netgw (2 source IPs),
and every activity belongs to exactly one attacker group.

## Gate G0
| Requirement | Result | Evidence |
|---|---|---|
| R1 technique labels per flow | pass, with caveat | `Activity` per flow; names, not IDs; 2 values are not techniques |
| R2 dst-port lookup not within 0.05 of GBDT | not run | R4 fails first; note 1 source IP per activity |
| R3 benign and attack flows share days | pass | `benign_flows_in_attack_folders` > 0 at every capture with attacks |
| R4 >= 4 techniques with >= 50 flows and >= 3 windows in every split | **fail** | chronological 60/20/20 split: 0 activities meet it in all 3 splits at any capture point (`out/r4_summary.csv`); a split by host is impossible (1 source IP per activity); a split by campaign is impossible (no activity in both groups) |
| R5 >= 20 hosts with benign traffic | pass | up to 3,063 benign source IPs |

**G0: Unraveled fails (R4).**
