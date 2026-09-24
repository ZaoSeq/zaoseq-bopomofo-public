# 造序注音 v0.1 HTTP API（api_version "1"）

網站端只依賴本 HTTP 合約，不 import Python core。所有路徑相對於模型服務的 origin。

## POST /api/bopomofo/rank

服務是無狀態的：composition（尚未送出的讀音）由網站端保存，每次把「已確認前文」與「目前整段讀音」送來，
回傳這段讀音的候選與第一名。游標、選字後的送出由網站端處理。

### Request

```json
{
  "committed_left": "我明天會",
  "readings": "ㄗㄞˋ ㄑㄩˋ ㄊㄞˊ ㄅㄟˇ",
  "max_candidates": 10,
  "compare_mode": false
}
```

| 欄位 | 型別 | 說明 |
|---|---|---|
| `committed_left` | string，≤ 512 字，選填 | 使用者已確認送出的前文；只取最後 64 字做情境。 |
| `readings` | string，1–128 字 | 注音（音節以空白分隔，可省略一聲）或標準（大千）排列按鍵，例如 `y94 fm4`；最多 12 個音節。 |
| `max_candidates` | int，1–20，預設 10 | 回傳候選數上限。 |
| `compare_mode` | bool，預設 false | true 時額外回傳 `compare`（研究比較用）。 |

### Response 200

```json
{
  "api_version": "1",
  "final_text": "再去台北",
  "composition": {
    "readings": ["ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ"],
    "text": "再去台北",
    "segments": [{"text": "再", "readings": ["ㄗㄞˋ"]}, {"text": "去", "readings": ["ㄑㄩˋ"]}, {"text": "台北", "readings": ["ㄊㄞˊ", "ㄅㄟˇ"]}]
  },
  "candidates": [
    {"text": "再去台北", "segments": [...]},
    {"text": "在去台北", "segments": [...]}
  ],
  "engine_mode": "fine_tuned_laya",
  "fallback_reason": null,
  "model_ready": true,
  "latency_ms": {"decoder": 12.3, "contextual": 18.1, "total": 30.6}
}
```

| 欄位 | 說明 |
|---|---|
| `final_text` | 這段 composition 目前的第一名（不含 `committed_left`）。沒有候選時為空字串。 |
| `composition` | 本次解析出的讀音，以及第一名的分段。 |
| `candidates` | 依最終排序的候選，第一個等於 `final_text`。一般模式不含分數。 |
| `engine_mode` | `fine_tuned_laya`：由 fine-tuned 排序模型排序；`v0_fallback`：完整使用 V0 排序。 |
| `fallback_reason` | `engine_mode` 為 `v0_fallback` 時的原因：`model_not_ready`、`model_unavailable`、`model_disabled`、`inference_error`、`timeout`；否則為 null。 |
| `model_ready` | 模型已載入、驗證並暖機完成。 |
| `latency_ms` | 伺服器內部量測：`decoder`（V0 候選產生）、`contextual`（排序模型，fallback 前未呼叫時為 null）、`total`。不含網路。 |

`experimental` 只在伺服器以 `ZAOSEQ_TYPO_CORRECTION=1` 啟動時出現（`{"typo_correction": true}`），
此時候選另帶 `experimental_correction`。v0.1 production 預設關閉，網站端應標示 Experimental。

### compare_mode

```json
"compare": {
  "score_note": "Scores are uncalibrated ranking scores, not probabilities of correctness.",
  "v0": [{"text": "在去台北", "v0_score": -35.655}],
  "fine_tuned_laya": [{"text": "再去台北", "model_score": 0.9312}]
}
```

- `v0_score`：V0 的 log10 分數，只能在同一個 request 內比較。
- `model_score`：排序模型對 V0 前 4 個候選的分數，**未校準**，不是正確率；前 4 名以外為 null。
- 模型 fallback 時 `fine_tuned_laya` 為 null。

### 錯誤

| 狀態 | `detail` | 說明 |
|---|---|---|
| 422 | `invalid_bopomofo`、`too_many_syllables` 或欄位驗證錯誤 | 輸入不合法。 |
| 429 | `busy` | 單一 GPU 同時只處理一個排序 request；帶 `Retry-After: 2`。 |
| 503 | `decoder_not_ready` | 部署缺少 V0 語料統計檔（部署錯誤，不是模型 fallback）。 |
| 500 | `internal_error` | 不應發生；不回傳例外內容。 |

模型未就緒、失敗或逾時**不會**造成錯誤狀態碼，而是 200 + `engine_mode: "v0_fallback"`。

每個 response 帶 `X-Request-ID`（隨機值，不含輸入內容）。

## GET /health

程序存活：`200 {"status": "ok"}`。

## GET /ready

```json
{"ready": true, "model_state": "ready", "decoder_ready": true, "default_engine": "fine_tuned_laya"}
```

`ready` 為 true 時 200，否則 503。`model_state`：`not_loaded`、`loading`、`warming`、`ready`、`failed`、`disabled`。
網站端可在 503 時照常呼叫 rank（會得到 `v0_fallback`），但應顯示「模型載入中」。

## 隱私

- 輸入只用於當次推論，不儲存、不作為訓練資料。
- 應用程式 log 只記 request id、endpoint、狀態碼、延遲與 engine mode，不記前文、讀音、候選或 request body。
- 排序模型在同一台服務上執行，不呼叫第三方推論 API。
- 反向代理 / CDN 的存取紀錄由部署端設定，不得記錄 request body。

## 非合約端點

`/api/rank`、`/bopomofo/api/rank`、`/api/status`、`/bopomofo/api/status` 只供本 repo 內建的 demo 頁使用，隨時可能變更。
