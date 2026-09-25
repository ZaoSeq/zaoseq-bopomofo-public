# Daily Corpus Round 2 + Production Lexicon Cleanup（v0.2 development）

所有數字只來自 DEV：Coverage-DEV v1.1（300 句）與 GOV-DEV（400 句）。v0.1 TEST 只用於語料排除；沒有建立 sealed TEST，production path 沒有修改。
完整數據：[daily_round2.md](../benchmarks/results/daily_round2.md)、[daily_round2.json](../benchmarks/results/daily_round2.json)。

## Selection plan（實驗前凍結）

[benchmarks/frozen/v0.2_selection_plan.json](../benchmarks/frozen/v0.2_selection_plan.json)，sha256 `83c59d9b35d56b76ab0bfe81daa39b5ddb25549f8b269e76c0a606cc4e23e852`，
雜湊紀錄 [V0.2_PLAN.json](../benchmarks/frozen/V0.2_PLAN.json)，`daily.selection.SelectionPlan` 執行前會驗證。

1. production eligibility：所有日常來源都必須通過 production LicenseGate；HOLD / DEV-only 設定只能當診斷。
2. regression gates：GOV-DEV decoder Top-1 與 frozen teacher Top-1 相對 V0 各不得下降超過 0.02。
3. primary：Coverage-DEV 上 frozen fine-tuned Laya（K=4）的 Top-1。
4. tie-break（primary 差 ≤ 1 句）：teacher 改錯數、decoder Top-1、MRR、R@5、teacher window、p95、增量 RSS、artifact 大小。

分階段：讀音政策 → 抽詞過濾 → lexical prior → 日常 LM 權重；每階段的候選與 mapping 都事前寫定。

## 來源

- 狀態沒有改變：production 只有 Tatoeba 繁體原句；OASST1 prompter 只限 DEV；其餘 HOLD。
- **Common Voice：WAITING_FOR_OFFICIAL_COMMON_VOICE_ARTIFACT**。本機沒有 Mozilla Data Collective 的官方 zh-TW release；沒有使用舊的 Sentence Collector export，也沒有下載非官方 mirror。
- **Aya Dataset（CohereLabs/aya_dataset，Traditional Chinese 1,871 列）：HOLD**。授權是 Apache-2.0，但回答有百科複製與模板化問答的跡象（維基衍生內容被政策排除），
  183 列是其他資料集的 re-annotation；16 位標注者、前 5 位佔 98%；地區標記香港 57、中國 34、臺灣 5。未匯入。
- 權利鏈可驗證的臺灣原創文本：本輪沒有找到。

## Derived lexicon correctness

### 讀音

| policy | derived words | 無證據讀音 | 假同音競爭 |
|---|---|---|---|
| R0 舊作法（CNS 讀音組合，最多 4 組） | 82,841 | 85,529 | 10,813 |
| R1 unambiguous-only | 32,134 | 0 | 0 |
| R2 known-word-reading（多音字只能由 builtin 詞決定） | 34,123 | 0 | 0 |
| R3 bounded（R2 + builtin 單字的明確讀音） | 51,827 | 0 | 0 |

R1–R3 每個詞只有一組讀音，錯誤讀音污染完全消除。everyday teacher Top-1 三者與 R0 相同（0.760）；R3 的 GOV 最好（0.830 / 0.870），但依 tie-break（改錯數）選出 R2。

### 政府模板過濾

| filter | derived words | everyday teacher | GOV decoder | GOV teacher | gates |
|---|---|---|---|---|---|
| L1 政府 + 日常 | 34,123 | 0.760 | 0.807 | 0.855 | pass |
| L2 只從日常抽詞 | 4,469 | 0.787 | 0.748 | 0.843 | GOV decoder 失敗 |
| L3 需日常支持 | 3,883 | 0.793 | 0.745 | 0.845 | GOV decoder 失敗 |
| L4 領域集中度 + 數字模板 | 21,806 | 0.767 | 0.752 | 0.823 | 兩個 gate 都失敗 |
| L5 文件 ≥ 5、來源 ≥ 3 | 25,789 | 0.767 | 0.797 | 0.850 | pass（選出） |

- 「條第」「項規定」這類片段可以用一般訊號去除：L4 的數字鄰接比例排除 1,579 個 n-gram，領域集中度排除 34,530 個；但它同時移除真正的政府用語，GOV 退步。
- 只用日常詞（L2、L3）對日常最好，但 GOV decoder 退步 5–6 個百分點；政府詞彙對 GOV 仍是必要的。
- 選出的 L5 以獨立來源數過濾單一機關的模板，GOV 在 gate 內。

### Frequency 是否有用

