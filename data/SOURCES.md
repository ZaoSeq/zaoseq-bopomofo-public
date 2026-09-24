# 資料來源與授權紀錄

本檔由 `data/sources.json` 產生（`python -m zaoseq_bopomofo.corpus.sources_md`），請修改 JSON 而不是本檔。

資料採白名單制：任一授權欄位狀態不明（`unknown` 或空白）的來源不得進 production corpus，
`python -m zaoseq_bopomofo.corpus check` 會列出每個來源能否使用與原因。
授權欄位以 data.gov.tw 資料集頁面與 API 的 license metadata 為準（2026-09-23 查核），不以搜尋結果為準。

## 授權判讀摘要

政府資料開放授權條款第 1 版：不限目的、時間與地域，可重製、改作、編輯、公開傳輸與轉授權，含商業利用；
必須依條款附件顯名；不含專利與商標；資料涉及第三人權利時提供機關得停止授權。
條款沒有明文提到 AI／機器學習訓練，因此 `ai_training` 記為 `allowed_under_general_grant`，
`ai_training_explicit` 為 false，`ai_training_basis` 為 "general unrestricted-purpose license grant"。
**不宣稱政府明文允許 AI 訓練。** 用於 n-gram 統計、decoder、ranking data 產生，以及 2026-09-23 的
排序模型的研究訓練（權重不散布；訓練資料的組成不在公開版本中）。

**只使用資料集下載內容本身。** 資料集欄位中指向外部網站的網址（法規網址、新聞稿連結、附件）不屬於下載內容，
不自動視為同一授權，一律不抓取。

原始下載檔放在 `data/raw/<source_id>/`，不進 git；以下 SHA-256 是 2026-09-23 下載的檔案。
語料衍生檔在 `data/corpus/<source_id>/`，依該來源授權，不適用本專案程式碼的 Apache-2.0。

## 已登錄來源

### cns11643

```
dataset_name: CNS11643中文標準交換碼全字庫(簡稱全字庫)
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/5961
download_url: https://www.cns11643.gov.tw/opendata/Properties.zip ; https://www.cns11643.gov.tw/opendata/MapingTables.zip
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)（資料集另可選 OFL 1.1，僅適用字型；本專案選用 OGDL）
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: character_data
attribution: 資料來源：數位發展部，CNS11643中文標準交換碼全字庫，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-22
upstream_version_or_updated_at: release 20260805
sha256: Properties.zip 3d56ef14cc8099893245dac58fe4718d2fa64812b9159352a98a4588ad3efa5c; MapingTables.zip 4502fcf7b433d679dee51127298929543ec7f4aa99be93cd219df1552bc3d2bf
allowed_uses: character_readings, candidate_generation, reading_annotation
text_fields: —
excluded_fields: —
status: approved
production_ready: yes
notes: 只使用 CNS_phonetic.txt 與 CNS→Unicode 對照表；未使用字型與聲音檔。
```

### moj_law_zh

```
dataset_name: 中文法規_法律資料檔下載
provider: 法務部資訊處
official_dataset_url: https://data.gov.tw/dataset/18289
download_url: https://sendlaw.moj.gov.tw/PublicData/GetFile.ashx?DType=XML&AuData=CF
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: legal
attribution: 資料來源：法務部資訊處，中文法規_法律資料檔下載，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:20+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-05 14:29:12
sha256: d8d634f7fddc40d3fe0bad7d5ba8cc9b0311caa4311998470dbf1ba98c629811
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 法規名稱, 前言, 條文內容
excluded_fields: 法規網址, 英文法規名稱, 附件, 沿革內容
status: approved
production_ready: yes
notes: zip 內 FalV.xml。只匯入法規名稱、前言與條文內容；法規網址指向的網頁與附件不在下載內容內，不抓取。法律條文依著作權法第 9 條本身不受著作權保護。文體為法律語體，與日常用語差異大。
```

### gsn_qa

```
dataset_name: GSN政府網際服務網_問與答
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/171425
download_url: https://gsn.nat.gov.tw/file/GSN_QA.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，GSN政府網際服務網_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:20+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-02-26 17:44:39; HTTP Last-Modified Fri, 13 Dec 2024 02:22:07 GMT
sha256: 5ad2eb689044e36ba7ddedd288720f2a47250e5f0ade8003557a7f04753f5d7f
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: faq_question, faq_answer
excluded_fields: —
status: approved
production_ready: yes
notes: —
```

### itaiwan_qa

```
dataset_name: iTaiwan公共區域免費無線上網_問與答
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/171426
download_url: https://itaiwan.gov.tw/file/iTaiwan_QA.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，iTaiwan公共區域免費無線上網_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:20+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-04-29 08:45:05; HTTP Last-Modified Wed, 12 Feb 2025 09:41:48 GMT
sha256: 3e5f3c1862ec040bb1c99a3bee32a1183db38800d2e7addac3d81c5bfa50c9ba
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: faq_question, faq_answer
excluded_fields: ID
status: approved
production_ready: yes
notes: —
```

### archives_edoc_faq

```
dataset_name: 電子文書檔案服務中心-常見問題
provider: 國家發展委員會檔案管理局
official_dataset_url: https://data.gov.tw/dataset/103298
download_url: https://www.archives.gov.tw/opendata/公文電子交換常見問題管理.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：國家發展委員會檔案管理局，電子文書檔案服務中心-常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:21+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-12-16 16:03:48
sha256: 9fe32030e76b15d15cd5e5d73e56f80e10fe9bb066c3cb44be96175b73a1766d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 內容
excluded_fields: —
status: approved
production_ready: yes
notes: —
```

### tipo_trade_secret_qa

