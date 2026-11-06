# REACH Phase 3 results: DARPA TC E3 (single run of the frozen methods of PREREG_PHASE3.md, seed 0)

Attacks detected / ground-truth nodes found at 10 / 25 / 50 / 100 / 250 / 500 nodes (`results_phase3_*.json`):
| Dataset (attacks, GT nodes) | Velox-lite AUC | Velox-lite | knowledge | sum | interleave |
|---|---|---|---|---|---|
| CLEARSCOPE (1, 41) | 0.196 | 0/0 0/0 0/0 1/1 1/1 1/1 | identical (0 processes with points) | identical | identical |
| CADETS (3, 72) | 0.979 | 0/0 0/0 2/4 3/10 3/14 3/22 | 0/0 0/0 0/0 0/0 0/0 3/16 | 0/0 0/0 0/0 0/0 0/0 3/16 | 0/0 0/0 0/0 2/4 3/10 3/15 |
| THEIA (2, 118) | 0.572 | 1/1 1/1 1/1 1/1 1/1 2/11 | 0/0 for all budgets | 0/0 for all budgets | 1/1 1/1 1/1 1/1 1/1 1/1 |

Pooled:
| Method | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 |
|---|---|---|---|---|
| Velox-lite | 1 | 3 | 5 | 5 |
| knowledge only | 0 | 0 | 1 | 0 |
| sum | 0 | 0 | 1 | 0 |
| interleave | 1 | 1 | 4 | 1 |

## Gate G-E3: FAILED
1. Interleave > Velox-lite at 25: no (1 vs 1).
2. Interleave > Velox-lite in GT nodes at 50: no (1 vs 5).
3. Interleave >= knowledge only at 25: yes (1 vs 0).

## Reading
- The Linux rules mark many benign processes: 13,291 test-population processes on THEIA and 240 on CADETS.
  They do not rank attack processes early.
- On Android (CLEARSCOPE) no process matches.
- The learned detector is better on these datasets; interleaving costs it half of its budget.
