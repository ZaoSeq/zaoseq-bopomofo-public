# Candidate Generation / Decoder Coverage V1

所有數字只來自 DEV：Coverage-DEV（300 句，[benchmarks/coverage_v1/](../benchmarks/coverage_v1/)）與 GOV-DEV（corpus split `test` 的規則標注片段，400 句）。
v0.1 sealed TEST 從這一輪起是 **V0.1 REFERENCE TEST**，只用於 Coverage-DEV 的洩漏檢查，沒有用於任何決策。
frozen V0 decoder 與 fine-tuned Laya teacher 都沒有修改；實驗用的 `coverage.lattice.CoverageLattice` 在 V0 設定下與 frozen decoder 於 700 句上逐項相同（文字、順序、分數）。
完整數據：[coverage_v1.md](../benchmarks/results/coverage_v1.md)、[coverage_v1.json](../benchmarks/results/coverage_v1.json)。

## Coverage-DEV

- 300 句、2,529 字，12 類各 25 句（conversation、school、work、technology、transport、shopping_food、names_places、time_schedule、social_chat、homophone、long_composition、segmentation），26 句附前文。
- 人工撰寫並人工斷詞；29 個專有名詞、12 個口語詞有標記。讀音逐字檢查 CNS11643 合法性。
- 與語料全部 split、人工 DEV / sanity、v0.1 TEST-EVERYDAY / TEST-GOV 做 char 4-gram MinHash 近重複檢查（Jaccard ≥ 0.6）：初稿有 2 句與人工 DEV 重複，已替換；最終 0 筆重複，集合內部也沒有重複。
- cv19「唸」在 v1.0 未接受「念」（影響 1 句，0.33 個百分點）；本文數字維持 v1.0。Coverage-DEV v1.1（[benchmarks/coverage_v1_1/](../benchmarks/coverage_v1_1/)）只修正這一句，見 [DAILY_CORPUS.md](DAILY_CORPUS.md)。

## 1. v0.1 candidate recall 的主要瓶頸

**不是 search（beam / nbest / pruning），而是候選排序所依賴的詞彙與語料統計。**

V0 在 Coverage-DEV：

| R@1 | R@3 | R@5 | R@10 | unlimited | reachable | top-4 family window |
|---|---|---|---|---|---|---|
| 0.470 | 0.697 | 0.780 | 0.833 | 0.917 | 1.000 | 0.743 |

- **reachable 1.000、OOV 0、reading coverage 1.000**：每個 gold 都能由詞庫拼出，沒有缺字或缺讀音。
- **完全沒產生**：25 句（8.3%），全部是 beam 剪枝，沒有任何一句是詞庫拼不出。
- **有產生但排在前 5 名之外**：41 句（13.7%）。**這比「沒產生」多**。
- beam 加到 192 時 unlimited 升到 0.980，但 R@1–R@10 **完全不變**：被 beam 剪掉的 gold 即使留下來，分數也排不進前 10。
- 多字詞覆蓋率只有 24.5%（Coverage-DEV 780 個多字詞中 589 個不在詞庫）。

GOV-DEV（與語料同文體）則幾乎沒有這個問題：R@5 0.915、unlimited 0.978，缺失主要是單字選字的分數（67.6%）與 beam（24.3%）。

## 2. Missing-candidate taxonomy（V0，Coverage-DEV，77 句不在前 5 名或不在 4-family 視窗）