```
dataset_name: 營業秘密問答集
provider: 經濟部智慧財產局
official_dataset_url: https://data.gov.tw/dataset/22320
download_url: https://tiponet.tipo.gov.tw/datagov/ot/064-104-001.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：經濟部智慧財產局，營業秘密問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:21+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-26 17:54:49; HTTP Last-Modified Fri, 14 Nov 2025 06:32:41 GMT
sha256: bafa1e71c88fee68afa3d4b8ee571c1411879226240a1a422b8c4eb405f3713c
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回應意見
excluded_fields: 網址
status: approved
production_ready: yes
notes: CSV 為 Big5 編碼。網址欄位指向外部網頁，不抓取。
```

### mofa_press_zh

```
dataset_name: 外交部全球資訊網-中文版-新聞稿
provider: 外交部
official_dataset_url: https://data.gov.tw/dataset/30143
download_url: https://www.mofa.gov.tw/OpenData.aspx?SN=EE2F7076AA496A86
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：外交部，外交部全球資訊網-中文版-新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:29+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-20 16:41:33
sha256: 8fe18b8cf136f25d52dc3431eec2ac0ac3f7c55fab684ee1bd0094f1664a102e
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: title, 內容
excluded_fields: Link, Source, FileName
status: approved
production_ready: yes
notes: 只使用下載 JSON 內的 title 與內容欄位（HTML 已剝除）；Source/Link 指向的外交部網頁與附件不抓取。新聞稿可能引述第三人發言，OGDL 不涵蓋第三人權利；若第三人主張權利須移除。每日更新，只含下載當下的最近 1000 則。
```

### naer_terms_public_admin

```
dataset_name: 國家教育研究院-行政學學術名詞
provider: 國家教育研究院
official_dataset_url: https://data.gov.tw/dataset/15262
download_url: https://opendata.naer.edu.tw/學術名詞/國家教育研究院-行政學學術名詞.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: terminology
attribution: 資料來源：國家教育研究院，國家教育研究院-行政學學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:29+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-12 15:23:17; HTTP Last-Modified Thu, 11 Jul 2024 02:39:52 GMT
sha256: 8faf844b2393fbb27f432a8a5df8e4194c6e64c8a0c7754b0a6242a7b2e4f05b
allowed_uses: vocabulary_statistics, corpus
text_fields: 中文名稱
excluded_fields: 英文名稱, 來源網站
status: approved
production_ready: yes
notes: 詞條清單，不是句子；不進字元語言模型，只用於詞彙統計。
```

### naer_terms_info_k12

```
dataset_name: 國家教育研究院-資訊名詞-高中含以下資訊學術名詞
provider: 國家教育研究院
official_dataset_url: https://data.gov.tw/dataset/15407
download_url: https://opendata.naer.edu.tw/學術名詞/國家教育研究院-資訊名詞-高中含以下資訊學術名詞.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: terminology
attribution: 資料來源：國家教育研究院，國家教育研究院-資訊名詞-高中含以下資訊學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:29+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-12 13:57:39; HTTP Last-Modified Fri, 12 Jul 2024 08:17:31 GMT
sha256: 9931846343405436c5487a1c491a75c7522d93436d75722816cf2e23a6dc10fc
allowed_uses: vocabulary_statistics, corpus
text_fields: 中文名稱
excluded_fields: 英文名稱, 來源網站
status: approved
production_ready: yes
notes: 詞條清單，不是句子；不進字元語言模型，只用於詞彙統計。
```

### naer_terms_management

```
dataset_name: 國家教育研究院-管理學學術名詞
provider: 國家教育研究院
official_dataset_url: https://data.gov.tw/dataset/15440
download_url: https://opendata.naer.edu.tw/學術名詞/國家教育研究院-管理學學術名詞.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: terminology
attribution: 資料來源：國家教育研究院，國家教育研究院-管理學學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:30+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-12 13:43:15; HTTP Last-Modified Tue, 16 Jul 2024 02:29:22 GMT
sha256: 2f323ca6b4cf2a5a83dc01b1b044551c809e73f2f025858fd0b69c7b99e2bf4d
allowed_uses: vocabulary_statistics, corpus
text_fields: 中文名稱
excluded_fields: 英文名稱, 中國大陸譯名, 來源網站
status: approved
production_ready: yes
notes: 詞條清單；「中國大陸譯名」欄為簡體中文，排除不用。不進字元語言模型。
```

### naer_terms_math

```
dataset_name: 國家教育研究院-數學學術名詞
provider: 國家教育研究院
official_dataset_url: https://data.gov.tw/dataset/15443
download_url: https://opendata.naer.edu.tw/學術名詞/國家教育研究院-數學學術名詞.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: terminology
attribution: 資料來源：國家教育研究院，國家教育研究院-數學學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T08:37:30+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-12 13:41:05; HTTP Last-Modified Tue, 16 Jul 2024 02:42:44 GMT
sha256: 7d87046b66433e4e9331065473b7b1d3f03cddfab4540e3b2315239ad47e802c
allowed_uses: vocabulary_statistics, corpus
text_fields: 中文名稱
excluded_fields: 英文名稱, 來源網站
status: approved
production_ready: yes
notes: 詞條清單，不是句子；不進字元語言模型，只用於詞彙統計。
```

### dgt_175294

