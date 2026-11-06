# A3 rule ablation on CARBANAKv2 (fused = percentile + 0.1 x points; medians over seeds 0-4)

| Variant | GT nodes within 50 alerts | alerts to reach the attack |
|---|---|---|
| learned only | 0 [0-0] | 3035 [321-6387] |
| all rules | 5 [2-12] | 2 [1-3] |
| without execution | 4 [1-5] | 2 [1-6] |
| without proxy_lolbin | 6 [2-12] | 2 [1-3] |
| without discovery | 5 [2-12] | 2 [1-3] |
| without other_node | 8 [2-9] | 2 [1-3] |
| without doc_parent_edge | 5 [2-12] | 2 [1-3] |
| without interp_lolbin_edge | 9 [2-12] | 2 [1-36] |
