immediate: 104 cases (12 ambiguous at t0), composition: 104 cases

### Temporal：目標段從 t0 到 t1

| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong | unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.673 | 0.673 | 0.644 | 0 | 0 | 70 | 34 | 0 | n/a | 0/9 |
| laya[single] | 104 | 0.308 | 0.471 | 0.337 | 22 | 5 | 27 | 50 | 39 | 0.564 | 2/7 |
| hybrid[single,w=0.5] | 104 | 0.683 | 0.683 | 0.644 | 3 | 3 | 68 | 30 | 7 | 0.429 | 1/7 |
| laya[cyclic] | 104 | 0.192 | 0.404 | 0.221 | 24 | 2 | 18 | 60 | 41 | 0.585 | 4/10 |
| hybrid[cyclic,w=0.5] | 104 | 0.712 | 0.712 | 0.673 | 2 | 2 | 72 | 28 | 4 | 0.500 | 1/7 |
| laya[permutations] | 104 | 0.240 | 0.442 | 0.250 | 24 | 3 | 22 | 55 | 36 | 0.667 | 2/8 |
| hybrid[permutations,w=0.5] | 104 | 0.712 | 0.721 | 0.683 | 3 | 2 | 72 | 27 | 5 | 0.600 | 1/7 |

### CompositionReranking：完整序列

| ranker | n | top-1 | MRR | regressions | improvements | unchanged | fallback | timeout | invalid |
|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.644 | 0.801 | 0 | 0 | 104 | 0 | 0 | 0 |
| laya[single] | 104 | 0.337 | 0.583 | 36 | 4 | 49 | 0 | 0 | 0 |
| hybrid[single,w=0.5] | 104 | 0.644 | 0.788 | 3 | 3 | 86 | 0 | 0 | 0 |
| laya[cyclic] | 104 | 0.221 | 0.479 | 49 | 5 | 26 | 0 | 0 | 0 |
| hybrid[cyclic,w=0.5] | 104 | 0.673 | 0.800 | 2 | 5 | 83 | 0 | 0 | 0 |
| laya[permutations] | 104 | 0.250 | 0.501 | 48 | 7 | 30 | 0 | 0 | 0 |
| hybrid[permutations,w=0.5] | 104 | 0.683 | 0.812 | 3 | 7 | 86 | 0 | 0 | 0 |

### ImmediateRanking（t0 任一合理答案排第一即算對）

| ranker | n | top-1 | MRR | regressions | improvements | unchanged | fallback | timeout | invalid |
|---|---|---|---|---|---|---|---|---|---|
| frequency | 104 | 0.731 | 0.855 | 0 | 0 | 104 | 0 | 0 | 0 |
| laya[single] | 104 | 0.356 | 0.591 | 46 | 7 | 38 | 0 | 0 | 0 |
| hybrid[single,w=0.5] | 104 | 0.731 | 0.841 | 4 | 4 | 84 | 0 | 0 | 0 |
| laya[cyclic] | 104 | 0.212 | 0.493 | 59 | 5 | 22 | 0 | 0 | 0 |
| hybrid[cyclic,w=0.5] | 104 | 0.750 | 0.853 | 2 | 4 | 86 | 0 | 0 | 0 |
| laya[permutations] | 104 | 0.269 | 0.515 | 56 | 8 | 24 | 0 | 0 | 0 |
| hybrid[permutations,w=0.5] | 104 | 0.750 | 0.857 | 3 | 5 | 87 | 0 | 0 | 0 |

### ImmediateRanking：只看 unambiguous cases

| ranker | n | top-1 | MRR | regressions | improvements | unchanged | fallback | timeout | invalid |
|---|---|---|---|---|---|---|---|---|---|
| frequency | 92 | 0.728 | 0.852 | 0 | 0 | 92 | 0 | 0 | 0 |
| laya[single] | 92 | 0.293 | 0.548 | 44 | 4 | 31 | 0 | 0 | 0 |
| hybrid[single,w=0.5] | 92 | 0.717 | 0.831 | 3 | 2 | 75 | 0 | 0 | 0 |
| laya[cyclic] | 92 | 0.196 | 0.474 | 53 | 4 | 18 | 0 | 0 | 0 |
| hybrid[cyclic,w=0.5] | 92 | 0.750 | 0.851 | 1 | 3 | 76 | 0 | 0 | 0 |
| laya[permutations] | 92 | 0.228 | 0.483 | 53 | 7 | 17 | 0 | 0 | 0 |
| hybrid[permutations,w=0.5] | 92 | 0.750 | 0.855 | 2 | 4 | 77 | 0 | 0 | 0 |

### Latency（CompositionReranking cases，ms）

decoder（candidate generation）：p50 0.09 / p95 0.43

| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |
|---|---|---|---|---|
| frequency | n/a | n/a | 0.03 | 0.06 |
| laya[single] | 45.11 | 57.94 | 45.16 | 57.90 |
| hybrid[single,w=0.5] | 46.95 | 60.55 | 47.07 | 60.45 |
| laya[cyclic] | 45.86 | 61.30 | 45.90 | 61.00 |
| hybrid[cyclic,w=0.5] | 20.41 | 22.57 | 20.47 | 22.67 |
| laya[permutations] | 54.04 | 69.69 | 54.08 | 69.53 |
| hybrid[permutations,w=0.5] | 52.24 | 61.27 | 52.39 | 61.33 |

report -> benchmarks\results\dev_latest.json