```
dataset_name: 政府資料開放平臺常見問答(FAQ)
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/175294
download_url: https://www-api.moda.gov.tw/OpenData/Files/17486
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，政府資料開放平臺常見問答(FAQ)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:08+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-11-17 09:00:22
sha256: 00cb5d834444f6973da792c5d8ec8afced317d6d36c04360334e57c052a53e4d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回答
excluded_fields: 分類, 網址
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_175306

```
dataset_name: MyData平臺常見問答(FAQ)
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/175306
download_url: https://www-api.moda.gov.tw/OpenData/Files/17496
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，MyData平臺常見問答(FAQ)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:09+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-10-31 11:56:33
sha256: 2591773420057df81dca6006239731bcb77cfe94fb7a7386e6550a59b3ced34a
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答案
excluded_fields: 項目
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_175295

```
dataset_name: 政府資料標準平臺常見問答(FAQ)
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/175295
download_url: https://www-api.moda.gov.tw/OpenData/Files/17478
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，政府資料標準平臺常見問答(FAQ)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:10+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-11-17 10:57:29
sha256: ae10a073b0ef3738c9a338c80fcb6d3a6831956438ecba0e894553cdb1b929bc
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回答
excluded_fields: 網址
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_171427

```
dataset_name: 政府短網址服務_問與答
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/171427
download_url: https://url.gov.tw/OpenData_url_QA.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，政府短網址服務_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:11+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-07-14 14:27:13; HTTP Last-Modified Wed, 08 Apr 2026 07:10:11 GMT
sha256: 6d0166521e0deff695cd60f5f91ba49d6769369e54532928a48084ff3cdb3c8d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: faq_question, faq_answer
excluded_fields: —
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_171432

```
dataset_name: 政府專屬短碼簡訊平台_問與答
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/171432
download_url: https://s.moda.gov.tw/8NUnZD4hu6UL
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，政府專屬短碼簡訊平台_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:12+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-07-14 14:30:07; HTTP Last-Modified Fri, 29 Nov 2024 07:57:47 GMT
sha256: 8a98582e01a39602995dd1e734fcddee8f7c18a1adba5eaad5d0e1fb8d5825dd
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: faq_question, faq_answer
excluded_fields: —
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_11838

```
dataset_name: 1996內政服務熱線常見問題(QA)
provider: 資訊服務司
official_dataset_url: https://data.gov.tw/dataset/11838
download_url: https://opdadm.moi.gov.tw/api/v1/no-auth/resource/api/dataset/89040549-12D7-4137-873E-52FDC7C06158/resource/F31CBD8B-544D-46C2-804E-404F246C0D2B/download
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：資訊服務司，1996內政服務熱線常見問題(QA)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:14+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-30 23:31:02
sha256: 6e3345e243b243547cf8993ae46ca01423ea0e1af74e6b4409f27a7da529b1fa
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: QUESTION, ANSWER
excluded_fields: UNITNAME, SID, DEPTNAME, ROWNUM
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_45362

```
dataset_name: 新創圓夢網-創業常見問題
provider: 經濟部中小及新創企業署
official_dataset_url: https://data.gov.tw/dataset/45362
download_url: https://startup.sme.gov.tw/home/upload/opendata/gov_faq_opendata.json
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：經濟部中小及新創企業署，新創圓夢網-創業常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:15+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-09-22 13:43:18; HTTP Last-Modified Fri, 31 Jul 2026 07:24:03 GMT
sha256: c880569b55f90bba2a632b49dd2a59b6b5bc95687934a3d66802fd46573387ab
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題標題, 問題解答
excluded_fields: 類別, 建立時間, 修改時間
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_45909

```
dataset_name: 標檢局消費者Q&A
provider: 經濟部標準檢驗局
official_dataset_url: https://data.gov.tw/dataset/45909
download_url: https://safety.bsmi.gov.tw/wSite/public/Data/f6244329109369417.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：經濟部標準檢驗局，標檢局消費者Q&A，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:16+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2024-10-24 09:18:28
sha256: 942289e18045ab538b762ca3f6f42600a6e30fbc2c4edb1c489d96f8be447e97
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回答
excluded_fields: 編號
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_11024

```
dataset_name: 金管會民意信箱FAQ
provider: 金融監督管理委員會
official_dataset_url: https://data.gov.tw/dataset/11024
download_url: https://stat.fsc.gov.tw/api/v1/public/datasets/11024/export
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：金融監督管理委員會，金管會民意信箱FAQ，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:16+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-22 10:00:44
sha256: 992d71ac283e40305a5d9a2ab9776635048c18a1905f05422d2f489445312b8f
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題主旨, 問題內容, 答覆
excluded_fields: 公告日期, 問題種類, 單位, 建立日期, 編號
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_11185

```
dataset_name: 存款保險問答集
provider: 中央存款保險股份有限公司
official_dataset_url: https://data.gov.tw/dataset/11185
download_url: https://www.cdic.gov.tw/upload/opendata/存款保險問答集.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：中央存款保險股份有限公司，存款保險問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:17+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-09-21 17:04:57; HTTP Last-Modified Thu, 20 Nov 2025 07:15:19 GMT
sha256: fa42b9a4c2b03581b2a2516649d8b8b81b0a261258cc521036b133ae2cc11e56
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 存款保險問題, 答案
excluded_fields: 項次, 關鍵字, 更新日期(年), 更新日期(月), 更新日期(日), 提供機構, 來源網址
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_145013

