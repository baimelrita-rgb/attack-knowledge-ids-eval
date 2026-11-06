# Mechanism analysis for RQ2 (written 2026-11-02, before any of the quantities below was computed)

Status: exploratory. The aggregate RQ2 results are already known; the quantities below (per node type, per attack,
coverage, selectivity) have not been computed. No model is re-trained; inputs are the frozen Velox-lite node scores
(seeds 0-4), the knowledge points and the ground truth of the seven provenance datasets with a learned detector
(ATLASv2, OpTC h501/h051/h201, CADETS, THEIA, CLEARSCOPE). CARBANAKv2 enters only the coverage/selectivity table.
Fusion is the Phase-2 sum (percentile of the learned score + 0.1 x points) for every dataset, so one definition is used.

## Hypotheses
H1 (representation). The prior fails on OpTC h501/h201 because their ground truth is mostly network-connection nodes,
   not because the attack is invisible to it. Test: restrict the ground truth to process nodes. Prediction: on
   h501/h201 the knowledge ranking finds at least as many ground-truth processes within 50 alerts as the learned
   detector (median over seeds). If it does not, H1 is rejected and the paper says so.
H2 (coverage). The gain of fusion over the learned detector grows with the share of ground-truth processes that the
   rules mark. Test: Spearman correlation over the seven datasets between rule coverage of ground-truth processes
   and gain = fused minus learned ground-truth nodes within 50 alerts (median over seeds); exact permutation p-value.
H3 (weak learner). The gain is larger when the learned detector is weak. Test: Spearman between gain and the learned
   detector's node AUC (median over seeds), exact permutation p-value. Prediction: negative.
H4 (per attack). Alerts needed to reach the first ground-truth node of each attack (rank of its first node), fused vs
   learned, paired per attack and seed. Reported by group (Windows process-centric: ATLASv2, h051; others) with a
   Wilcoxon signed-rank test per group on the per-attack medians over seeds.

## Label-free indicator (descriptive)
Rule selectivity = share of test processes marked by the rules (needs no labels). Reported next to the gain to see
whether an operator could tell in advance whether the prior will help.

## Caveats fixed in advance
Seven datasets and few attacks: correlations over n = 7 have low power and are reported as exploratory with the exact
p-values; none of these results changes any pre-registered gate.
