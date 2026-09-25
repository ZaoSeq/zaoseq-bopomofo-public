# Daily Corpus V1 + Frequency-aware Lexicon（v0.2 development）

所有選擇只看 DEV：Coverage-DEV v1.1（300 句）與 GOV-DEV（400 句）。v0.1 TEST 只用於語料排除，沒有用於任何選擇。
frozen V0、fine-tuned Laya、V0.json、FINAL.json 與 production path 都沒有修改；本輪沒有建立 sealed TEST。
完整數據：[daily_v1.md](../benchmarks/results/daily_v1.md)、[daily_v1.json](../benchmarks/results/daily_v1.json)、
[daily_v1_ablation.json](../benchmarks/results/daily_v1_ablation.json)；來源清單：[data/daily/SOURCES.json](../data/daily/SOURCES.json)。

## Coverage-DEV v1.1

v1.0（[benchmarks/coverage_v1/](../benchmarks/coverage_v1/)）不變。v1.1（[benchmarks/coverage_v1_1/](../benchmarks/coverage_v1_1/)）只把 cv19 的「念」加為可接受答案，
manifest 記錄上層版本的 source 雜湊、修改理由與變動項目。V0 在 v1.0 / v1.1 的差異只有這一句：R@1 0.470 → 0.473，R@5 0.780 → 0.783，
top-4 window 0.743 → 0.747（[coverage_v1_1_delta.json](../benchmarks/results/coverage_v1_1_delta.json)）。

## 來源規則

- 只有官方版本且授權明確的資料可以 APPROVED；出處或條款不清楚的一律 HOLD。
- `approval_scope`：`production` 可以進入 production freeze；`dev_experiment` 只能做 DEV 實驗，freeze 前須重新審查資料權利。
- importer 先過 LicenseGate（任何權利欄位不確定就拒絕、production 用途只接受 production scope），再比對原始檔 SHA-256。
- training use 與 redistribution 分開記錄。原始檔只在 `data/raw/daily/`（不進 git），repo 只有 manifest、雜湊、統計與顯名清單。
- 簡體或混用字形的句子直接排除，不做簡轉繁。

| source | status | scope | 判斷 |
|---|---|---|---|
| Tatoeba cmn（繁體原句，2026-09-19 官方 weekly export） | APPROVED | production | CC BY 2.0 FR；作者清單在 [data/daily/attribution/tatoeba_cmn_hant.tsv](../data/daily/attribution/tatoeba_cmn_hant.tsv)，衍生 artifact 須一併附上 |
| OASST1 zh prompter（HF revision fdf72ae） | APPROVED | dev_experiment | Apache-2.0；只用未刪除、非 synthetic、通過審核的 prompter 訊息；freeze 前須重審 |
| Unihan Variants（Unicode 18.0） | APPROVED | production | 只用來標記簡體字，不做轉換 |
| Common Voice 官方 dataset（Mozilla Data Collective） | HOLD | – | 只能透過 MDC 取得，需要帳號並同意 MDC 條款；須由專案負責人取得並記錄確切版本後再審 |
| Common Voice repo 的 Sentence Collector export | HOLD | – | 不是官方 dataset 版本（web app repo 中 2022-07 的最後一次 export） |
| Common Voice repo 的 setences / chatlogs / lms / taipei_city_gov | HOLD | – | 來源混合或捐贈條款不在 repo 中 |
| OASST1 zh assistant | HOLD | – | 回答中可見複製的第三方文字（例如維基百科），可能含聊天機器人輸出 |
| TWLLM-Data | HOLD | – | 使用者同意與個資、商業模型輸出的條款限制、上傳者重新授權缺乏權利鏈 |
| Taiwan-Tongues-ASR-CE | HOLD | – | 資料頁未標明授權 |
| PTT、Dcard、Threads、Facebook、新聞全文、部落格、維基衍生、網路爬取、字幕、教育部辭典、其他輸入法詞庫、授權不明詞表 | REJECTED | – | 專案政策排除 |

## Corpus V1

| source | kept sentences | Han chars | train / dev / test | 簡體排除 | 評估集排除 |
|---|---|---|---|---|---|
| tatoeba_cmn_hant | 38,808 | 411k | 34,950 / 1,912 / 1,946 | 183 句（0.5%） | 31 句 |
| oasst1_zh_prompter | 182 | 2.8k | 162 / 13 / 7 | 1,356 句（88%） | 0 |

- 文件層級切分（Tatoeba 以句子 id、OASST1 以 conversation tree）；dev / test 與 train 近重複的句子再排除（87 句）。
- 評估集排除：與 Coverage-DEV v1.0 / v1.1、人工 DEV / sanity、GOV-DEV 所在的語料 split、v0.1 TEST（EVERYDAY、GOV、TYPO 與 TEST-GOV 語料 split）
  做 char 4-gram MinHash（Jaccard ≥ 0.6）與 8 字連續共用檢查。
- 其他品質統計：NFC 變動 0；Tatoeba 非臺灣標準字（主要是「裏」「爲」）479 句、零寬空白等 18 句排除；
  髒話只統計不刪除；Tatoeba 前 10 名作者佔 91% 的句子（來源集中度高）。
- daily 日常 LM 只用 production scope 的來源（目前只有 Tatoeba，train 45 萬字，約為政府語料的 5%）。

## 結果（DEV）