```
dataset_name: 國家發展委員會個資法問與答
provider: 國家發展委員會
official_dataset_url: https://data.gov.tw/dataset/145013
download_url: https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS8zNDg4Ni84ZTA2ZmZlYi1lM2JlLTRhZGQtOGY1Mi1jYTlmNjkzZTJhOGYuY3N2&n=5ZyL5a6255m85bGV5aeU5ZOh5pyD5YCL6LOH5rOV5ZWP6IiH562ULmNzdg%3d%3d&icon=..csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：國家發展委員會，國家發展委員會個資法問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:18+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-12 11:12:04; HTTP Last-Modified Wed, 23 Sep 2026 09:32:18 GMT
sha256: 3e2c9dd22367868dae9c3df652b78f7de6dab013f3b4fe5106cc7b51b6aa588b
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題標題, 答覆內容
excluded_fields: 發布日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_43609

```
dataset_name: 公文及檔案管理資訊系統驗證常見問題
provider: 國家發展委員會檔案管理局
official_dataset_url: https://data.gov.tw/dataset/43609
download_url: https://www.archives.gov.tw/opendata/公文及檔案管理資訊系統驗證常見問題.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：國家發展委員會檔案管理局，公文及檔案管理資訊系統驗證常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:19+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-09-03 15:56:42
sha256: cfb8ddd3c05c8ed44bc5923f6772563ce4c8b907e4bbb49d661caa3e2e76fbdd
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 常見問題內容, 常見問題答覆
excluded_fields: 序號, 常見問題類別, 發布日期, 來源網址
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_173229

```
dataset_name: 電信事業申請核配衛星通信用無線電頻率Q&A
provider: 數位發展部
official_dataset_url: https://data.gov.tw/dataset/173229
download_url: https://www-api.moda.gov.tw/OpenData/Files/14724
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：數位發展部，電信事業申請核配衛星通信用無線電頻率Q&A，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:20+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-06-30 13:44:37
sha256: 6861fa325e43836b9554a283c2c28925456c2adca2abd9038990acc35191771d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回答
excluded_fields: 編號
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_22314

```
dataset_name: 專利商標電子服務問答集
provider: 經濟部智慧財產局
official_dataset_url: https://data.gov.tw/dataset/22314
download_url: https://www.tipo.gov.tw/public/Data/data_output_8.xml
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：經濟部智慧財產局，專利商標電子服務問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:21+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-26 17:53:56
sha256: cb136c97e69045dff8ec90b2736dd9ff336c513deaef2f26eee7d37ba8f728e8
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答案
excluded_fields: 序號, 大類, 更新日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_41245

```
dataset_name: 新竹科學園區管理局常見問答
provider: 國家科學及技術委員會新竹科學園區管理局
official_dataset_url: https://data.gov.tw/dataset/41245
download_url: https://w3.sipa.gov.tw/OPENDATA/download.jsp?FileName=faq.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：國家科學及技術委員會新竹科學園區管理局，新竹科學園區管理局常見問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:22+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-23 22:07:39
sha256: 11c10781f033a51e679bdbdf9640adbc52b1ce703aeae321c72d47895f45db05
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答覆
excluded_fields: 主分類, 業務名稱, 更新日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_133047

```
dataset_name: 臺北市稅捐稽徵處常見問答集
provider: 臺北市稅捐稽徵處
official_dataset_url: https://data.gov.tw/dataset/133047
download_url: https://data.taipei/api/dataset/2ab479d3-a115-431f-92de-a1a5c5dea5a0/resource/9cbd768f-d817-4828-80f3-8db11acf3f24/download
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：臺北市稅捐稽徵處，臺北市稅捐稽徵處常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:23+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-02-11 15:37:11
sha256: d23c746cc3174adc964e0831933b3536196ce157405fd5bef786fe4a3356c145
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答案
excluded_fields: 項次, 機關名稱, 題數
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_123084

```
dataset_name: 新北市政府稅捐稽徵處常見問答集
provider: 新北市政府財政局
official_dataset_url: https://data.gov.tw/dataset/123084
download_url: https://data.ntpc.gov.tw/api/datasets/a9881b54-bce3-4f04-941d-900a52d21a01/csv/file
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：新北市政府財政局，新北市政府稅捐稽徵處常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:24+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-07-02 10:52:33
sha256: e43c7562ee141392a26fcb6cf0de7a22f1af7dc1d457aa972ba03ffc33421a8e
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: question, answer
excluded_fields: a_seqno, class, localcallservice, c_seqno
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_25590

```
dataset_name: 國稅問與答-營利事業所得稅
provider: 財政部臺北國稅局
official_dataset_url: https://data.gov.tw/dataset/25590
download_url: https://www.ntbt.gov.tw/download/235f96db98e245eab6a7764bbffc4192
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：財政部臺北國稅局，國稅問與答-營利事業所得稅，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:25+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-17 11:17:21
sha256: bc09d517c0b0acb620ed03752d24929ecade3e3dd5c449a11050ff72d4940c2b
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答
excluded_fields: 項次, 類別, 更新日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_25520

```
dataset_name: 國稅問與答-營業稅
provider: 財政部南區國稅局
official_dataset_url: https://data.gov.tw/dataset/25520
download_url: https://www.ntbsa.gov.tw/download/2c4249fc427342a1885f707ace33c159
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：財政部南區國稅局，國稅問與答-營業稅，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:26+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-06-10 15:31:08
sha256: 7543696c9d616e5419fb4f8e339b2fa061bbb6181654c0bbfa3504cd4c7bb095
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答
excluded_fields: 序號, 更新日期, 類別
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_25479

```
dataset_name: 國稅問與答—贈與稅
provider: 財政部中區國稅局
official_dataset_url: https://data.gov.tw/dataset/25479
download_url: https://www.ntbca.gov.tw/download/151b323765d000006dfc52ff883dca8f_2
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：財政部中區國稅局，國稅問與答—贈與稅，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:27+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-01-22 09:51:31
sha256: b202a1637c3b0a088db3de7d714a6a9ba87fd1e16f5a00ddb9b1efe154ea4eb7
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答
excluded_fields: 類別, 更新年度, 提供機關
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_57713

