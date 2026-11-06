# L3 blast radius on LANL, test days 13-30 (single run of the pre-registered configuration)

Numbers from `lanl/l3_test.json`. 107 first-compromise targets; 63 of them on day 13 and 27 on day 14.
| Method | recall@10 | recall@50 | recall@100 | MRR |
|---|---|---|---|---|
| random | 0.001 | 0.004 | 0.008 | - |
| degree | 0.056 | 0.103 | 0.131 | 0.034 |
| bfs1 | 0.047 | 0.093 | 0.093 | 0.031 |
| ppr | 0.047 | 0.112 | 0.150 | 0.034 |
| cred / cred_rt / cred_after | 0.056 | 0.103 | 0.140 | 0.033 |
Gate G3 (cred_after > degree at 50 AND at 100): **FAILED** (equal at 50; 0.140 vs 0.131 at 100).
Not pre-registered as ours: PPR is the best method on the test days at 50 and 100 (it was below degree in development).
All methods are 13-19x above random at 100 hosts, but no method beyond host popularity is supported by these data.
