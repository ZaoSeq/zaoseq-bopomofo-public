# data/corpus — 授權依各來源（不是 Apache-2.0）

每個子目錄 `<source_id>/` 是對應政府開放資料集的正規化衍生資料，依該來源的授權使用，
目前全部是政府資料開放授權條款第 1 版（https://data.gov.tw/license），須依 ../SOURCES.md 所列方式顯名。

- `<source_id>/sentences.jsonl`：正規化後的句子，含 source_id、doc_id 與 split（不進 git，可重建）。
- `lm/`：由 train split 計算的字元 n-gram 與詞頻統計（`*.gz` 不進 git，可重建；`manifest.json` 進 git）。
- `manifest.json`：各來源句數、split 與輸入檔 SHA-256。

重建：`python -m zaoseq_bopomofo.corpus build`。