```
dataset_name: 財政部南區國稅局檔案應用常見問答集
provider: 財政部南區國稅局
official_dataset_url: https://data.gov.tw/dataset/57713
download_url: https://www.ntbsa.gov.tw/download/a522743710e84dffa974b1894d084776
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：財政部南區國稅局，財政部南區國稅局檔案應用常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:28+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-06-09 15:19:30
sha256: 1a08082980a1cc63bfe8e5a9dfdfc41984eda627c006c14f3ada8dcca4236f90
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答案
excluded_fields: 更新日期, 問題類別, 本局負責單位
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_24107

```
dataset_name: 人民申請使用國有財產業務問答
provider: 財政部國有財產署
official_dataset_url: https://data.gov.tw/dataset/24107
download_url: https://esvc.fnp.gov.tw/opendata/openDataMain/file?sourceId=565
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: government_faq
attribution: 資料來源：財政部國有財產署，人民申請使用國有財產業務問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:29+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-09-19 10:24:10
sha256: 61169f6ce537512a5488a22807bd37bbe0ae556c80c1a2a00efba77948f133ac
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回答
excluded_fields: —
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_171525

```
dataset_name: 臺南市民服務平台常見問答
provider: 研究發展考核委員會
official_dataset_url: https://data.gov.tw/dataset/171525
download_url: https://soa.tainan.gov.tw/Api/Service/Get/ed61e35c-48eb-4b7a-a75e-8d2fc6557199
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：研究發展考核委員會，臺南市民服務平台常見問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:31+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-05-29 18:27:50
sha256: e059c85855f678058946a7437742995874e6049cf7de64e32310b527228c53d3
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答覆內容
excluded_fields: 機關名稱, 問題類型, 發布日期, 修改日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_177465

```
dataset_name: 苗栗縣便民快e通-常見問題
provider: 數位研考處
official_dataset_url: https://data.gov.tw/dataset/177465
download_url: https://webws.miaoli.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvb3BlbmRhdGEvMjExMS8zMzk2NjM3YS0wNjM2LTQxM2EtODc0NC0yMDgzNDBiNzZiMjIuY3N2&n=6IuX5qCX57ij5L6%2f5rCR5b%2brZemAmi3luLjopovllY%2fpoYwuY3N2&icon=.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：數位研考處，苗栗縣便民快e通-常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:32+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-04-21 15:44:28
sha256: f08f45dd2cae4f84f226701557191456417aa4646d21552a2e131f6756b93dbc
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題摘要, 答案
excluded_fields: —
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_175360

```
dataset_name: 臺鐵公司網站常見問答集
provider: 國營臺灣鐵路股份有限公司
official_dataset_url: https://data.gov.tw/dataset/175360
download_url: https://ods.railway.gov.tw/tra-ods-web/ods/download/dataResource/8ae4cac39a2f41f7019a33f314150567
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：國營臺灣鐵路股份有限公司，臺鐵公司網站常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:33+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-10-30 15:22:07
sha256: 31c41ab21829bbcae6afd724593299354980551b8c8270bba3f37e64420d596f
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答
excluded_fields: 類別
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_175519

```
dataset_name: 國立科學工藝博物館FAQS答客問
provider: 國立科學工藝博物館
official_dataset_url: https://data.gov.tw/dataset/175519
download_url: https://websrv.nstm.gov.tw/otherinfo/opendata/FAQSOpenData.ashx
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：國立科學工藝博物館，國立科學工藝博物館FAQS答客問，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:34+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-12-24 11:59:16
sha256: a6446cbaefb24e6c513e7c931b812c053fe605490fea6762817544f7567fe626
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答案說明
excluded_fields: 分類名稱, 發佈日期, 點閱率
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_123080

```
dataset_name: 捷運工程常見問題
provider: 新北市政府捷運工程局
official_dataset_url: https://data.gov.tw/dataset/123080
download_url: https://data.ntpc.gov.tw/api/datasets/f21b1156-bd0f-4fb9-929b-c5fb5fd12c7d/csv/file
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：新北市政府捷運工程局，捷運工程常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:36+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-28 10:02:03
sha256: 5dbae20241b5aa73c3d7cf087248cb2fb2a102c4ff4b733a076bfe748d4a20bb
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: question, answer
excluded_fields: number, date
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_110972

```
dataset_name: 台灣糖業公司常見問答資料
provider: 台灣糖業股份有限公司
official_dataset_url: https://data.gov.tw/dataset/110972
download_url: https://www.taisugar.com.tw/DownLoadDataRow.ashx?DataRow=12
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：台灣糖業股份有限公司，台灣糖業公司常見問答資料，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:37+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2024-08-13 16:55:06
sha256: 7e61d47227af0bc04723cf892203c829829f243628730ac9d6a355e0c52813ca
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 問題內容, 答案內容
excluded_fields: sn, 主類別, 次類別
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_41446

```
dataset_name: 臺東區農業改良場常見問答集
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/41446
download_url: https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=B86&FOTT=CSV&IsTransData=1
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：農業部，臺東區農業改良場常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:38+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2024-05-06 16:07:43
sha256: 07e8af0c3ce7cf1ff2989f3a1fe9ed95bfa1990486bc74d052d9554a96bd3789
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答
excluded_fields: 類別
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_9536

```
dataset_name: 高雄區農業改良場轄區常見農業相關問題(問答Q&A)
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/9536
download_url: https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=115&FOTT=CSV&IsTransData=1
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：農業部，高雄區農業改良場轄區常見農業相關問題(問答Q&A)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:38+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-17 16:23:33
sha256: 44e586bc673ac7976dbbd656fa8430b58b7e50ce7f2753f7928e5997b21ef05d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答
excluded_fields: 單位
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_7301

