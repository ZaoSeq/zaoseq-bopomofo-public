immediate: 104 cases (12 ambiguous at t0), composition: 104 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.673 | 0.673 | 0.644 | 0 | 0 | 70 | 34 | 0 | n/a | 0/9 |
| corpus | 104 | 0.654 | 0.625 | 0.587 | 1 | 4 | 64 | 35 | 10 | 0.100 | 0/8 |
| corpus+lexicon | 104 | 0.721 | 0.721 | 0.692 | 1 | 1 | 74 | 28 | 4 | 0.250 | 0/8 |
| hybrid-confidence[pairwise] | 104 | 0.663 | 0.673 | 0.644 | 1 | 0 | 69 | 34 | 1 | 1.000 | 0/8 |
| hybrid-confidence[pairwise,corpus] | 104 | 0.663 | 0.635 | 0.606 | 0 | 3 | 66 | 35 | 6 | 0.000 | 0/8 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.644 | 0.798 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus | 104 | 0.587 | 0.738 | 18 | 12 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus+lexicon | 104 | 0.692 | 0.821 | 7 | 12 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise] | 104 | 0.644 | 0.800 | 1 | 1 | 0 | 0/102 | 0 | 18 | 0.004 | 0.267 | n/a | 102 | 1224 |
| hybrid-confidence[pairwise,corpus] | 104 | 0.606 | 0.759 | 17 | 13 | 0 | 0/102 | 0 | 18 | 0.004 | 0.268 | n/a | 102 | 1224 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.731 | 0.855 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus | 104 | 0.702 | 0.813 | 13 | 10 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus+lexicon | 104 | 0.769 | 0.872 | 7 | 11 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise] | 104 | 0.721 | 0.850 | 2 | 1 | 0 | 0/102 | 0 | 22 | 0.005 | 0.273 | n/a | 102 | 1202 |
| hybrid-confidence[pairwise,corpus] | 104 | 0.712 | 0.829 | 13 | 11 | 0 | 0/102 | 0 | 22 | 0.005 | 0.273 | n/a | 102 | 1202 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 92 | 0.728 | 0.852 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus | 92 | 0.696 | 0.807 | 13 | 10 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus+lexicon | 92 | 0.772 | 0.872 | 7 | 11 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise] | 92 | 0.707 | 0.841 | 2 | 0 | 0 | 0/90 | 0 | 18 | 0.005 | 0.281 | n/a | 90 | 1058 |
| hybrid-confidence[pairwise,corpus] | 92 | 0.707 | 0.825 | 13 | 11 | 0 | 0/90 | 0 | 18 | 0.005 | 0.281 | n/a | 90 | 1058 |

### Latency（CompositionReranking cases，ms）

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.03 | 0.07 |
| corpus | n/a | n/a | 0.13 | 0.26 |
| corpus+lexicon | n/a | n/a | 0.09 | 0.14 |
| hybrid-confidence[pairwise] | 64.88 | 85.41 | 64.95 | 85.62 |
| hybrid-confidence[pairwise,corpus] | 77.49 | 93.97 | 77.90 | 94.28 |

report -> benchmarks\results\dev_corpus.json
