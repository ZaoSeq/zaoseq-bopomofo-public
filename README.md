# 造序注音 ZaoSeq Bopomofo — public core

繁體中文注音輸入的研究核心：注音解析、候選產生（decoder）、詞庫與語料工具、授權稽核，以及評估框架與研究結果。
由造序科技（籌備中）開發。

> 這是從內部 repository 匯出的**公開子集**，不是完整的 production 系統。
> production 排序模型（fine-tuned ranker）的訓練、權重、模型載入與部署不在這裡，
> 因此本 repository **無法重現 production 排序結果**。邊界說明見 [docs/PUBLIC_BOUNDARY.md](docs/PUBLIC_BOUNDARY.md)。

## v0.2 Research Preview

- v0.2 decoder 在 v0.1 的政府語料之外，加入兩個官方且授權明確的日常語料：Tatoeba 與 Mozilla Common Voice 27.0 zh-TW
  （LM 權重 0.5 / 0.5），並使用由語料統計衍生的日常詞表（R2 讀音政策、L5 詞表過濾、daily_only 先驗）。
- 設定只在 DEV 上選擇，事前凍結選擇規則；之後建立全新的 sealed TEST-V1，在凍結設定之後只評估一次，結果為 PASS
  （`benchmarks/results/v0.2_sealed_test.md`）。
- **沒有正式的 runtime validation**：v0.2 是 Research Preview，production runtime（快取容量、延遲）的定案延後，
  本版本不提供官方延遲數字（`benchmarks/results/v0.2_runtime_status.json`）。

## 內容

| 模組 | 用途 |
|---|---|
| `phonetics/` | 注音符號、標準排列鍵盤、音節組字與解析 |
| `lexicon/` | 詞庫（CNS11643 單字讀音 + 專案維護的 builtin 詞表） |
| `decoding/` | lattice decoder、候選產生、CandidateFamily、V0 baseline 設定 |
| `corpus/` | 政府開放資料語料的匯入、正規化、斷句、切分與字元 n-gram 語言模型 |
| `daily/` | 日常語料來源稽核（LicenseGate）、品質檢查、評估集排除、衍生詞表、compact lexicon 與語料 ablation |
| `coverage/` | 候選涵蓋率分析與 Coverage-DEV |
| `ranking/` | 排序介面（`CandidateRanker`）、詞頻 / 語料 baseline、contextual 排序框架與 hybrid |
| `evaluation/` | benchmark、指標、freeze 紀錄驗證 |

## 可重現的程度

1. **可由本 repository 的元件重建**：V0 與 v0.2 decoder、詞庫、語料語言模型、衍生詞表，以及 Coverage-DEV / GOV-DEV / TEST-V1 上的
   decoder 指標。語料需依 `data/sources.json` 與 `data/daily/SOURCES.json` 自行從官方來源取得（原始檔不在 repository 中；
   Common Voice 需經 Mozilla Data Collective 取得，平台條款不允許轉散布），再以 `corpus`、`daily` 的 builder 重建語言模型與詞表；
   sealed 評估的執行腳本與 semantic freeze 驗證器留在內部。
2. **只報告、無法由本 repository 重現**：frozen teacher（fine-tuned 排序模型）的所有指標，包括 sealed TEST 的 final Top-1。
3. **不提供**：production 延遲與 runtime 設定（v0.2 runtime closure 延後）。
4. **完整原始碼驗證**：v0.1 的 `FINAL.json`、v0.2 的 semantic freeze 紀錄與模型只在內部 repository 驗證；
   `PUBLIC_DISTRIBUTION.json` 記錄匯出來源 commit、排除的元件與私有紀錄的雜湊。

部分研究程式在需要 teacher 時會嘗試載入不在公開版本中的模組，這些路徑在公開版本會出現 `ModuleNotFoundError`；
清單記錄在 `PUBLIC_DISTRIBUTION.json` 的 `audit.lazy_private_imports`。

## 使用

```bash
pip install -e ".[dev]"
python -m pytest
python -m zaoseq_bopomofo.corpus build
python -m zaoseq_bopomofo.daily audit
```

## 研究文件

- 候選產生與涵蓋率：[docs/CANDIDATE_COVERAGE.md](docs/CANDIDATE_COVERAGE.md)
- 日常語料 V1：[docs/DAILY_CORPUS.md](docs/DAILY_CORPUS.md)
- 日常語料 Round 2 與詞表清理：[docs/DAILY_CORPUS_ROUND2.md](docs/DAILY_CORPUS_ROUND2.md)
- v0.2 sealed evaluation：[benchmarks/results/v0.2_sealed_test.md](benchmarks/results/v0.2_sealed_test.md)
- 線上 Demo 的 HTTP API 合約：[docs/API.md](docs/API.md)

所有 benchmark 都是本專案的內部基準，不是與任何商用輸入法的比較。

## 授權

程式碼以 Apache License 2.0 發布（LICENSE、NOTICE）。`data/` 內的資料依各來源授權，不適用 Apache-2.0；
第三方元件與資料來源見 THIRD_PARTY_NOTICES.md、data/SOURCES.md 與 data/daily/SOURCES.json。
本專案不包含、也不依賴 McBopomofo、新酷音（Chewing）、Rime 或其他輸入法的程式碼與詞庫。
