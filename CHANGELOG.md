# Changelog（public core）

本檔只記錄公開子集的內容。production 排序模型的訓練與部署紀錄在內部 repository。

## 0.2.0 — Research Preview

### Coverage-DEV 與候選涵蓋率
- Coverage-DEV v1.0（300 句人工撰寫、人工斷詞）與 v1.1（只修正 cv19 的可接受寫法）。
- `coverage.CoverageLattice`：可追蹤的候選產生器，V0 設定與 frozen decoder 逐項相同；missing-candidate taxonomy。
- 結論：search 不是瓶頸，日常 recall 受限於詞彙與語料統計。

### 日常語料與衍生詞表
- 來源稽核（`data/daily/SOURCES.json`）：只有官方版本且授權明確者可 APPROVED；approval scope 區分 production 與 DEV 實驗。
- 字形檢查（不做簡轉繁）、品質統計、評估集近重複排除、文件層級切分、日常 LM 插值。
- 衍生詞讀音政策（不展開讀音組合）、一般訊號的模板過濾、事前固定的 lexical prior。
- compact lexicon：同一詞表 RSS 78.7 → 10.0 MB、載入 0.93 → 0.12 s，輸出與原表示完全相同。
- 事前凍結的 selection plan（`benchmarks/frozen/v0.2_selection_plan.json`）。

### Round 3
- Mozilla Common Voice 27.0 zh-TW（Mozilla Data Collective 確切版本）：archive 與成員雜湊稽核、句子 id 與 NFC 全文去重、評估集排除。
- 事前凍結的 Round 3 addendum；Stage 5 語料 ablation 選出政府 0.5 + Tatoeba 與 Common Voice 合併 0.5。
- `BoundedLanguageModelCache`（LRU，輸出與不快取逐項相同）；production 容量未定案（runtime closure 延後）。

### v0.2 semantic freeze 與 sealed TEST-V1
- 選定設定在 TEST 建立前凍結；test plan、decision plan 與 gate 在 TEST 存在之前寫定，TEST 建立後 seal。
- TEST-V1-EVERYDAY（480 句，16 類）與 TEST-V1-GOV（211 句，未被使用過的政府文件），洩漏篩選後 0 項重疊。
- 只評估一次，依 decision plan 判定 PASS（`benchmarks/results/v0.2_sealed_test.md`）。

## 0.1.0 — Research Preview（2026-09-23）

- 注音解析、標準排列鍵盤、CNS11643 字音詞庫、lattice decoder 與 V0 baseline（`benchmarks/frozen/V0.json`）。
- 政府開放資料語料的匯入、領域平衡語言模型。
- 人工 DEV / sanity、TEST-EVERYDAY / TEST-GOV / TEST-TYPO（v0.2 起只作 reference）。
- v0.1 的 production 排序模型與其驗證紀錄不在公開版本中。
