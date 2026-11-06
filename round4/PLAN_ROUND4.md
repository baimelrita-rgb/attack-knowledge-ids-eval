# Round 4 plan (written 2026-11-03, before any run or computation listed here)

## A. Methodological rigour and strength of results (new experiments)
A1. **CARBANAKv2 as an uncontaminated Windows check (confirmatory for the mechanism).**
    The Windows rules were fixed before CARBANAKv2 ground truth was opened (DEVLOG disclosure); only the aggregate
    rule coverage (115 of 229 ground-truth processes) has been computed since. No learned-detector ranking on
    CARBANAKv2 exists. Run Velox-lite (unchanged code, emb 32, seeds 0-4) and the Phase-2 fusion (lambda = 0.1).
    Predictions from the mechanism (coverage 0.50 > 0): (P1) fused finds more ground-truth nodes within 50 alerts
    than the learned detector (median over seeds); (P2) fused reaches the attack in fewer alerts than the learned
    detector in at least 4 of 5 seeds. Both are reported whether they hold or not.
A2. **Negative control: content-free rules.** For every provenance dataset and seed, replace the rule points by the
    same multiset of points assigned to randomly chosen processes in the test population (same selectivity),
    1,000 draws. If the observed gain exceeds the 95th percentile of the control, the gain comes from what the rules
    mark, not from adding points to a ranking. Reported per dataset as the control's gain distribution and the
    one-sided permutation p-value of the observed gain.
A3. **Rule ablation on CARBANAKv2** (if per-rule points can be recomputed from the restored database): drop one
    rule family at a time and report the change in fused ground-truth nodes within 50 alerts, to show whether the
    gain rests on one pattern.
A4. **Multiplicity.** Holm correction over the mechanism tests (H2, H3, process share, H4 x 2) reported next to the
    raw p-values.

## B. Writing and structure
B1. Summary-of-findings table (question, answer, evidence, condition) at the end of the Introduction.
B2. Study-design figure (datasets -> questions -> gates).
B3. Full copy-edit pass: terminology (learned detector, rule prior, fusion), stray lines, consistent numbers and
    table captions (source file names moved to a single "Sources" note per table).
B4. Graphical abstract built from B2.

## C. Related work
C1. Restructure into: learned provenance detection; knowledge-based detection and threat intelligence;
    lateral movement and attack graphs; explanation methods in security; evaluation methodology (pitfalls,
    pre-registration). Every added reference is verified by search before it is cited.

## D. Fit to Computers & Security
D1. "Implications for practice" subsection for security operations.
D2. Cite relevant Computers & Security articles (verified) to place the work in the journal's conversation.
D3. Submission checklist (declarations, highlights, keywords, data statement, figures, abbreviations).
