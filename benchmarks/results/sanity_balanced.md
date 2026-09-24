immediate: 27 cases (11 ambiguous at t0), composition: 27 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.704 | 0.704 | 0.667 | 0 | 0 | 19 | 8 | 0 | n/a | 0/5 |
| corpus-raw | 27 | 0.704 | 0.815 | 0.778 | 4 | 1 | 18 | 4 | 7 | 0.571 | 2/5 |
| corpus-raw+lexicon | 27 | 0.778 | 0.852 | 0.852 | 3 | 1 | 20 | 3 | 5 | 0.600 | 2/5 |
| corpus-general | 27 | 0.741 | 0.778 | 0.778 | 2 | 1 | 19 | 5 | 3 | 0.667 | 1/3 |
| corpus-general+lexicon | 27 | 0.741 | 0.815 | 0.778 | 2 | 0 | 20 | 5 | 2 | 1.000 | 2/5 |
| hybrid-confidence[pairwise,general+lexicon] | 27 | 0.741 | 0.815 | 0.778 | 2 | 0 | 20 | 5 | 2 | 1.000 | 2/5 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.667 | 0.815 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw | 27 | 0.778 | 0.867 | 3 | 6 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw+lexicon | 27 | 0.852 | 0.904 | 1 | 6 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general | 27 | 0.778 | 0.861 | 2 | 5 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general+lexicon | 27 | 0.778 | 0.877 | 1 | 4 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise,general+lexicon] | 27 | 0.778 | 0.877 | 1 | 4 | 0 | 1/27 | 0 | 3 | 0.030 | 0.240 | n/a | 27 | 324 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.852 | 0.920 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw | 27 | 0.852 | 0.920 | 2 | 2 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw+lexicon | 27 | 0.926 | 0.957 | 0 | 2 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general | 27 | 0.815 | 0.895 | 2 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general+lexicon | 27 | 0.889 | 0.938 | 0 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise,general+lexicon] | 27 | 0.889 | 0.938 | 0 | 1 | 0 | 1/27 | 0 | 4 | 0.026 | 0.264 | n/a | 27 | 324 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 16 | 0.812 | 0.906 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw | 16 | 0.812 | 0.896 | 2 | 2 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw+lexicon | 16 | 0.938 | 0.969 | 0 | 2 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general | 16 | 0.750 | 0.854 | 2 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general+lexicon | 16 | 0.875 | 0.938 | 0 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise,general+lexicon] | 16 | 0.875 | 0.938 | 0 | 1 | 0 | 0/16 | 0 | 2 | 0.008 | 0.304 | n/a | 16 | 192 |

### Latency（CompositionReranking cases，ms）

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.03 | 0.06 |
| corpus-raw | n/a | n/a | 0.12 | 0.16 |
| corpus-raw+lexicon | n/a | n/a | 0.12 | 0.16 |
| corpus-general | n/a | n/a | 0.30 | 0.47 |
| corpus-general+lexicon | n/a | n/a | 0.39 | 1.07 |
| hybrid-confidence[pairwise,general+lexicon] | 60.18 | 66.31 | 60.88 | 66.99 |

report -> benchmarks\results\sanity_balanced.json