```
dataset_name: 病蟲害診斷服務問答集
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/7301
download_url: https://data.moa.gov.tw/Service/OpenData/FromM/blightdialoguedata.aspx?UnitId=022&FOTT=CSV&IsTransData=1
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：農業部，病蟲害診斷服務問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:39+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2024-08-27 14:58:52
sha256: 53ca1e0d4017273e22fcd6c1a2d852ba51e6a6bde14e017ab2d282a087c7934d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 解答, 防治方法
excluded_fields: 植物分類, 品名
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_9807

```
dataset_name: 畜產農民常見問題集
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/9807
download_url: https://data.moa.gov.tw/Service/OpenData/DataFileService.aspx?UnitId=161&FOTT=CSV&IsTransData=1
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：農業部，畜產農民常見問題集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:40+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2024-12-23 16:50:56
sha256: f86deedca7a65bd32b40de5b61fbd4f5e1759fb0f16990af76c6326cae6be1b1
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 內容
excluded_fields: 問題分類
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_24392

```
dataset_name: 農藥所民意信箱問答集
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/24392
download_url: https://data.moa.gov.tw/Service/OpenData/TactriMbox.aspx?FOTT=CSV&IsTransData=1&UnitId=352
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：農業部，農藥所民意信箱問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:44+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-03-09 10:00:22
sha256: 1b8537b726c2e7a1939b654ddd25d7e21adb975773fea2ae0865ca22b7541ddb
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 回答
excluded_fields: 類別, 日期, 文件
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_114846

```
dataset_name: 水產試驗所漁業問答
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/114846
download_url: https://data.moa.gov.tw/Service/OpenData/TfrinRss/TfrinRss02.aspx?FOTT=CSV&IsTransData=1&UnitId=B71
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：農業部，水產試驗所漁業問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:45+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2023-08-14 16:35:14
sha256: 8dc37b1d433a90e5b5df413ee515868b1430cd87ffb812d31fc4a97f5c9bdaa4
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: title, description
excluded_fields: link, pubdate
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_14519

```
dataset_name: 常見問題Q&A(財團法人汽車交通事故特別補償基金)
provider: 金融監督管理委員會保險局
official_dataset_url: https://data.gov.tw/dataset/14519
download_url: https://www.mvacf.org.tw/UpFile/OtherFiles/mvacf_opendata20.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：金融監督管理委員會保險局，常見問題Q&A(財團法人汽車交通事故特別補償基金)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:47+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-06-09 15:29:28; HTTP Last-Modified Fri, 13 Feb 2026 05:43:27 GMT
sha256: f3f8d724ec7d0895e4a5f2da941587e7ac608a4c4a1485771f9bc75126f13b75
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 留言, 基金回覆
excluded_fields: 序號, 日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_11442

```
dataset_name: 常見問題Q&A (財團法人住宅地震保險基金)
provider: 金融監督管理委員會保險局
official_dataset_url: https://data.gov.tw/dataset/11442
download_url: https://www.treif.org.tw/contents/H_service/H1OpenDataAll.ashx
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：金融監督管理委員會保險局，常見問題Q&A (財團法人住宅地震保險基金)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:48+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-06-09 15:28:29
sha256: f35e230d7b833643cd8c150d756036f291047447de3683321f6895a69816e632
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 問題, 答案
excluded_fields: 問題類別, 更新日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_38262

```
dataset_name: 165反詐騙諮詢專線－詐騙闢謠專區
provider: 警政署
official_dataset_url: https://data.gov.tw/dataset/38262
download_url: https://opdadm.moi.gov.tw/api/v1/no-auth/resource/api/dataset/4F4DF9A5-DF4C-4EE8-A50D-869347D38D9E/resource/443DBD23-3957-4FC9-9F3D-E8F3479021CB/download
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：警政署，165反詐騙諮詢專線－詐騙闢謠專區，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:49+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-09-23 15:05:13
sha256: 03d1cc63b1704fad9535493f2340f249e96851e42e14db49812112c9aab5e8d2
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 發佈內容
excluded_fields: 編號, 發佈時間
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_176413

```
dataset_name: 臺北市消費資（警）訊
provider: 臺北市政府法務局
official_dataset_url: https://data.gov.tw/dataset/176413
download_url: https://data.taipei/api/dataset/25e50f73-e043-44ee-ae5c-7dc723147192/resource/a5c719aa-78f7-4a47-a733-06b02dcf0f62/download
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：臺北市政府法務局，臺北市消費資（警）訊，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:50+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-08-27 14:49:11
sha256: 70adc8b291c05e61ba82798cdc4cb36d8bfd46749d45956e0d1a12e1c9bbe113
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 消費資（警）訊內容
excluded_fields: 日期, 企業經營者名稱, 統一編號, 連結
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_11519

```
dataset_name: 教育宣導資訊(財團法人汽車交通事故特別補償基金)
provider: 金融監督管理委員會保險局
official_dataset_url: https://data.gov.tw/dataset/11519
download_url: https://www.mvacf.org.tw/UpFile/OtherFiles/mvacf_opendata01new.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: public_service
attribution: 資料來源：金融監督管理委員會保險局，教育宣導資訊(財團法人汽車交通事故特別補償基金)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:52+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-06-19 15:37:40; HTTP Last-Modified Wed, 17 Jun 2026 03:25:24 GMT
sha256: 41acf36f2868cb56657aa67b51eec492fd80d2d908e61eb75c0d6c3344e0dcc8
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 大綱, 內容
excluded_fields: 日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_55229

```
dataset_name: 陸委會新聞稿
provider: 大陸委員會
official_dataset_url: https://data.gov.tw/dataset/55229
download_url: https://www.mac.gov.tw/big5/data/55229_大陸委員會新聞稿.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：大陸委員會，陸委會新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:54+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-08-22 13:39:33; HTTP Last-Modified Wed, 28 May 2025 01:51:36 GMT
sha256: ddfc40632123dc1dd25ce690fd6893b0def76e74d47c71c9f98da959626d5d0a
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 內文
excluded_fields: 發布日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_25848

