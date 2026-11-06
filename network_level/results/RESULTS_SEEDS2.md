# Seed round 2 (seeds [42, 0, 1, 2, 3, 4]; original seed 42 re-run)


## RQ1 optc: host-day AUC and host-day detection at 5 alerts/day, median [min-max]

| Method | host-day AUC | detection@5 |
|---|---|---|
| model_p3 | 0.673 [0.673-0.673] | 0.007 [0.007-0.008] |
| channels_only | 0.707 [0.707-0.707] | 0.005 [0.005-0.005] |
| ablation_gnn_only | 0.513 [0.513-0.513] | 0.001 [0.001-0.002] |
| ecod_pooled | 0.896 [0.896-0.896] | 0.003 [0.003-0.003] |
| iforest_pooled | 0.876 [0.857-0.892] | 0.001 [0.000-0.001] |
| autoencoder_pooled | 0.985 [0.960-0.991] | 0.008 [0.008-0.010] |

Best method per seed: ['autoencoder_pooled', 'autoencoder_pooled', 'autoencoder_pooled', 'autoencoder_pooled', 'autoencoder_pooled', 'autoencoder_pooled']


## RQ1 unraveled: host-day AUC and host-day detection at 5 alerts/day, median [min-max]

| Method | host-day AUC | detection@5 |
|---|---|---|
| model_p3 | 0.818 [0.815-0.826] | 0.342 [0.267-0.383] |
| channels_only | 0.888 [0.881-0.891] | 0.192 [0.133-0.250] |
| ablation_gnn_only | 0.762 [0.679-0.839] | 0.217 [0.100-0.267] |
| ecod_pooled | 0.709 [0.701-0.721] | 0.208 [0.167-0.283] |
| iforest_pooled | 0.706 [0.663-0.757] | 0.242 [0.117-0.350] |
| autoencoder_pooled | 0.758 [0.712-0.914] | 0.183 [0.100-0.417] |

Best method per seed: ['channels_only', 'channels_only', 'channels_only', 'channels_only', 'channels_only', 'autoencoder_pooled']


## RQ3 attribution accuracy, dedale (n = 12)

| Method | accuracy |
|---|---|
| ours | 0.542 [0.500-0.583] |
| ae_error | 0.583 [0.417-0.750] |
| shap_ae | 0.417 [0.333-0.750] |
| shap_if | 0.458 [0.333-0.500] |
| occlusion_ae | 0.708 [0.500-0.917] |
| random | 0.354 [0.354-0.354] |

Best explainer per seed: ['occlusion_ae', 'occlusion_ae', 'ours', 'ae_error', 'occlusion_ae', 'ours']


## RQ3 attribution accuracy, unraveled (n = 645)

| Method | accuracy |
|---|---|
| ours | 0.251 [0.141-0.256] |
| ae_error | 0.513 [0.409-0.647] |
| shap_ae | 0.387 [0.234-0.609] |
| shap_if | 0.364 [0.233-0.398] |
| occlusion_ae | 0.407 [0.340-0.530] |
| random | 0.263 [0.263-0.263] |

Best explainer per seed: ['occlusion_ae', 'ae_error', 'ae_error', 'ae_error', 'ae_error', 'shap_ae']


## RQ3 attribution accuracy, optc (n = 102)

| Method | accuracy |
|---|---|
| ours | 0.373 [0.373-0.373] |
| ae_error | 0.358 [0.284-0.676] |
| shap_ae | 0.181 [0.069-0.353] |
| shap_if | 0.319 [0.186-0.422] |
| occlusion_ae | 0.324 [0.314-0.422] |
| random | 0.341 [0.341-0.341] |

Best explainer per seed: ['shap_if', 'occlusion_ae', 'ae_error', 'ae_error', 'ours', 'ae_error']


## RQ3 attribution accuracy, pooled (n = 759)

| Method | accuracy |
|---|---|
| ours | 0.271 [0.179-0.277] |
| ae_error | 0.500 [0.411-0.601] |
| shap_ae | 0.361 [0.229-0.548] |
| shap_if | 0.360 [0.228-0.401] |
| occlusion_ae | 0.406 [0.340-0.518] |
| random | 0.275 [0.275-0.275] |

Best explainer per seed: ['occlusion_ae', 'ae_error', 'ae_error', 'ae_error', 'ae_error', 'shap_ae']


## RQ3 gate per seed (descriptive)

| seed | G1 | G2 | G3 | pass |
|---|---|---|---|---|
| 42 | False | False | True | False |
| 0 | False | False | True | False |
| 1 | False | False | False | False |
| 2 | False | False | False | False |
| 3 | False | False | True | False |
| 4 | False | False | True | False |

## Reading (descriptive; the gate decisions stay with the original seed)
- RQ1 OpTC: our model 0.673 in all six seeds; the GNN channel alone 0.513 in all seeds (it does not move the OpTC
  ranking). The pooled autoencoder is the best method in every seed (0.960-0.991). Conclusion unchanged.
- RQ1 Unraveled (development): the tactic channels without ECOD fusion have the best host-day AUC in 5 of 6 seeds.
- RQ3: the E1 gate fails in all six seeds. Grouping the autoencoder's reconstruction error by channel is above chance on
  Unraveled in every seed (0.41-0.65 vs 0.263) but the best explainer in only 4 of 6. On OpTC it ranges 0.28-0.68 and is
  above chance in 3 of 6 seeds. KernelSHAP is below chance on OpTC in 5 of 6 seeds. Explainer rankings are seed-dependent.
- The seed-42 re-run reproduces every OpTC number of the paper exactly; on DEDALE/Unraveled the GNN is not
  bit-reproducible between runs (see PLAN_SEEDS2.md), so the re-run differs from the originally reported dev values.
