# Release notes（public core）

## 0.2.0 — Research Preview

匯出來源 commit 與檔案雜湊記錄在 `PUBLIC_DISTRIBUTION.json`。

### 內容

- v0.2 decoder：政府語料 LM 0.5 + 官方日常語料 LM 0.5（Tatoeba、Mozilla Common Voice 27.0 zh-TW），
  日常衍生詞表（R2 / L5 / daily_only），beam 48、nbest 20、CandidateFamily 不變。
- 日常語料來源稽核：Common Voice 只使用 Mozilla Data Collective 的確切版本（cv-corpus-27.0-2026-09-11），
  只取句子 id 與句子文字，不使用說話者資料；原始資料不在 repository 中。
- 事前凍結的選擇規則與 Round 3 addendum、sealed TEST-V1（EVERYDAY 480 句、GOV 211 句）及其 test plan、decision plan、gate 與 seal 紀錄。

### Sealed TEST-V1（凍結設定之後只評估一次）

| | v0.1 | v0.2 |
|---|---|---|
| EVERYDAY decoder Top-1（可由本 repository 重現） | 0.496 | 0.658 |
| EVERYDAY final Top-1（frozen teacher，只報告） | 0.667 | 0.817 |
| GOV decoder Top-1（可由本 repository 重現） | 0.697 | 0.711 |
| GOV final Top-1（frozen teacher，只報告） | 0.768 | 0.801 |

依事前凍結的 decision plan 判定 PASS。EVERYDAY 為在專案負責人指示下以 AI 輔助撰寫的句子，不代表真實使用者輸入的分布；
GOV 只有 211 句，差異的統計檢定力有限。細節見 `benchmarks/results/v0.2_sealed_test.md`。

### Runtime

- **v0.2 沒有完成正式的 runtime validation。** runtime closure 延後（`benchmarks/results/v0.2_runtime_status.json`），
  未指定 production 快取容量，本版本不提供官方延遲數字。
- LM 快取不影響任何候選或分數（各容量輸出逐項相同）；sealed 評估使用不經快取的參照路徑。

## 兩種驗證

- **Public distribution verification**：本 repository 的每個檔案都與 `PUBLIC_DISTRIBUTION.json` 的 SHA-256 相同（文字檔以 LF 換行計算）。
  這證明公開內容就是某個內部 commit 依白名單匯出的結果。
- **Full-source verification**：v0.1 的 `FINAL.json`、v0.2 的 semantic freeze 紀錄與模型權重只在內部 repository 驗證。
  `PUBLIC_DISTRIBUTION.json` 的 `private_commitments` 記錄這些私有紀錄的雜湊，日後可以比對，但本 repository 本身無法完成這項驗證。

## 不宣稱的事

- 不宣稱可以由本 repository 重現 production 排序結果或 frozen teacher 的任何指標。
- 不宣稱 production 延遲、快取設定或 runtime 已驗證。
- 不宣稱優於任何商用輸入法。

## 0.1.0 — Research Preview（2026-09-23）

見 tag `v0.1.0`。
