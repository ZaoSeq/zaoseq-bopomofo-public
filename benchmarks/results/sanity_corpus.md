immediate: 27 cases (11 ambiguous at t0), composition: 27 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.704 | 0.704 | 0.667 | 0 | 0 | 19 | 8 | 0 | n/a | 0/5 |
| corpus | 27 | 0.667 | 0.667 | 0.593 | 1 | 1 | 17 | 8 | 4 | 0.250 | 1/5 |
| corpus+lexicon | 27 | 0.741 | 0.741 | 0.667 | 0 | 0 | 20 | 7 | 1 | 0.000 | 0/5 |
| hybrid-confidence[pairwise] | 27 | 0.704 | 0.704 | 0.667 | 0 | 0 | 19 | 8 | 0 | n/a | 0/5 |
| hybrid-confidence[pairwise,corpus] | 27 | 0.667 | 0.704 | 0.593 | 1 | 0 | 18 | 8 | 1 | 1.000 | 1/5 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.667 | 0.815 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus | 27 | 0.593 | 0.744 | 4 | 2 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus+lexicon | 27 | 0.667 | 0.812 | 1 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise] | 27 | 0.667 | 0.815 | 0 | 0 | 0 | 0/27 | 0 | 5 | 0.013 | 0.235 | n/a | 27 | 324 |
| hybrid-confidence[pairwise,corpus] | 27 | 0.593 | 0.754 | 4 | 2 | 0 | 1/27 | 0 | 3 | 0.030 | 0.240 | n/a | 27 | 324 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 27 | 0.852 | 0.920 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus | 27 | 0.741 | 0.846 | 4 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus+lexicon | 27 | 0.889 | 0.938 | 0 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise] | 27 | 0.852 | 0.920 | 0 | 0 | 0 | 0/27 | 0 | 5 | 0.009 | 0.264 | n/a | 27 | 324 |
| hybrid-confidence[pairwise,corpus] | 27 | 0.741 | 0.852 | 4 | 1 | 0 | 1/27 | 0 | 4 | 0.026 | 0.264 | n/a | 27 | 324 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 16 | 0.812 | 0.906 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus | 16 | 0.750 | 0.844 | 2 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus+lexicon | 16 | 0.875 | 0.938 | 0 | 1 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise] | 16 | 0.812 | 0.906 | 0 | 0 | 0 | 0/16 | 0 | 2 | 0.008 | 0.304 | n/a | 16 | 192 |
| hybrid-confidence[pairwise,corpus] | 16 | 0.750 | 0.854 | 2 | 1 | 0 | 0/16 | 0 | 2 | 0.008 | 0.304 | n/a | 16 | 192 |

### Latency（CompositionReranking cases，ms）

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.03 | 0.16 |
| corpus | n/a | n/a | 0.11 | 0.21 |
| corpus+lexicon | n/a | n/a | 0.11 | 0.15 |
| hybrid-confidence[pairwise] | 64.26 | 81.39 | 64.54 | 81.64 |
| hybrid-confidence[pairwise,corpus] | 70.68 | 101.41 | 71.08 | 101.82 |

report -> benchmarks\results\sanity_corpus.json