| prior | everyday teacher | teacher 改對 / 改錯（vs V0 teacher） | GOV decoder | GOV teacher | 同音 gold 排第一（47 個有競爭的 gold 詞） |
|---|---|---|---|---|---|
| flat | 0.767 | 35 / 14 | 0.797 | 0.850 | 35 |
| raw | 0.767 | 36 / 15 | 0.807 | 0.860 | 42 |
| log | 0.770 | 36 / 14 | 0.805 | 0.853 | 42 |
| doc | 0.767 | 36 / 15 | 0.805 | 0.860 | 41 |
| daily_only | 0.780 | 36 / 11 | 0.802 | 0.858 | 41 |
| interpolated | 0.763 | 36 / 16 | 0.805 | 0.863 | 43 |
| rank_bucket | 0.770 | 36 / 14 | 0.807 | 0.858 | 41 |

乾淨的讀音之後，頻率確實改善同音詞排序（gold 排第一 35 → 41–43），並讓 GOV 回升約 1 個百分點；
對 everyday teacher Top-1 的影響小（± 4 句），daily_only 最好（改錯最少）。上一輪「頻率沒有用」的結論主要受錯誤讀音影響。

## 最終設定（依事前規則）

**R2 known-word readings + L5 doc-frequency filter + daily_only prior + gov 0.5 / Tatoeba 0.5**

| config | everyday decoder | everyday teacher | teacher 改對 / 改錯 | MRR | R@5 | window | GOV decoder | GOV teacher |
|---|---|---|---|---|---|---|---|---|
| V0 | 0.473 | 0.697 | – | 0.600 | 0.783 | 0.747 | 0.802 | 0.860 |
| 日常權重 0（V0 LM + clean lexicon） | 0.523 | 0.703 | 14 / 12 | 0.637 | 0.797 | 0.773 | 0.835 | 0.863 |
| 日常權重 0.1 | 0.643 | 0.763 | 34 / 14 | 0.735 | 0.860 | 0.843 | 0.835 | 0.868 |
| 日常權重 0.25 | 0.650 | 0.780 | 36 / 11 | 0.746 | 0.867 | 0.857 | 0.802 | 0.858 |
| **日常權重 0.5（選出）** | 0.650 | 0.787 | 42 / 15 | 0.751 | 0.873 | 0.857 | 0.790 | 0.858 |

- frozen teacher everyday Top-1 0.697 → 0.787（+9.0 個百分點）；GOV teacher 0.860 → 0.858（18 / 19）。
- 0.25 與 0.5 的 primary 差 2 句，依規則選 0.5；0.1 在 GOV 反而優於 V0（0.835 / 0.868），everyday teacher 0.763。
- 診斷（不可選）：加入 OASST1 的混合 LM everyday teacher 0.790，與 Tatoeba 單獨相差 1 句。
- teacher window 從 0.747 升到 0.857，與上一輪的 E 設定（0.847）相近，沒有重跑 K=8。

## 記憶體與延遲

同一份詞表在三種表示下（各自在新 process 量測）：

| lexicon | representation | load s | +RSS MB | lookup µs |
|---|---|---|---|---|
| 選出的詞表（42,548 entries，其中衍生 25,789） | frozen Lexicon | 0.93 | 78.7 | 0.12 |
| | frozen Lexicon + provenance 物件 | 0.98 | 79.0 | 0.13 |
| | compact（1.26 MB artifact） | 0.12 | 10.0 | 1.17 |
| R0 舊作法（154,115 entries） | frozen Lexicon | 3.23 | 262.3 | 0.20 |
| | compact（5.37 MB） | 0.16 | 21.5 | 1.30 |

- 上一輪的 347 MB 主要是 frozen Lexicon 建置後留在 process 的記憶體（provenance 物件只佔不到 1 MB），不是量測誤差。
- compact 表示：文字、讀音 id、權重、來源與 provenance id 放在 numpy 陣列，lookup 時才建立 LexiconEntry（LRU 快取）；
  provenance id 可以由另一份 JSON 還原來源。建置結果逐位元組 deterministic。
- 最終設定的執行期增量：日常 LM 0.84 MB / RSS +9.5 MB，compact 詞表 1.26 MB / RSS +1.9 MB，合計 +11.4 MB（V0 本身約 328 MB）。
- LM 快取：以 (history, char) 快取 `extend`，結果逐位元相同；DEV 命中率約 64%。
- 同一次執行比較（700 句）：frozen Lexicon + 未快取 LM 87 / 238 ms（p50 / p95）→ compact + 快取 65 / 208 ms，候選與分數 0 差異。
  各設定表格中的延遲受 GPU / 子程序同時執行影響，波動大（p50 36–76 ms），只作參考。
- 快取目前上限 100 萬筆；本機 IME 使用前需要依記憶體預算調小並量測。

## 重現

```bash
python -m zaoseq_bopomofo.daily build
python -m zaoseq_bopomofo.daily round2
python -m zaoseq_bopomofo.daily report2
```
