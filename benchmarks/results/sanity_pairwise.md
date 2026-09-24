immediate: 27 cases (11 ambiguous at t0), composition: 27 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.704 | 0.704 | 0.667 | 0 | 0 | 19 | 8 | 0 | n/a | 0/5 |
| laya-mc-cyclic | 27 | 0.111 | 0.407 | 0.185 | 8 | 0 | 3 | 16 | 14 | 0.571 | 3/9 |
| laya-pairwise | 27 | 0.111 | 0.444 | 0.185 | 9 | 0 | 3 | 15 | 14 | 0.643 | 5/10 |
| hybrid-fixed[mc-cyclic] | 27 | 0.704 | 0.704 | 0.630 | 0 | 0 | 19 | 8 | 0 | n/a | 0/5 |
| hybrid-confidence[mc-cyclic] | 27 | 0.667 | 0.704 | 0.630 | 1 | 0 | 18 | 8 | 1 | 1.000 | 0/5 |
| hybrid-confidence[pairwise] | 27 | 0.704 | 0.704 | 0.667 | 0 | 0 | 19 | 8 | 0 | n/a | 0/5 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.667 | 0.815 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| laya-mc-cyclic | 27 | 0.185 | 0.469 | 15 | 2 | 0 | 0/27 | 0 | 5 | n/a | n/a | 0.519 | 27 | 108 |
| laya-pairwise | 27 | 0.185 | 0.466 | 16 | 3 | 0 | 0/27 | 0 | 5 | n/a | 0.235 | n/a | 27 | 324 |
| hybrid-fixed[mc-cyclic] | 27 | 0.630 | 0.793 | 1 | 0 | 0 | 0/27 | 0 | 5 | n/a | n/a | 0.519 | 27 | 108 |
| hybrid-confidence[mc-cyclic] | 27 | 0.630 | 0.790 | 1 | 0 | 0 | 0/27 | 0 | 5 | 0.007 | n/a | 0.519 | 27 | 108 |
| hybrid-confidence[pairwise] | 27 | 0.667 | 0.815 | 0 | 0 | 0 | 0/27 | 0 | 5 | 0.013 | 0.235 | n/a | 27 | 324 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.852 | 0.920 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| laya-mc-cyclic | 27 | 0.222 | 0.509 | 17 | 0 | 0 | 1/27 | 1 | 6 | n/a | n/a | 0.417 | 27 | 108 |
| laya-pairwise | 27 | 0.185 | 0.478 | 18 | 0 | 0 | 0/27 | 0 | 5 | n/a | 0.264 | n/a | 27 | 324 |
| hybrid-fixed[mc-cyclic] | 27 | 0.852 | 0.920 | 0 | 0 | 0 | 1/27 | 1 | 6 | n/a | n/a | 0.417 | 27 | 108 |
| hybrid-confidence[mc-cyclic] | 27 | 0.815 | 0.901 | 1 | 0 | 0 | 1/27 | 1 | 6 | 0.053 | n/a | 0.417 | 27 | 108 |
| hybrid-confidence[pairwise] | 27 | 0.852 | 0.920 | 0 | 0 | 0 | 0/27 | 0 | 5 | 0.009 | 0.264 | n/a | 27 | 324 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 16 | 0.812 | 0.906 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| laya-mc-cyclic | 16 | 0.062 | 0.391 | 12 | 0 | 0 | 1/16 | 1 | 1 | n/a | n/a | 0.422 | 16 | 64 |
| laya-pairwise | 16 | 0.125 | 0.401 | 11 | 0 | 0 | 0/16 | 0 | 2 | n/a | 0.304 | n/a | 16 | 192 |
| hybrid-fixed[mc-cyclic] | 16 | 0.812 | 0.906 | 0 | 0 | 0 | 1/16 | 1 | 1 | n/a | n/a | 0.422 | 16 | 64 |
| hybrid-confidence[mc-cyclic] | 16 | 0.750 | 0.875 | 1 | 0 | 0 | 1/16 | 1 | 1 | 0.077 | n/a | 0.422 | 16 | 64 |
| hybrid-confidence[pairwise] | 16 | 0.812 | 0.906 | 0 | 0 | 0 | 0/16 | 0 | 2 | 0.008 | 0.304 | n/a | 16 | 192 |

### Latency（CompositionReranking cases，ms）

decoder（candidate generation）：p50 0.16 / p95 0.47

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.03 | 0.03 |
| laya-mc-cyclic | 43.96 | 52.28 | 44.01 | 52.35 |
| laya-pairwise | 45.88 | 49.12 | 45.94 | 49.17 |
| hybrid-fixed[mc-cyclic] | 43.30 | 48.82 | 43.46 | 48.97 |
| hybrid-confidence[mc-cyclic] | 42.96 | 51.33 | 43.13 | 51.50 |
| hybrid-confidence[pairwise] | 47.72 | 63.30 | 47.87 | 63.49 |

report -> benchmarks\results\sanity_pairwise.json
