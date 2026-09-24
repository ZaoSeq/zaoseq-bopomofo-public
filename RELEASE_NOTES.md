# Release notes（public core）

## 0.1.0 — public core

v0.1.0 Research Preview（2026-09-23）的公開子集。匯出來源 commit 與檔案雜湊記錄在 `PUBLIC_DISTRIBUTION.json`。

- 注音解析、decoder、詞庫、政府語料語言模型與 V0 baseline（`benchmarks/frozen/V0.json`）
- 評估框架、DEV / sanity / TEST 資料集與研究結果
- 不含 production 排序模型、訓練程式、權重、服務與部署

## 兩種驗證

- **Public distribution verification**：每個檔案都與 `PUBLIC_DISTRIBUTION.json` 的 SHA-256 相同（文字檔以 LF 換行計算）。
  這證明公開內容就是 v0.1.0 內部 commit 依白名單匯出的結果。
- **Historical full-source verification**：v0.1.0 的完整原始碼、`FINAL.json` 與模型權重只在內部 repository 驗證。
  `PUBLIC_DISTRIBUTION.json` 的 `private_commitments` 記錄這些私有紀錄的雜湊，日後可以比對，但本版本本身無法完成這項驗證。

## 不宣稱的事

- 不宣稱可以由本版本重現 v0.1 的 production 排序結果。
- 不宣稱優於任何商用輸入法。