| config | everyday top1 | everyday R@5 | top-4 window | teacher everyday | GOV top1 | teacher GOV | lexicon entries | decoder p50 / p95 ms |
|---|---|---|---|---|---|---|---|---|
| A V0（gov only） | 0.473 | 0.783 | 0.747 | 0.697 | 0.802 | 0.860 | 16,759 | 71 / 186 |
| B daily only | 0.550 | 0.743 | 0.727 | – | 0.312 | – | 16,759 | 48 / 147 |
| C gov 0.75 / daily 0.25（= D = F） | 0.617 | 0.860 | 0.843 | 0.780 | 0.745 | 0.848 | 16,759 | 100 / 255 |
| E pmi（DEV 規則選出） | 0.643 | 0.863 | 0.847 | 0.780 | 0.785 | 0.860 | 58,111 | 85 / 253 |
| E doc_freq | 0.660 | 0.857 | 0.847 | – | 0.815 | – | 132,826 | 85 / 242 |
| G gov + OASST1（DEV only） | 0.497 | 0.750 | 0.723 | – | 0.770 | – | 16,759 | 70 / 198 |
| H gov + Tatoeba + OASST1（DEV only） | 0.613 | 0.860 | 0.843 | – | 0.743 | – | 16,759 | 87 / 222 |

選擇規則（事前固定）：GOV-DEV R@1 不低於 A − 0.02 的設定中取 Coverage-DEV v1.1 R@5 最高者。
三個 C 權重都沒有通過 GOV 條件（0.745 / 0.715 / 0.667），依規則選 GOV 下降最少的 0.25；E 的五個變體中四個通過，選出 pmi。

- **日常語料有效**：C 的 everyday Top-1 +14.4 個百分點、R@5 +7.7，日常 DEV 交叉熵 8.95 → 6.93 bits/char；但只加 LM 時 GOV Top-1 −5.7。
- **衍生詞表把 GOV 拉回來**：E 在 C 之上 GOV +4.0（pmi）/ +7.0（doc_freq），everyday Top-1 再 +2.6 / +4.3。
- **頻率權重本身沒有額外效果**：同一份 pmi 詞表全部改成固定權重 10，結果幾乎相同（everyday 0.650 / 0.863，GOV 0.785）。收益來自詞條，不是頻率權重。
- **選擇規則的問題**：pmi 與 doc_freq 的 R@5 只差 2 句，doc_freq 在 everyday Top-1、GOV Top-1、MRR 都較好；freeze 前需要重新定義選擇指標。
- **frozen teacher**：E 的 everyday teacher Top-1 0.697 → 0.780（37 句改對 / 12 句改錯，McNemar p = 0.0005）；GOV 持平（16 / 16）。
- **OASST1** 只有 162 句，單獨加入時 everyday 反而下降，與 Tatoeba 混合時沒有差異。

### 衍生詞表

| variant | eligible words | daily-only | gov-only |
|---|---|---|---|
| raw_freq（pooled, docs ≥ 2） | 71,330 | 387 | 57,271 |
| doc_freq（pooled, docs ≥ 5） | 69,644 | 387 | 55,593 |
| pmi（pooled, docs ≥ 5, PMI ≥ 5） | 23,901 | 231 | 19,280 |
| daily_weighted（daily 0.75, docs ≥ 5, PMI ≥ 5） | 12,648 | 1,268 | 5,121 |
| interpolated（daily 0.25, docs ≥ 5, PMI ≥ 5） | 24,255 | 1,767 | 16,372 |

- 每個詞記錄 corpus / document / daily / government count、領域分佈、PMI、估計頻率、權重、source_ids、provenance 與 eligibility。
- 抽出的詞以政府語料為主，含法規模板片段（「條第」「項規定」「第一項」）；改錯的日常句多半是這類詞搶走位置（施工 → 施公頃、三月 → 參閱、線上 → 呈現）。
- 讀音無法唯一標注的詞列出全部 CNS 組合，產生錯誤的同音競爭（例如「注射」得到 ㄓㄨˋ ㄧˋ 而與「注意」競爭）。
- 同音競爭分析：有既有同長度競爭詞的衍生讀音 7 個，其中 2 個權重高於競爭詞；E 相對 C 在 Coverage-DEV 改對 13 / 改錯 5、GOV-DEV 改對 22 / 改錯 6，全部涉及衍生詞。

### Teacher window（只診斷，production 仍是 K=4）

K=5/6/8 讓 gold 進入視窗的比例上升（E everyday 0.847 → 0.863 / 0.867 / 0.880），但 teacher Top-1 幾乎不變（0.780 → 0.783 / 0.773 / 0.790），
改對與改錯的句數接近（K=8：12 / 9），模型延遲與 GPU 記憶體沒有明顯差異。列為 teacher-v2 的候選題目，不採用。

### 延遲與記憶體

- 日常 LM artifact 0.84 MB（政府 9.27 MB），載入 0.2 s、RSS +10 MB；LM extend 每次約 +1–2.5 µs（14.4 → 15.2–16.9 µs）。
- decoder 延遲（Coverage-DEV）：A 71 / 186 ms → E pmi 85 / 253 ms（p50 +20%、p95 +36%）。
- 衍生詞表（pmi，58k entries）載入 3.2 s、RSS +347 MB（新 process：V0 336 MB → 693 MB），是目前最大的成本。
- 詞表統計（兩次掃描，政府 + 日常 train split）離線約 73 s、0.6 GB。

## 重現

```bash
python -m zaoseq_bopomofo.coverage.dataset build --version 1.1
python -m zaoseq_bopomofo.daily audit
python -m zaoseq_bopomofo.daily build
python -m zaoseq_bopomofo.daily experiments
python -m zaoseq_bopomofo.daily ablation
python -m zaoseq_bopomofo.daily report
```

`build` 需要 `data/raw/daily/` 中與 SOURCES.json 雜湊相同的官方原始檔（URL 與版本都記錄在 manifest）。
