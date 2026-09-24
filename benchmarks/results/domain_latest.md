| system | set | n | top-1 | char acc | R@5 | lexicon OOV | corpus OOV | decoder p50/p95 ms | LM p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| lexicon (old baseline) | everyday_dev | 131 | 0.626 | 0.856 | 0.985 | 0.000 | 0.000 | 0.2 / 0.8 | 0.0 / 0.0 |
| lexicon (old baseline) | legal | 200 | 0.015 | 0.489 | 0.045 | 0.000 | 0.000 | 1.0 / 1.7 | 0.0 / 0.0 |
| lexicon (old baseline) | faq_public_service | 400 | 0.043 | 0.463 | 0.098 | 0.000 | 0.000 | 0.7 / 1.7 | 0.0 / 0.0 |
| lexicon (old baseline) | press_release | 200 | 0.035 | 0.442 | 0.095 | 0.000 | 0.000 | 0.8 / 1.9 | 0.0 / 0.0 |
| lexicon (old baseline) | mixed | 800 | 0.034 | 0.464 | 0.084 | 0.000 | 0.000 | 0.8 / 1.7 | 0.0 / 0.0 |
| raw corpus | everyday_dev | 131 | 0.656 | 0.843 | 0.916 | 0.000 | 0.000 | 10.0 / 62.2 | 2.8 / 13.8 |
| raw corpus | legal | 200 | 0.920 | 0.979 | 0.965 | 0.000 | 0.000 | 62.8 / 130.3 | 16.5 / 29.1 |
| raw corpus | faq_public_service | 400 | 0.787 | 0.939 | 0.927 | 0.000 | 0.000 | 44.1 / 134.7 | 10.9 / 32.0 |
| raw corpus | press_release | 200 | 0.805 | 0.963 | 0.960 | 0.000 | 0.000 | 46.0 / 122.1 | 11.5 / 26.3 |
| raw corpus | mixed | 800 | 0.825 | 0.956 | 0.945 | 0.000 | 0.000 | 48.4 / 127.6 | 11.9 / 30.0 |
| raw corpus + lexicon | everyday_dev | 131 | 0.771 | 0.905 | 0.992 | 0.000 | 0.000 | 10.6 / 62.1 | 2.6 / 14.1 |
| raw corpus + lexicon | legal | 200 | 0.890 | 0.973 | 0.950 | 0.000 | 0.000 | 61.7 / 121.8 | 15.7 / 27.7 |
| raw corpus + lexicon | faq_public_service | 400 | 0.795 | 0.942 | 0.922 | 0.000 | 0.000 | 44.3 / 141.6 | 11.0 / 32.8 |
| raw corpus + lexicon | press_release | 200 | 0.775 | 0.952 | 0.935 | 0.000 | 0.000 | 47.3 / 120.0 | 12.3 / 27.7 |
| raw corpus + lexicon | mixed | 800 | 0.814 | 0.953 | 0.932 | 0.000 | 0.000 | 47.5 / 124.5 | 11.5 / 30.8 |
| capped corpus | everyday_dev | 131 | 0.672 | 0.853 | 0.931 | 0.000 | 0.000 | 9.2 / 56.9 | 2.5 / 12.5 |
| capped corpus | legal | 200 | 0.880 | 0.971 | 0.960 | 0.000 | 0.000 | 61.8 / 120.7 | 15.0 / 27.5 |
| capped corpus | faq_public_service | 400 | 0.805 | 0.944 | 0.917 | 0.000 | 0.000 | 41.9 / 127.8 | 10.5 / 31.7 |
| capped corpus | press_release | 200 | 0.775 | 0.953 | 0.945 | 0.000 | 0.000 | 48.0 / 125.0 | 12.2 / 28.0 |
| capped corpus | mixed | 800 | 0.816 | 0.953 | 0.935 | 0.000 | 0.000 | 50.3 / 129.6 | 11.8 / 29.9 |
| balanced corpus (general) | everyday_dev | 131 | 0.687 | 0.858 | 0.901 | 0.000 | 0.000 | 16.0 / 82.7 | 8.0 / 52.9 |
| balanced corpus (general) | legal | 200 | 0.890 | 0.971 | 0.955 | 0.000 | 0.000 | 97.6 / 180.6 | 53.9 / 107.2 |
| balanced corpus (general) | faq_public_service | 400 | 0.823 | 0.953 | 0.922 | 0.000 | 0.000 | 66.8 / 216.5 | 35.9 / 127.9 |
| balanced corpus (general) | press_release | 200 | 0.850 | 0.968 | 0.950 | 0.000 | 0.000 | 74.1 / 190.7 | 40.2 / 117.3 |
| balanced corpus (general) | mixed | 800 | 0.846 | 0.961 | 0.938 | 0.000 | 0.000 | 78.3 / 198.2 | 41.9 / 115.4 |
| balanced corpus + lexicon | everyday_dev | 131 | 0.763 | 0.908 | 0.985 | 0.000 | 0.000 | 16.9 / 101.1 | 8.2 / 66.2 |
| balanced corpus + lexicon | legal | 200 | 0.850 | 0.960 | 0.940 | 0.000 | 0.000 | 102.1 / 195.2 | 57.3 / 122.2 |
| balanced corpus + lexicon | faq_public_service | 400 | 0.775 | 0.937 | 0.910 | 0.000 | 0.000 | 70.3 / 215.7 | 37.7 / 130.2 |
| balanced corpus + lexicon | press_release | 200 | 0.800 | 0.949 | 0.925 | 0.000 | 0.000 | 76.7 / 178.3 | 43.6 / 110.1 |
| balanced corpus + lexicon | mixed | 800 | 0.800 | 0.946 | 0.921 | 0.000 | 0.000 | 76.4 / 198.5 | 41.8 / 120.0 |