```
dataset_name: 漁業署新聞稿
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/25848
download_url: https://data.moa.gov.tw/Service/OpenData/FromM/FishNewsData.aspx?FOTT=CSV&IsTransData=1&UnitId=043
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：農業部，漁業署新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:55+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-03-17 04:15:00
sha256: bb13278f39256f1b11a057d94d4566cee9ac28f690c735a1a007bce72bdc9b78
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 內文
excluded_fields: 張貼日
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_7505

```
dataset_name: 各警察機關新聞發布
provider: 警政署
official_dataset_url: https://data.gov.tw/dataset/7505
download_url: https://opdadm.moi.gov.tw/api/v1/no-auth/resource/api/dataset/00F7F1C4-2AC0-461C-B060-A6FCD3FF6E45/resource/15425644-4FAE-4735-B2D4-666E4119D187/download
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：警政署，各警察機關新聞發布，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:56+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-09-23 15:01:03
sha256: 92ef378cb6dd80547b90207b9f26ca59cbc5e31a1160734ea98ab997f8d350a2
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: stitle, content
excluded_fields: serialNo, deptName, postDate
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_94024

```
dataset_name: 中央研究院院新聞稿
provider: 資訊服務處
official_dataset_url: https://data.gov.tw/dataset/94024
download_url: https://file.apps.sinica.edu.tw/filepool/opendata/news.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：資訊服務處，中央研究院院新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:58+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2023-10-27 14:01:46; HTTP Last-Modified Wed, 23 Sep 2026 05:00:08 GMT
sha256: 39add267ca9774c57f5f66e34bb97305cdc39ea5be200d4a97456be7db313b9d
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 網頁內容
excluded_fields: 來源網址, 發布單位, 發布日期, 相關圖片
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_6421

```
dataset_name: 行政院消費者保護會-消費者保護新聞稿
provider: 行政院
official_dataset_url: https://data.gov.tw/dataset/6421
download_url: https://www.ey.gov.tw/NewOpenData/CSV/185
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：行政院，行政院消費者保護會-消費者保護新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:59+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-06-24 16:31:01; HTTP Last-Modified Wed, 23 Sep 2026 09:32:58 GMT
sha256: f00faf420fab0f786bc6d0586cc676897c1d8527f8557b7ac84b38d085c50141
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 標題, 內容
excluded_fields: 來源網址, 上版日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_128337

```
dataset_name: 臺北市市政網站整合平台之新聞稿
provider: 臺北市政府資訊局
official_dataset_url: https://data.gov.tw/dataset/128337
download_url: https://www.gov.taipei/OpenData.aspx?SN=ABBF62618F53F8DE
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：臺北市政府資訊局，臺北市市政網站整合平台之新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:32:59+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-07-14 13:47:07
sha256: 72276b808a4e4448fe0356c4f657d0ea58ac8f57dc676092f9de92f0e639020a
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: title, 內容
excluded_fields: DataSN, ArticleType, FileName, Link, Source, 聯絡人, 聯絡資訊, 日期時間, 分類, 相關檔案, url, 相關連結, url, 相關圖片, url, 相關影音, 發布單位
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_174199

```
dataset_name: 貿易署新聞發布
provider: 經濟部國際貿易署
official_dataset_url: https://data.gov.tw/dataset/174199
download_url: https://www.trade.gov.tw/OpenData/getOpenData.aspx?oid=1E57D83236381A52
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：經濟部國際貿易署，貿易署新聞發布，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:33:08+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-11-20 13:01:34
sha256: 9e3823149b594b63d86796715a9f7b04cba3de858a6ad191bd879b73c2483973
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: PageTitle, PageContent
excluded_fields: Id, PagePublishTime, department
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_22927

```
dataset_name: 國家發展委員會新聞稿
provider: 國家發展委員會
official_dataset_url: https://data.gov.tw/dataset/22927
download_url: https://www.ndc.gov.tw/OpenData.aspx?SN=99606AC2FCD53A3A
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：國家發展委員會，國家發展委員會新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:33:11+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-02-11 15:25:59; HTTP Last-Modified Wed, 23 Sep 2026 09:33:11 GMT
sha256: b3c532d6421913917b20b4daf309c7ecc540d71473a3d1e316491cd13aa328e5
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 主題, 內容
excluded_fields: ArticleType, FileName, Link, 網址, 上版日期, 序號
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_166117

```
dataset_name: 國家文官學院新聞稿
provider: 國家文官學院
official_dataset_url: https://data.gov.tw/dataset/166117
download_url: https://www.nacs.gov.tw/OpenData.aspx?SN=38F3F9325113076C
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：國家文官學院，國家文官學院新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:33:12+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-11-13 14:39:27
sha256: f91fb981a1e78c6e4ddd577d1412db749a68f3bc724e91d3ec16ed59d258101c
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: title, 內容
excluded_fields: 機關代碼, 發稿日期, 編號, 發稿單位, 聯絡人, 聯絡資訊
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_175903

