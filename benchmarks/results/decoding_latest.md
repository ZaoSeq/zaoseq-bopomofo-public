items: 452, noise items: {'tone_missing': 449, 'tone_wrong': 452, 'insertion': 411, 'deletion': 448, 'substitution': 452, 'adjacent_key': 452}

### ExactReadingBenchmark

| system | set | n | sentence acc | char acc | R@1 | R@5 | R@10 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| lexicon-exact | hand | 131 | 0.626 | 0.856 | 0.626 | 0.985 | 1.000 | 0.2 | 0.7 |
| lexicon-exact | silver | 321 | 0.019 | 0.476 | 0.019 | 0.053 | 0.059 | 0.9 | 2.0 |
| corpus-exact | hand | 131 | 0.519 | 0.776 | 0.519 | 0.817 | 0.863 | 9.4 | 51.2 |
| corpus-exact | silver | 321 | 0.844 | 0.962 | 0.844 | 0.947 | 0.972 | 44.7 | 284.7 |
| corpus-tolerant | hand | 131 | 0.450 | 0.719 | 0.450 | 0.779 | 0.832 | 16.2 | 141.1 |
| corpus-tolerant | silver | 321 | 0.844 | 0.961 | 0.844 | 0.944 | 0.969 | 57.2 | 309.5 |
| corpus+lexicon-tolerant | hand | 131 | 0.634 | 0.856 | 0.634 | 0.939 | 0.977 | 18.4 | 157.8 |
| corpus+lexicon-tolerant | silver | 321 | 0.838 | 0.960 | 0.838 | 0.947 | 0.966 | 55.8 | 340.3 |
| corpus-tolerant+laya-hybrid | hand | 131 | 0.450 | 0.719 | 0.450 | 0.779 | 0.832 | 91.5 | 263.1 |
| corpus-tolerant+laya-hybrid | silver | 321 | 0.844 | 0.961 | 0.844 | 0.944 | 0.969 | 136.4 | 408.3 |

### Clean input safety（正確輸入）

| system | n | false correction rate | exact-input regressions | regression rate |
|---|---|---|---|---|
| lexicon-exact | 452 | 0.000 | 281 | 0.622 |
| corpus-exact | 452 | 0.000 | 0 | 0.000 |
| corpus-tolerant | 452 | 0.058 | 9 | 0.020 |
| corpus+lexicon-tolerant | 452 | 0.027 | 13 | 0.029 |
| corpus-tolerant+laya-hybrid | 452 | 0.058 | 9 | 0.020 |

### TypoToleranceBenchmark：sentence recovery（R@5）

| system | tone_missing | tone_wrong | insertion | deletion | substitution | adjacent_key |
|---|---|---|---|---|---|---|
| lexicon-exact | 0.009 (0.013) | 0.004 (0.011) | 0.000 (0.000) | 0.000 (0.000) | 0.000 (0.000) | 0.000 (0.000) |
| corpus-exact | 0.045 (0.051) | 0.035 (0.044) | 0.000 (0.000) | 0.000 (0.000) | 0.000 (0.000) | 0.000 (0.000) |
| corpus-tolerant | 0.096 (0.147) | 0.064 (0.126) | 0.046 (0.073) | 0.022 (0.033) | 0.038 (0.064) | 0.046 (0.077) |
| corpus+lexicon-tolerant | 0.134 (0.198) | 0.102 (0.184) | 0.083 (0.122) | 0.049 (0.080) | 0.073 (0.113) | 0.073 (0.135) |
| corpus-tolerant+laya-hybrid | 0.098 (0.147) | 0.064 (0.126) | 0.046 (0.073) | 0.022 (0.033) | 0.038 (0.064) | 0.046 (0.077) |

### Latency on noisy input（p50 / p95 ms）

| system | tone_missing | tone_wrong | insertion | deletion | substitution | adjacent_key |
|---|---|---|---|---|---|---|
| lexicon-exact | 0.6 / 1.5 | 0.6 / 1.7 | 0.7 / 1.8 | 0.7 / 1.7 | 0.5 / 1.5 | 0.6 / 1.6 |
| corpus-exact | 24.5 / 189.0 | 33.0 / 195.9 | 25.0 / 147.4 | 19.0 / 199.2 | 19.1 / 115.7 | 36.4 / 164.2 |
| corpus-tolerant | 42.7 / 287.4 | 46.2 / 295.4 | 42.9 / 267.0 | 56.9 / 350.6 | 47.7 / 312.2 | 45.8 / 307.6 |
| corpus+lexicon-tolerant | 21.9 / 201.8 | 41.4 / 307.3 | 43.2 / 302.2 | 55.5 / 312.2 | 56.2 / 324.2 | 50.2 / 325.3 |
| corpus-tolerant+laya-hybrid | 121.6 / 367.9 | 105.1 / 322.8 | 120.5 / 353.4 | 127.3 / 417.8 | 134.5 / 405.6 | 153.1 / 448.7 |
