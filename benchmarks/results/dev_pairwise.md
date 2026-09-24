immediate: 104 cases (12 ambiguous at t0), composition: 104 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.673 | 0.673 | 0.644 | 0 | 0 | 70 | 34 | 0 | n/a | 0/9 |
| laya-mc-cyclic | 104 | 0.202 | 0.423 | 0.240 | 25 | 2 | 19 | 58 | 41 | 0.610 | 5/10 |
| laya-pairwise | 104 | 0.202 | 0.375 | 0.192 | 19 | 1 | 20 | 64 | 35 | 0.543 | 4/11 |
| hybrid-fixed[mc-cyclic] | 104 | 0.721 | 0.712 | 0.673 | 1 | 2 | 73 | 28 | 3 | 0.333 | 0/6 |
| hybrid-confidence[mc-cyclic] | 104 | 0.673 | 0.654 | 0.625 | 0 | 2 | 68 | 34 | 2 | 0.000 | 0/9 |
| hybrid-confidence[pairwise] | 104 | 0.663 | 0.673 | 0.644 | 1 | 0 | 69 | 34 | 1 | 1.000 | 0/8 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.644 | 0.798 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| laya-mc-cyclic | 104 | 0.240 | 0.489 | 48 | 6 | 0 | 3/102 | 3 | 23 | n/a | n/a | 0.475 | 102 | 408 |
| laya-pairwise | 104 | 0.192 | 0.457 | 51 | 4 | 0 | 0/102 | 0 | 18 | n/a | 0.267 | n/a | 102 | 1224 |
| hybrid-fixed[mc-cyclic] | 104 | 0.673 | 0.800 | 2 | 5 | 0 | 3/102 | 3 | 23 | n/a | n/a | 0.475 | 102 | 408 |
| hybrid-confidence[mc-cyclic] | 104 | 0.625 | 0.788 | 2 | 0 | 0 | 3/102 | 3 | 23 | 0.024 | n/a | 0.475 | 102 | 408 |
| hybrid-confidence[pairwise] | 104 | 0.644 | 0.800 | 1 | 1 | 0 | 0/102 | 0 | 18 | 0.004 | 0.267 | n/a | 102 | 1224 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.731 | 0.855 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| laya-mc-cyclic | 104 | 0.231 | 0.504 | 57 | 5 | 0 | 2/102 | 2 | 22 | n/a | n/a | 0.438 | 102 | 404 |
| laya-pairwise | 104 | 0.231 | 0.486 | 56 | 4 | 0 | 0/102 | 0 | 22 | n/a | 0.273 | n/a | 102 | 1202 |
| hybrid-fixed[mc-cyclic] | 104 | 0.760 | 0.858 | 1 | 4 | 0 | 2/102 | 2 | 22 | n/a | n/a | 0.438 | 102 | 404 |
| hybrid-confidence[mc-cyclic] | 104 | 0.731 | 0.855 | 0 | 0 | 0 | 2/102 | 2 | 22 | 0.028 | n/a | 0.438 | 102 | 404 |
| hybrid-confidence[pairwise] | 104 | 0.721 | 0.850 | 2 | 1 | 0 | 0/102 | 0 | 22 | 0.005 | 0.273 | n/a | 102 | 1202 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 92 | 0.728 | 0.852 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| laya-mc-cyclic | 92 | 0.207 | 0.481 | 52 | 4 | 0 | 2/90 | 2 | 17 | n/a | n/a | 0.424 | 90 | 356 |
| laya-pairwise | 92 | 0.217 | 0.468 | 50 | 3 | 0 | 0/90 | 0 | 18 | n/a | 0.281 | n/a | 90 | 1058 |
| hybrid-fixed[mc-cyclic] | 92 | 0.750 | 0.851 | 1 | 3 | 0 | 2/90 | 2 | 17 | n/a | n/a | 0.424 | 90 | 356 |
| hybrid-confidence[mc-cyclic] | 92 | 0.728 | 0.852 | 0 | 0 | 0 | 2/90 | 2 | 17 | 0.031 | n/a | 0.424 | 90 | 356 |
| hybrid-confidence[pairwise] | 92 | 0.707 | 0.841 | 2 | 0 | 0 | 0/90 | 0 | 18 | 0.005 | 0.281 | n/a | 90 | 1058 |

### Latency（CompositionReranking cases，ms）

decoder（candidate generation）：p50 0.08 / p95 0.42

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.02 | 0.03 |
| laya-mc-cyclic | 24.57 | 37.21 | 24.48 | 37.28 |
| laya-pairwise | 22.89 | 34.96 | 22.83 | 34.97 |
| hybrid-fixed[mc-cyclic] | 20.48 | 26.32 | 20.57 | 26.40 |
| hybrid-confidence[mc-cyclic] | 43.04 | 56.37 | 43.14 | 56.51 |
| hybrid-confidence[pairwise] | 45.49 | 53.40 | 45.61 | 53.56 |

report -> benchmarks\results\dev_pairwise.json
