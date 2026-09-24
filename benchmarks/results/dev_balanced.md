immediate: 104 cases (12 ambiguous at t0), composition: 104 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.673 | 0.673 | 0.644 | 0 | 0 | 70 | 34 | 0 | n/a | 0/9 |
| corpus-raw | 104 | 0.731 | 0.740 | 0.721 | 4 | 3 | 73 | 24 | 8 | 0.500 | 1/7 |
| corpus-raw+lexicon | 104 | 0.760 | 0.788 | 0.769 | 4 | 1 | 78 | 21 | 7 | 0.571 | 1/7 |
| corpus-general | 104 | 0.712 | 0.760 | 0.721 | 7 | 2 | 72 | 23 | 10 | 0.700 | 2/7 |
| corpus-general+lexicon | 104 | 0.750 | 0.808 | 0.779 | 6 | 0 | 78 | 20 | 8 | 0.750 | 2/8 |
| hybrid-confidence[pairwise,general+lexicon] | 104 | 0.750 | 0.798 | 0.779 | 6 | 1 | 77 | 20 | 8 | 0.750 | 2/8 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.644 | 0.798 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw | 104 | 0.721 | 0.830 | 10 | 18 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw+lexicon | 104 | 0.769 | 0.868 | 5 | 18 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general | 104 | 0.721 | 0.833 | 9 | 17 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general+lexicon | 104 | 0.779 | 0.875 | 4 | 18 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise,general+lexicon] | 104 | 0.779 | 0.871 | 4 | 18 | 0 | 0/102 | 0 | 18 | 0.004 | 0.268 | n/a | 102 | 1224 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.731 | 0.855 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw | 104 | 0.769 | 0.863 | 11 | 15 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw+lexicon | 104 | 0.798 | 0.893 | 7 | 14 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general | 104 | 0.750 | 0.854 | 9 | 11 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general+lexicon | 104 | 0.798 | 0.895 | 6 | 13 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise,general+lexicon] | 104 | 0.798 | 0.892 | 6 | 13 | 0 | 0/102 | 0 | 22 | 0.005 | 0.273 | n/a | 102 | 1202 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong | low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 92 | 0.728 | 0.852 | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw | 92 | 0.772 | 0.863 | 11 | 15 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-raw+lexicon | 92 | 0.804 | 0.895 | 7 | 14 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general | 92 | 0.750 | 0.853 | 9 | 11 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| corpus-general+lexicon | 92 | 0.804 | 0.897 | 6 | 13 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | 0 | 0 |
| hybrid-confidence[pairwise,general+lexicon] | 92 | 0.804 | 0.894 | 6 | 13 | 0 | 0/90 | 0 | 18 | 0.005 | 0.281 | n/a | 90 | 1058 |

### Latency（CompositionReranking cases，ms）

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.03 | 0.06 |
| corpus-raw | n/a | n/a | 0.12 | 0.17 |
| corpus-raw+lexicon | n/a | n/a | 0.13 | 0.22 |
| corpus-general | n/a | n/a | 0.28 | 0.53 |
| corpus-general+lexicon | n/a | n/a | 0.30 | 0.46 |
| hybrid-confidence[pairwise,general+lexicon] | 56.16 | 63.43 | 56.76 | 63.93 |

report -> benchmarks\results\dev_balanced.json