| 類別 | 句數 | 比例 | 說明 | 可否系統性改善 |
|---|---|---|---|---|
| lexical_missing | 32 | 41.6% | 錯誤位置的詞不在詞庫（例：自習室、口試、英檢）；其中 12 句被 beam 剪掉、20 句有產生但排得太後 | 需要帶日常頻率的詞彙與語料；從政府語料抽詞無效（見 3） |
| score_pruned | 17 | 22.1% | 單字選字輸給同音字（例：按→案、滑→華、唸→念*） | 需要日常語料的 LM 統計或 contextual ranker |
| beam_pruned | 11 | 14.3% | 單字選字在 beam 中被剪掉（例：倒→到、設→色） | beam 加大可產生，但排名仍進不了前 10 |
| candidate_family_issue | 11 | 14.3% | 全部是排第 5 名、剛好在 4-family 視窗外；CandidateFamily 分組本身沒有刪掉任何候選 | 屬於 teacher 視窗大小，本輪不調整 teacher |
| proper_noun | 4 | 5.2% | 嘉義、清境、野柳 | 需要授權清楚的地名 / 專有名詞來源 |
| colloquial_word | 2 | 2.6% | 幹嘛、蠻 | 需要日常 / 口語語料 |
| pronunciation_variant_missing、segmentation_missing、orthographic_variant、character_reading_missing、other | 0 | 0% | — | — |

\* 唸／念見上方已知標注問題。

## 3. 各項修改是否能泛化改善

| 修改 | Coverage-DEV R@5 | 延遲 | 結論 |
|---|---|---|---|
| nbest 20 → 50 / 100 | 不變（0.780） | 不變 | 前 10 名以內沒有差別 |
| beam 48 → 96 / 192 | 不變；unlimited 0.917 → 0.960 / 0.980 | p95 228 → 392 / 691 ms | 只增加「產生但排很後」的 gold，不採用 |
| beam 48 → 24 | 0.773（−2 句） | p50 82 → 40 ms、p95 228 → 104 ms | 延遲取向的 Pareto 點，本輪不採用 |
| 每個 span 限制詞條數（8 / 16 / 32） | 0.490 / 0.723 / 0.770 | 更快 | 會剪掉正確單字，不採用 |
| 保護詞表路徑的額外 beam（16 / 32） | 不變 | 變慢 | 無效 |
| 輕聲 / 本調互通查詢 | 0.757 | 不變 | 增加競爭候選，變差 |
| beam 只用詞表分數剪枝 | 0.370 | — | 語料 LM prior 是必要的，並沒有「太早剪枝」 |
| 從 TRAIN 語料抽詞（c20, PMI≥5, 31,015 詞條） | 0.777；R@1 +1.7 個百分點（p=0.27） | 相近 | 詞彙覆蓋 24.5% → 51.7%，日常 recall 沒有顯著改善；GOV-DEV R@1 +2.8 個百分點（p=0.04） |
| oracle：直接加入 Coverage-DEV 的 gold 詞（診斷上限） | **0.943**；R@1 0.717 | 相近 | 只作上限，不可採用 |

oracle 與抽詞結果的差距說明：幫助來自「知道哪個詞是對的」並給它先驗，而不是單純詞條數量。
從政府語料抽出的詞表把同音競爭詞一起加入，優勢互相抵銷。

## 4. 最佳 candidate-generation config

**維持 V0 的 generation 參數（beam 48、nbest 20、不限 span 詞條數）。** 沒有任何 decoder 端的修改在 DEV 上顯著改善日常 recall。

- 從語料抽詞（`derived_c20_pmi5_w10`）是下一階段 lexicon V1 的候選元件：GOV-DEV decoder-order R@1 +2.8 個百分點（18 fixed / 7 broken，p=0.04），日常不顯著；加上 frozen teacher 後兩個 DEV 都沒有差異（Coverage-DEV 0.693 → 0.710，p=0.36；GOV-DEV 0.860 → 0.860）。本輪不採用。
- beam 24 是延遲取向的候選，留給本機輸入法階段再評估。

## 5. Recall@5 / @10 提升多少

採用的設定（V0）沒有變化：R@5 0.780、R@10 0.833。可達到的最大 unlimited recall 是 0.980（beam 192），但 R@5 / R@10 不變。
抽詞設定：R@5 0.777（−0.3）、R@10 0.843（+1.0 個百分點），都在 300 句的雜訊範圍內。

