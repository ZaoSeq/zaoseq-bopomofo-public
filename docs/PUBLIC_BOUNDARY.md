# Public / private 邊界

造序注音分成三個 repository：

| repository | 可見性 | 內容 |
|---|---|---|
| zaoseq-bopomofo（本 repository） | Public | 注音解析、decoder、詞庫與語料工具、授權稽核、評估框架、研究結果 |
| zaoseq-ranker | Private | production 排序模型的訓練、hard-negative、蒸餾、模型載入、權重與部署 |
| zaoseq-ime-windows | Private | Windows 輸入法整合、產品功能、個人化 |

相依方向只有一個：私有 repository 依賴公開核心，公開核心不依賴任何私有程式。

## 判斷原則

- **公開**：能讓研究結果被檢驗與重現、且本身不是產品差異化來源的部分——decoder、詞庫與語料處理、授權稽核、評估方法與資料集。
- **私有**：production 排序模型的訓練配方與資料組成、模型權重與載入方式、部署設定、輸入法產品行為與個人化資料。

## 本版本排除的元件

排除清單、原因與去處記錄在 `PUBLIC_DISTRIBUTION.json` 的 `excluded_components`。
目前 API service 會直接載入私有模型，所以暫不公開；公開的 API 層（可插入不同排序模型）之後再拆出。
v0.2 的 semantic freeze 紀錄鎖定私有排序模型的 checkpoint 與訓練設定，只公開其雜湊（`private_commitments`）；sealed TEST-V1 的資料、test plan、decision plan、gate 與 seal 是公開的。

## 資料

- 第三方原始語料、模型權重與產生的語言模型 / 詞表 artifact 都不在任何 repository 中；repository 只保存來源、授權、雜湊與統計。
- 評估集中尚未執行的 sealed TEST 在執行前不會公開；TEST-V1 已在凍結設定後執行一次，因此與結果一起公開。
- frozen teacher 的逐句結果不公開，只公開彙總指標。
- 在非安靜環境下量到的延遲資料不公開，v0.2 不提供官方延遲。
