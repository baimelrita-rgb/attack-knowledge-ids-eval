# Velox-lite over seeds 0-4

## OpTC (Windows): median [min-max] over seeds

### OPTC_H501 (seeds [0, 1, 2, 3, 4])

| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |
|---|---|---|---|---|---|---|
| learned | 1 [1-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 2 [1-2] | 2 [1-3] |
| knowledge | 0 [0-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 2 [2-2] | 2 [2-2] |
| sum | 0 [0-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 2 [2-2] | 2 [2-2] |

Velox-lite AUC: median 0.723 [0.642-0.735]

### OPTC_H051 (seeds [0, 1, 2, 3, 4])

| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |
|---|---|---|---|---|---|---|
| learned | 0 [0-0] | 0 [0-0] | 0 [0-1] | 0 [0-1] | 0 [0-1] | 0 [0-1] |
| knowledge | 1 [1-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 4 [4-4] | 7 [7-7] |
| sum | 1 [1-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 4 [4-4] | 4 [4-4] |

Velox-lite AUC: median 0.859 [0.798-0.923]

### OPTC_H201 (seeds [0, 1, 2, 3, 4])

| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |
|---|---|---|---|---|---|---|
| learned | 0 [0-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 1 [1-1] | 1 [1-2] |
| knowledge | 0 [0-0] | 0 [0-0] | 1 [0-1] | 1 [1-1] | 1 [0-1] | 3 [1-4] |
| sum | 0 [0-0] | 0 [0-0] | 1 [0-1] | 1 [1-1] | 1 [0-1] | 3 [1-4] |

Velox-lite AUC: median 0.728 [0.520-0.732]


## DARPA TC E3: median [min-max] over seeds

### CLEARSCOPE_E3 (seeds [0, 1, 2, 3, 4])

| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |
|---|---|---|---|---|---|---|
| learned | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-1] | 0 [0-0] | 0 [0-1] |
| knowledge | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-1] | 0 [0-0] | 0 [0-1] |
| sum | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-1] | 0 [0-0] | 0 [0-1] |
| interleave | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-1] | 0 [0-0] | 0 [0-1] |

Velox-lite AUC: median 0.162 [0.089-0.196]

### CADETS_E3 (seeds [0, 1, 2, 3, 4])

| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |
|---|---|---|---|---|---|---|
| learned | 0 [0-0] | 0 [0-2] | 3 [2-3] | 3 [3-3] | 5 [2-15] | 10 [8-24] |
| knowledge | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] |
| sum | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] |
| interleave | 0 [0-0] | 0 [0-0] | 0 [0-2] | 3 [2-3] | 0 [0-4] | 5 [2-15] |

Velox-lite AUC: median 0.969 [0.957-0.979]

### THEIA_E3 (seeds [0, 1, 2, 3, 4])

| Method | attacks@10 | attacks@25 | attacks@50 | attacks@100 | GT nodes@50 | GT nodes@100 |
|---|---|---|---|---|---|---|
| learned | 1 [0-1] | 1 [1-1] | 1 [1-2] | 1 [1-2] | 1 [1-4] | 1 [1-11] |
| knowledge | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] |
| sum | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] | 0 [0-0] |
| interleave | 1 [0-1] | 1 [1-1] | 1 [1-1] | 1 [1-2] | 1 [1-1] | 1 [1-4] |

Velox-lite AUC: median 0.630 [0.572-0.697]


## Gate quantities per seed (descriptive; the pre-registered decision is seed 0)

| Phase / seed | G1 | G2 | G3 | pooled values |
|---|---|---|---|---|
| E3_seed0 | False | False | True | {'velox': 3, 'knowledge': 0, 'sum': 0, 'interleave': 1} |
| OpTC_seed0 | False | True | True | {'velox': 3, 'knowledge_only': 7, 'fused': 7} |
| E3_seed1 | False | False | True | {'velox': 5, 'knowledge': 0, 'sum': 0, 'interleave': 1} |
| OpTC_seed1 | False | True | True | {'velox': 3, 'knowledge_only': 7, 'fused': 7} |
| E3_seed2 | False | False | True | {'velox': 4, 'knowledge': 0, 'sum': 0, 'interleave': 1} |
| OpTC_seed2 | False | True | True | {'velox': 3, 'knowledge_only': 7, 'fused': 7} |
| E3_seed3 | False | False | True | {'velox': 4, 'knowledge': 0, 'sum': 0, 'interleave': 3} |
| OpTC_seed3 | False | True | True | {'velox': 3, 'knowledge_only': 6, 'fused': 6} |
| E3_seed4 | False | False | True | {'velox': 3, 'knowledge': 0, 'sum': 0, 'interleave': 1} |
| OpTC_seed4 | False | True | True | {'velox': 2, 'knowledge_only': 7, 'fused': 7} |
