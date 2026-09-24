# Sealed TEST（v0.1.0）

- `everyday.jsonl`（TEST-EVERYDAY，264）與 `gov.jsonl`（TEST-GOV，800）：在 `benchmarks/frozen/FINAL.json` freeze 之後只執行過一次，
  結果見 `benchmarks/results/test_final.md`。之後不得依這些結果調整模型或設定；若要調整，這份 TEST 降級為 DEV，並另建新的 TEST。
- `typo.jsonl` 已在同一次執行中被評估過，因此自 v0.1.0 起定位為 **TYPO-REFERENCE-v0**：只作為參考，
  不得作為未來 typo threshold 調整後的 untouched final test。未來 typo 評估需另建新的 sealed set。
- 所有檔案的 SHA-256 記錄於 `MANIFEST.json`（由 FINAL.json 鎖定，不修改）。