## 6. Latency 代價

- V0 在 Coverage-DEV（平均 8.4 字）p50 82 ms、p95 228 ms（本機 CPU，重複量測約 ±15% 雜訊）。
- 時間分布：語料 LM 計分 64%、lattice 內部物件與迴圈 31%、beam 排序 3%、詞庫查詢 1%、k-best 1%、CandidateFamily 0.1%。
- beam 96 / 192 的 p95 為 392 / 691 ms，不符合「不要讓 decoder 變成幾百毫秒」的要求。
- 提升 recall 的方向（詞彙與語料）不需要增加 beam，因此不需要付出延遲代價；降低延遲的主要槓桿是 LM 計分（快取或 incremental scoring）。

## 7. 是否需要增加 lexicon / corpus

**需要，而且是帶日常頻率的詞彙與語料，不是更大的詞條清單。**

- 缺少的 589 個多字詞中 552 個（94%）已出現在政府 TRAIN 語料，LM 其實看過這些字串；但 Coverage-DEV 的字元 trigram 只有 31.6% 在政府語料出現過，日常句的統計支撐很薄。
- 從政府語料自動抽詞使詞彙覆蓋翻倍，日常 recall 卻不變；oracle 詞庫則大幅改善。缺的是日常用法的相對頻率。

### Common Voice zh-TW 評估（HOLD）

- Common Voice 官方 GitHub repo 的 `server/data/zh-TW/` 有 5 個句子檔（約 1.9 萬句，2018–2022）：`sentence-collector.txt`（15,580 句，投稿者聲明 CC0）、
  `setences.txt`（2,898）、`chatlogs.txt`（309，個人捐贈的聊天紀錄）、`lms.txt`（186，來源不明）、`taipei_city_gov.txt`（354，擷取自臺北市政府新聞稿）。
- 內容確實是臺灣繁體中文日常語句（無簡體字；含捷運、便當、悠遊卡等臺灣用語）。只加 sentence-collector 的 13.6 萬字，就讓 Coverage-DEV 的 trigram 覆蓋從 31.6% 升到 36.9%。
- repo 程式碼是 MPL-2.0，沒有資料授權檔；CC0 是 Common Voice 的政策宣稱。正式資料集自 2025 年 10 月起只在 Mozilla Data Collective 提供，需要帳號並同意新的服務條款。
- **判定：HOLD。** 原始出處不一（新聞稿、個人聊天紀錄、來源不明檔案），且正式取得管道需要同意條款。沒有匯入任何 production 或實驗資料，只在暫存區計算重疊比例。
  若要使用，建議先由人確認 Mozilla Data Collective 條款，且只考慮投稿者聲明 CC0 的 sentence-collector 子集。

## 8. 下一步：corpus V1 還是 decoder V1

**先做 corpus V1（授權清楚的日常繁中語料與帶頻率的詞彙），decoder V1 目前不需要。**

- decoder search 不是瓶頸：所有 search 參數對 R@1–R@10 都沒有改善，只改變延遲與 unlimited recall。
- 主要損失（lexical_missing 41.6% + score_pruned 22.1% + colloquial / proper noun 7.8%）都指向日常語言統計不足。
- decoder 端值得保留的只有兩件事：LM 計分的效能（佔 64% 時間），以及未來 teacher 視窗大小的評估（14.3% 的 case 正好是第 5 名）。

## 重現

```bash
python -m zaoseq_bopomofo.coverage.dataset build
python -m zaoseq_bopomofo.coverage.analysis --output benchmarks/results/coverage_v1_raw.json
python -m zaoseq_bopomofo.coverage.derived_lexicon --output benchmarks/results/coverage_v1_derived.json
python -m zaoseq_bopomofo.coverage.teacher --output benchmarks/results/coverage_v1_teacher.json
python -m zaoseq_bopomofo.coverage.report
```
