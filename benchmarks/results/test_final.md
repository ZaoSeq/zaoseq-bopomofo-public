| system | set | n | top-1 | char acc | R@5 | w→c vs V0 | c→w vs V0 | high-conf wrong | total p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| old lexicon baseline | test-everyday | 264 | 0.087 | 0.685 | 0.186 | 3 | 116 | 0 | 1.4 / 2.8 |
| old lexicon baseline | test-gov | 800 | 0.030 | 0.453 | 0.074 | 1 | 581 | 0 | 0.8 / 1.9 |
| old lexicon baseline | test-typo | 1583 | 0.001 | 0.580 | 0.004 | 2 | 22 | 0 | 1.4 / 3.0 |
| V0 (general corpus + lexicon) | test-everyday | 264 | 0.515 | 0.923 | 0.777 | 0 | 0 | 0 | 98.7 / 394.4 |
| V0 (general corpus + lexicon) | test-gov | 800 | 0.755 | 0.934 | 0.899 | 0 | 0 | 0 | 71.7 / 312.1 |
| V0 (general corpus + lexicon) | test-typo | 1583 | 0.014 | 0.772 | 0.023 | 0 | 0 | 0 | 58.1 / 307.8 |
| zero-shot Laya (pairwise) | test-everyday | 264 | 0.155 | 0.866 | 0.769 | 17 | 112 | 0 | 179.7 / 481.1 |
| zero-shot Laya (pairwise) | test-gov | 800 | 0.254 | 0.836 | 0.894 | 34 | 435 | 2 | 142.3 / 380.1 |
| zero-shot Laya (pairwise) | test-typo | 1583 | 0.007 | 0.747 | 0.023 | 6 | 17 | 0 | 151.7 / 432.3 |
| zero-shot Laya (multi-choice) | test-everyday | 264 | 0.216 | 0.881 | 0.773 | 5 | 84 | 7 | 156.8 / 405.1 |
| zero-shot Laya (multi-choice) | test-gov | 800 | 0.347 | 0.858 | 0.896 | 16 | 342 | 27 | 122.8 / 355.3 |
| zero-shot Laya (multi-choice) | test-typo | 1583 | 0.009 | 0.755 | 0.023 | 5 | 13 | 65 | 135.0 / 401.1 |
| fine-tuned Laya | test-everyday | 264 | 0.727 | 0.958 | 0.777 | 58 | 2 | 71 | 169.1 / 424.5 |
| fine-tuned Laya | test-gov | 800 | 0.856 | 0.963 | 0.899 | 93 | 12 | 113 | 133.3 / 379.5 |
| fine-tuned Laya | test-typo | 1583 | 0.022 | 0.791 | 0.023 | 13 | 0 | 1422 | 152.0 / 421.2 |
| V0 + fine-tuned Laya (confidence hybrid) | test-everyday | 264 | 0.720 | 0.958 | 0.777 | 56 | 2 | 73 | 168.3 / 430.7 |
| V0 + fine-tuned Laya (confidence hybrid) | test-gov | 800 | 0.856 | 0.963 | 0.899 | 92 | 11 | 115 | 114.6 / 343.5 |
| V0 + fine-tuned Laya (confidence hybrid) | test-typo | 1583 | 0.022 | 0.791 | 0.023 | 13 | 0 | 1459 | 177.7 / 518.4 |
