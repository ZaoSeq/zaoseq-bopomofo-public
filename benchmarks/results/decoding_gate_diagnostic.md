# TolerantDecoder gate diagnostic（2026-09-23，只作說明，未據此調整任何設定）

corpus-tolerant（corpus_weight 1、lexical_weight 0、quality_threshold -4.0/字）在 452 個 item 上，
TolerantDecoder 是否展開 edit distance 1 的次數：

| 輸入 | not_expanded | low_exact_quality | 展開後 gold 在候選中 |
|---|---|---|---|
| clean | 420 | 32 | – |
| tone_missing | 372 | 77 | 53 / 77 |
| tone_wrong | 378 | 74 | 48 / 74 |
| insertion | 347 | 64 | 37 / 64 |
| deletion | 393 | 55 | 23 / 55 |
| substitution | 380 | 72 | 33 / 72 |
| adjacent_key | 379 | 73 | 48 / 73 |

大多數加入 noise 的讀音仍能解碼成「看起來合理」的另一段文字，每字 corpus 分數沒有低於門檻，
所以 gate 不展開修正；typo recovery 偏低的主因是 gate，而不是展開後的排序。
