# 造序注音 ZaoSeq Bopomofo

**v0.3.0 Research Preview · 2026-10-05**

繁體中文注音輸入的公開研究核心，由造序科技（籌備中）開發。

本版新增可獨立使用的高階字元 n-gram、Witten–Bell / Kneser–Ney 語言模型、混合模型與繁體字形檢查 decoder。保留注音解析、詞庫、候選產生、語料授權稽核及既有評估工具。

本次發布的是程式研究預覽，沒有新增正式 benchmark 或品質結論。既有 v0.2 sealed TEST-V1 結果保留為歷史紀錄；新版本的正式 benchmark 將在封存評估完成後另行發布。

## 使用

```bash
python -m pip install -e ".[dev]"
python -m pytest
python examples/decoder_preview.py
```

範例只使用自帶的小型詞庫與示例句子，可在本機離線執行。完整語料需依來源授權自行取得與重建。

## 公開內容

| 元件 | 內容 |
|---|---|
| phonetics / lexicon / decoding | 注音、詞庫與候選產生 |
| decoder_v3 | 高階 n-gram、混合語言模型與繁體字形檢查 |
| corpus / daily | 語料處理、來源授權稽核與衍生詞表 |
| coverage / evaluation / ranking | 涵蓋率、評估指標與排序介面 |

正式產品的排序模型、訓練配方、權重、部署、Windows 輸入法整合與未執行的測試資料保留在私密專案。本版不含可直接安裝的系統輸入法。

## 報告與授權

- [v0.3.0 發布報告](docs/RESEARCH_PREVIEW_V0.3.md)
- [v0.2 歷史評估](benchmarks/results/v0.2_sealed_test.md)
- [公開範圍](docs/PUBLIC_BOUNDARY.md)
- [ZaoSeq Labs](https://lab.zaoseq.com/bopomofo)

程式碼採 Apache-2.0；資料依各來源授權，見 LICENSE、NOTICE、THIRD_PARTY_NOTICES.md 與 data/SOURCES.md。PUBLIC_DISTRIBUTION.json 記錄公開檔案的 SHA-256。