### 錯字分類（第一名 vs gold，逐字）

| system | set | 功能詞組錯誤 | 組外同音字 | 非同音 |
|---|---|---|---|---|
| lexicon (old baseline) | everyday_dev | 在再 9、做作 5、的得地 4、他她它 2、是事 2 | 36 | 0 |
| lexicon (old baseline) | legal | 是事 7、才財 6、在再 5、為位 2 | 626 | 0 |
| lexicon (old baseline) | faq_public_service | 是事 29、為位 4、已以 3、在再 2、會匯 2、做作 1、才財 1 | 1204 | 0 |
| lexicon (old baseline) | press_release | 是事 6、為位 6、才財 3、做作 2、在再 1、會匯 1 | 643 | 0 |
| lexicon (old baseline) | mixed | 是事 42、為位 12、才財 10、在再 8、做作 3、已以 3、會匯 3 | 2473 | 0 |
| raw corpus | everyday_dev | 在再 7、做作 3、他她它 2、的得地 2、已以 1、是事 1 | 47 | 0 |
| raw corpus | legal | 在再 1 | 25 | 0 |
| raw corpus | faq_public_service | 在再 4、已以 3、做作 1、是事 1、的得地 1 | 131 | 0 |
| raw corpus | press_release | — | 44 | 0 |
| raw corpus | mixed | 在再 5、已以 3、做作 1、是事 1、的得地 1 | 200 | 0 |
| raw corpus + lexicon | everyday_dev | 在再 7、他她它 2、做作 2、的得地 2、是事 1 | 24 | 0 |
| raw corpus + lexicon | legal | 在再 1、為位 1 | 32 | 0 |
| raw corpus + lexicon | faq_public_service | 為位 2、做作 1、在再 1、已以 1、是事 1、的得地 1 | 127 | 0 |
| raw corpus + lexicon | press_release | 為位 3 | 54 | 0 |
| raw corpus + lexicon | mixed | 為位 6、在再 2、做作 1、已以 1、是事 1、的得地 1 | 213 | 0 |
| capped corpus | everyday_dev | 在再 5、做作 4、他她它 3、已以 1、是事 1、的得地 1 | 44 | 0 |
| capped corpus | legal | 在再 1、為位 1 | 34 | 0 |
| capped corpus | faq_public_service | 做作 1、在再 1、的得地 1 | 128 | 0 |
| capped corpus | press_release | 是事 2、在再 1 | 53 | 0 |
| capped corpus | mixed | 在再 3、是事 2、做作 1、為位 1、的得地 1 | 215 | 0 |
| balanced corpus (general) | everyday_dev | 在再 5、他她它 4、做作 3、是事 1、的得地 1 | 43 | 0 |
| balanced corpus (general) | legal | 在再 1 | 36 | 0 |
| balanced corpus (general) | faq_public_service | 做作 1、在再 1、已以 1、是事 1、為位 1、的得地 1 | 104 | 0 |
| balanced corpus (general) | press_release | 是事 1 | 37 | 0 |
| balanced corpus (general) | mixed | 在再 2、是事 2、做作 1、已以 1、為位 1、的得地 1 | 177 | 0 |
| balanced corpus + lexicon | everyday_dev | 在再 7、他她它 2、做作 2、的得地 2 | 24 | 0 |
| balanced corpus + lexicon | legal | 在再 1、是事 1、為位 1 | 48 | 0 |
| balanced corpus + lexicon | faq_public_service | 是事 2、為位 2、做作 1、在再 1、的得地 1 | 140 | 0 |
| balanced corpus + lexicon | press_release | 是事 2、為位 2、做作 1 | 55 | 0 |
| balanced corpus + lexicon | mixed | 是事 5、為位 5、做作 2、在再 2、的得地 1 | 243 | 0 |
