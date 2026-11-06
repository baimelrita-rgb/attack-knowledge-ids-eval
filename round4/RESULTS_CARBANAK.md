# A1: CARBANAKv2 (rules fixed before its ground truth was opened), Velox-lite seeds 0-4

| Seed | learned AUC | GT@50 learned / knowledge / fused | alerts to attack: learned / fused | negative control: gain vs control median (p) |
|---|---|---|---|---|
| 0 | 0.340 | 0 / 18 / 12 | 3035 / 1 | +12 vs +0 (0.001) |
| 1 | 0.342 | 0 / 10 / 5 | 3656 / 2 | +5 vs +0 (0.001) |
| 2 | 0.326 | 0 / 19 / 11 | 6387 / 2 | +11 vs +0 (0.001) |
| 3 | 0.387 | 0 / 10 / 2 | 1985 / 3 | +2 vs +0 (0.038) |
| 4 | 0.374 | 0 / 11 / 2 | 321 / 2 | +2 vs +0 (0.042) |

P1 (fused > learned GT nodes within 50 alerts, median over seeds): holds (5 vs 0).
P2 (fused reaches the attack first in >= 4 of 5 seeds): holds (5 of 5).
