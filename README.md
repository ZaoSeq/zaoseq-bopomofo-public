# 造序注音 ZaoSeq Bopomofo — public core v0.1.0

繁體中文注音輸入的研究核心：注音解析、候選產生（decoder）、詞庫、政府開放資料語料工具與評估框架。
由造序科技（籌備中）開發。

> 這是 v0.1.0 Research Preview 的**公開子集**。production 排序模型（及其訓練、權重、模型載入、服務與部署）不在這裡，
> 因此本版本**無法重現 v0.1 的 production 排序結果**。邊界說明見 [docs/PUBLIC_BOUNDARY.md](docs/PUBLIC_BOUNDARY.md)。

## 內容

| 模組 | 用途 |
|---|---|
| `phonetics/` | 注音符號、標準排列鍵盤、音節組字與解析 |
| `lexicon/` | 詞庫（CNS11643 單字讀音 + 專案維護的 builtin 詞表） |
| `decoding/` | lattice decoder、候選產生、CandidateFamily、V0 baseline 設定 |
| `corpus/` | 政府開放資料語料的匯入、正規化、斷句、切分與字元 n-gram 語言模型 |
| `ranking/` | 排序介面（`CandidateRanker`）、詞頻 / 語料 baseline、排序框架 |
| `evaluation/` | benchmark、指標、測試集與 V0 freeze 紀錄驗證 |

## 可重現的程度

1. **可由本版本重現**：V0 decoder、詞庫、語料語言模型與 decoder 指標。語料需依 `data/sources.json` 自行從官方來源下載。
2. **只報告、無法由本版本重現**：production 排序模型的所有指標。
3. **歷史完整驗證**：v0.1 的完整原始碼與模型只在內部 repository 驗證；`PUBLIC_DISTRIBUTION.json` 記錄匯出來源與私有紀錄的雜湊。

## 使用

```bash
pip install -e ".[dev]"
python -m pytest
python -m zaoseq_bopomofo.corpus build
```

所有 benchmark 都是本專案的內部基準，不是與任何商用輸入法的比較。

## 授權

程式碼以 Apache License 2.0 發布（LICENSE、NOTICE）。`data/` 內的資料依各來源授權，不適用 Apache-2.0；
第三方元件與資料來源見 THIRD_PARTY_NOTICES.md 與 data/SOURCES.md。
本專案不包含、也不依賴 McBopomofo、新酷音（Chewing）、Rime 或其他輸入法的程式碼與詞庫。
