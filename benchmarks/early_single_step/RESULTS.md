# Early single-step experiment（已封存，不作產品結論）

2026-09-22 的第一版實驗。每個 case 只有「已確認前文 + 目標讀音」，gold 取自事後完整句子，
因此許多 case 在該時間點其實有多個合理答案（例如「我明天會 ㄗㄞˋ」），不應拿來評斷 Laya 是否適合注音。
當時 Laya 載入方式為 `convaiinnovations/laya-multilingual`，選項只有候選本身、沒有排列去偏。

135 cases，top_k=12，timeout 2s，warmup 3，RTX 4070 SUPER：

| ranker | top-1 | MRR | regressions | improvements | unchanged | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|
| frequency | 0.778 | 0.880 | 0 | 0 | 135 | 0.02 | 0.06 |
| laya | 0.356 | 0.586 | 61 | 4 | 53 | 45.27 | 55.95 |
| hybrid(w=0.3) | 0.785 | 0.877 | 2 | 3 | 121 | 44.14 | 54.58 |
| hybrid(w=0.5) | 0.770 | 0.861 | 4 | 3 | 114 | 23.55 | 52.18 |
| hybrid(w=0.7) | 0.600 | 0.768 | 27 | 3 | 87 | 19.64 | 45.13 |

同一份資料的 ablation（英文 instructions、top_k=5、把前文接在選項前）都沒有明顯差異。
這份結果被後來的 temporal benchmark（ImmediateRanking / CompositionReranking）取代。