```
dataset_name: 台灣中油公司新聞稿
provider: 台灣中油股份有限公司
official_dataset_url: https://data.gov.tw/dataset/175903
download_url: https://www3.cpc.com.tw/opendata_a06/台灣中油公司新聞稿.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：台灣中油股份有限公司，台灣中油公司新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:33:13+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-12-04 15:02:49; HTTP Last-Modified Thu, 10 Sep 2026 09:50:23 GMT
sha256: 9f7298eae613b0b1162e23bcde3ab9aa050aae61cba00b06183c050814a1de30
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 新聞稿標題, 新聞稿內文
excluded_fields: 項目, 單位, 年月日
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_32021

```
dataset_name: 臺灣金融控股股份有限公司網站新聞稿
provider: 臺灣金融控股股份有限公司
official_dataset_url: https://data.gov.tw/dataset/32021
download_url: https://www.twfhc.com.tw/Content/fileredirect?Path=/opendata/12_%E7%B6%B2%E7%AB%99%E6%96%B0%E8%81%9E%E7%A8%BF/1_12_%E8%87%BA%E7%81%A3%E9%87%91%E8%9E%8D%E6%8E%A7%E8%82%A1%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8%E7%B6%B2%E7%AB%99%E6%96%B0%E8%81%9E%E7%A8%BF_111Q2.csv
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：臺灣金融控股股份有限公司，臺灣金融控股股份有限公司網站新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:33:14+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2026-05-19 14:22:26
sha256: 27eb07699c86646ff3280b143b8ace5504c42bf1d468d3894ee0ccc28b769579
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: 新聞稿標題, 新聞稿內容
excluded_fields: 發布單位, 發布日期
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

### dgt_68551

```
dataset_name: 水產試驗所新聞稿
provider: 農業部
official_dataset_url: https://data.gov.tw/dataset/68551
download_url: https://data.moa.gov.tw/Service/OpenData/Tfrin.aspx?key=1198&FOTT=CSV&IsTransData=1&UnitId=E43
license: 政府資料開放授權條款-第1版 (Open Government Data License, version 1.0)
license_url: https://data.gov.tw/license
commercial_use: allowed
modification: allowed
redistribution: allowed_with_attribution
ai_training: allowed_under_general_grant
ai_training_explicit: false
ai_training_basis: general unrestricted-purpose license grant
domain: press_release
attribution: 資料來源：農業部，水產試驗所新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license
downloaded_at: 2026-09-23T09:33:15+00:00
upstream_version_or_updated_at: data.gov.tw metadata modified 2025-02-19 11:01:58
sha256: 8c44cbccf1b958cf394f9fec8076200945fcbd3602ef16d9eb7913929b1e116e
allowed_uses: corpus, language_model_statistics, benchmark, ranking_training_data
text_fields: title, description
excluded_fields: link, pubDate
status: approved
production_ready: yes
notes: 只使用下載檔中 text_fields 列出的欄位；網址、附件、圖片欄位指向的外部內容不抓取。
```

## 拒絕或排除的來源

| id | 原因 |
|---|---|
| ptt | 規格明列禁止；使用者發文著作權屬各作者，無可商用改作授權 |
| dcard | 規格明列禁止；平台條款不授權重製與訓練 |
| threads | 規格明列禁止；無資料集授權 |
| facebook | 規格明列禁止；無資料集授權 |
| news_websites | 規格明列禁止；新聞著作權屬各媒體 |
| blogs | 規格明列禁止；著作權屬各作者 |
| wikipedia | 規格明列禁止（CC BY-SA 的相同方式分享條件與本專案 Apache-2.0 資料使用方式需另行確認） |
| github_unknown_wordlists | 規格明列禁止；來源與授權不明 |
| mcbopomofo_chewing_rime_dictionaries | 規格明列禁止；其他輸入法詞庫 |
| moe_dictionaries | 規格明列禁止：教育部辭典內容，未另行逐項確認授權 |
| naer_general_corpus | 規格明列禁止：國教院一般語料庫，未另行逐項確認授權 |
| external_pages_linked_from_datasets | 資料集欄位中的外部網址（法規網址、新聞稿 Source/Link 等）不屬於下載內容，不自動視為同一授權 |
| dgt_10547 | data.gov.tw dataset 10547：標示為 CSV 但內容是破損的 JSON 片段，無法可靠解析，暫不使用 |
| dgt_9641 | data.gov.tw dataset 9641：下載檔實際為 ZIP（標示為 CSV），內容未檢查，暫不使用 |
| dgt_7404 | data.gov.tw dataset 7404：下載網址回應 HTTP 403，未取得檔案 |

## builtin lexicon（`data/builtin/lexicon.tsv`）與字形表（`data/builtin/variants.tsv`）

```
Source: 本專案人工建立與維護
Provider: 造序科技 ZaoSeq Technologies（籌備中）
License: Apache-2.0（與本專案程式碼相同）
Commercial use / Modification / Redistribution / Model training: 允許
Attribution requirement: 依 Apache-2.0 與 NOTICE
```

- 詞條與常用度等級（1–5）是人工判斷，不是語料統計；現在降級為 demo heuristic，語料模型不使用它（lexical_weight 預設 0）。
- 每個讀音都由 builder 檢查必須存在於 CNS11643 該字的讀音中；多音字必須明確寫出讀音。
- 部分詞（例如「一次、家裡、承諾、情況、臺北、睡覺」）是為了讓 DEV / sanity benchmark 的完整句子存在於候選中而補入，
  因此這些 benchmark 不能用來評估詞庫 coverage。

## Benchmark 情境（`benchmarks/`）

本專案人工撰寫的句子、讀音與 acceptable 答案，Apache-2.0。Web Demo 的使用者輸入不儲存、不加入 corpus、benchmark 或訓練資料。
