# RQ2 mechanism analysis (exploratory; PLAN_MECHANISM.md)

## Per dataset (median over five seeds; ground-truth nodes within 50 alerts)

| Dataset | GT process share | rule coverage of GT processes | selectivity | learned AUC | learned | knowledge | fused | gain | GT processes@50 learned / knowledge / fused |
|---|---|---|---|---|---|---|---|---|---|
| ATLASV2_EDR | 1.00 | 1.00 | 0.0172 | 0.843 | 0 | 26 | 26 | +26 | 0 / 26 / 26 |
| OPTC_H501 | 0.03 | 0.09 | 0.0084 | 0.723 | 2 | 2 | 2 | +0 | 2 / 2 / 2 |
| OPTC_H051 | 0.52 | 0.12 | 0.0060 | 0.859 | 0 | 4 | 4 | +4 | 0 / 4 / 4 |
| OPTC_H201 | 0.01 | 0.12 | 0.0091 | 0.728 | 1 | 1 | 1 | +0 | 1 / 1 / 1 |
| CADETS_E3 | 0.54 | 0.00 | 0.0031 | 0.969 | 5 | 0 | 0 | -5 | 2 / 0 / 0 |
| THEIA_E3 | 0.81 | 0.00 | 0.1246 | 0.630 | 1 | 0 | 0 | -1 | 0 / 0 / 0 |
| CLEARSCOPE_E3 | 0.02 | 0.00 | 0.0000 | 0.162 | 0 | 0 | 0 | +0 | 0 / 0 / 0 |
| CARBANAKV2_EDR (rules only) | 1.00 | 0.50 | 0.0304 | - | - | - | - | - | - |

## Correlations over the seven datasets (exact permutation p, two-sided)

- H2 coverage of GT processes vs gain: rho = 0.81, p = 0.043
- H3 learned AUC vs gain: rho = 0.07, p = 0.879
- GT process share vs gain: rho = 0.07, p = 0.879

## H4: alerts needed to reach each attack (median over seeds)

| Group | attacks | fused better | learned better | ties | median rank fused | learned | knowledge | Wilcoxon p |
|---|---|---|---|---|---|---|---|---|
| other | 8 | 0 | 7 | 1 | 271 | 34 | 275 | 0.016 |
| win_process_centric | 11 | 11 | 0 | 0 | 5 | 2698 | 11 | 0.001 |

### Per attack

| Dataset | attack | learned | knowledge | fused |
|---|---|---|---|---|
| ATLASV2_EDR | 0 | 4092 | 61 | 50 |
| ATLASV2_EDR | 1 | 3094 | 11 | 5 |
| ATLASV2_EDR | 2 | 2688 | 27 | 19 |
| ATLASV2_EDR | 3 | 929 | 14 | 9 |
| ATLASV2_EDR | 4 | 3092 | 11 | 3 |
| ATLASV2_EDR | 5 | 3096 | 10 | 3 |
| ATLASV2_EDR | 6 | 3090 | 10 | 4 |
| ATLASV2_EDR | 7 | 2698 | 1 | 1 |
| ATLASV2_EDR | 8 | 931 | 15 | 11 |
| ATLASV2_EDR | 9 | 344 | 19 | 13 |
| CADETS_E3 | 0 | 42 | 276 | 274 |
| CADETS_E3 | 1 | 34 | 275 | 271 |
| CADETS_E3 | 2 | 35 | 275 | 271 |
| CLEARSCOPE_E3 | 0 | 196 | 196 | 196 |
| OPTC_H051 | 0 | 105 | 4 | 4 |
| OPTC_H201 | 0 | 13 | 41 | 41 |
| OPTC_H501 | 0 | 5 | 12 | 12 |
| THEIA_E3 | 0 | 328 | 13619 | 1611 |
| THEIA_E3 | 1 | 4 | 13295 | 1225 |
