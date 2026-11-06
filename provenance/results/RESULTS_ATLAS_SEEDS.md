# ATLASv2 (development): Velox-lite seeds 0-4, lambda = 0.1

| Method | attacks@10 | attacks@25 | attacks@50 | GT nodes@50 | AUC |
|---|---|---|---|---|---|
| velox | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0.843 [0.836-0.848] |
| knowledge_only | 3 [2-3] | 8 [7-9] | 9 [9-10] | 26 [14-29] | 1.000 [1.000-1.000] |
| fused | 7 [5-7] | 9 [8-10] | 10 [9-10] | 26 [16-28] | 0.891 [0.890-0.901] |

Per seed fused attacks@10: [7, 5, 7, 6, 7] of 10
