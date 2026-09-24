# Third-Party Notices

造序注音 ZaoSeq Bopomofo 的程式碼以 Apache License 2.0 發布（見 LICENSE 與 NOTICE）；data/ 內的資料依各自來源授權，不適用 Apache-2.0。以下第三方元件依各自授權使用；
本 repository 不包含、也不重新散布任何第三方原始碼或模型權重，除了下方註明的 CNS11643 衍生資料。

目前的程式碼與資料不包含、也不依賴 McBopomofo、McBopomofoWeb、新酷音（Chewing）、Rime
或任何其他輸入法的程式碼與詞庫。

Clean-room 紀錄：2026-09-22 同一個開發工作階段稍早，曾有一個以 McBopomofoWeb（MIT）作為候選來源的原型，
過程中 clone 並閱讀過 McBopomofoWeb 的原始碼（ReadingGrid、鍵盤排列、語言模型）。
該原型在規格改為 clean-room 後已整批刪除，未進入任何 commit；現行 parser、decoder、詞庫與排序皆依公開的注音規則重新撰寫，
沒有複製或逐項翻寫該專案的程式碼、資料或模組結構。

## CNS11643 中文標準交換碼全字庫

- Provider：數位發展部（Ministry of Digital Affairs, Taiwan），經由政府資料開放平臺提供
- Source：https://data.gov.tw/dataset/5961 ，https://www.cns11643.gov.tw/opendata/
- License：政府資料開放授權條款－第 1 版（Open Government Data License, version 1.0）
- Usage：Traditional Chinese character and Bopomofo reading data。
  使用 `Properties.zip` 內的 `CNS_phonetic.txt` 與 `MapingTables.zip` 內的 CNS→Unicode 對照表（BMP、第 2、3 字面），
  轉換為 `data/cns11643/cns_char_readings.tsv`（衍生資料，檔頭保留出處）。未使用字型檔與聲音檔。
- Attribution：本專案字音資料衍生自 CNS11643 中文標準交換碼全字庫，依政府資料開放授權條款第 1 版使用。


## 政府開放資料語料（data/corpus/）

以下資料集依政府資料開放授權條款－第 1 版（https://data.gov.tw/license）使用，衍生資料位於 `data/corpus/<source_id>/`，
不適用本專案程式碼的 Apache-2.0。完整 provenance（領域、下載網址、SHA-256、匯入與排除欄位）見 data/SOURCES.md 與 data/sources.json。

- [legal] 資料來源：法務部資訊處，中文法規_法律資料檔下載，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/18289）
- [government_faq] 資料來源：數位發展部，GSN政府網際服務網_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/171425）
- [government_faq] 資料來源：數位發展部，iTaiwan公共區域免費無線上網_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/171426）
- [government_faq] 資料來源：國家發展委員會檔案管理局，電子文書檔案服務中心-常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/103298）
- [government_faq] 資料來源：經濟部智慧財產局，營業秘密問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/22320）
- [press_release] 資料來源：外交部，外交部全球資訊網-中文版-新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/30143）
- [terminology] 資料來源：國家教育研究院，國家教育研究院-行政學學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/15262）
- [terminology] 資料來源：國家教育研究院，國家教育研究院-資訊名詞-高中含以下資訊學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/15407）
- [terminology] 資料來源：國家教育研究院，國家教育研究院-管理學學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/15440）
- [terminology] 資料來源：國家教育研究院，國家教育研究院-數學學術名詞，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/15443）
- [government_faq] 資料來源：數位發展部，政府資料開放平臺常見問答(FAQ)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/175294）
- [government_faq] 資料來源：數位發展部，MyData平臺常見問答(FAQ)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/175306）
- [government_faq] 資料來源：數位發展部，政府資料標準平臺常見問答(FAQ)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/175295）
- [government_faq] 資料來源：數位發展部，政府短網址服務_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/171427）
- [government_faq] 資料來源：數位發展部，政府專屬短碼簡訊平台_問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/171432）
- [government_faq] 資料來源：資訊服務司，1996內政服務熱線常見問題(QA)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/11838）
- [government_faq] 資料來源：經濟部中小及新創企業署，新創圓夢網-創業常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/45362）
- [government_faq] 資料來源：經濟部標準檢驗局，標檢局消費者Q&A，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/45909）
- [government_faq] 資料來源：金融監督管理委員會，金管會民意信箱FAQ，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/11024）
- [government_faq] 資料來源：中央存款保險股份有限公司，存款保險問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/11185）
- [government_faq] 資料來源：國家發展委員會，國家發展委員會個資法問與答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/145013）
- [government_faq] 資料來源：國家發展委員會檔案管理局，公文及檔案管理資訊系統驗證常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/43609）
- [government_faq] 資料來源：數位發展部，電信事業申請核配衛星通信用無線電頻率Q&A，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/173229）
- [government_faq] 資料來源：經濟部智慧財產局，專利商標電子服務問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/22314）
- [government_faq] 資料來源：國家科學及技術委員會新竹科學園區管理局，新竹科學園區管理局常見問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/41245）
- [government_faq] 資料來源：臺北市稅捐稽徵處，臺北市稅捐稽徵處常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/133047）
- [government_faq] 資料來源：新北市政府財政局，新北市政府稅捐稽徵處常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/123084）
- [government_faq] 資料來源：財政部臺北國稅局，國稅問與答-營利事業所得稅，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/25590）
- [government_faq] 資料來源：財政部南區國稅局，國稅問與答-營業稅，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/25520）
- [government_faq] 資料來源：財政部中區國稅局，國稅問與答—贈與稅，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/25479）
- [government_faq] 資料來源：財政部南區國稅局，財政部南區國稅局檔案應用常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/57713）
- [government_faq] 資料來源：財政部國有財產署，人民申請使用國有財產業務問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/24107）
- [public_service] 資料來源：研究發展考核委員會，臺南市民服務平台常見問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/171525）
- [public_service] 資料來源：數位研考處，苗栗縣便民快e通-常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/177465）
- [public_service] 資料來源：國營臺灣鐵路股份有限公司，臺鐵公司網站常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/175360）
- [public_service] 資料來源：國立科學工藝博物館，國立科學工藝博物館FAQS答客問，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/175519）
- [public_service] 資料來源：新北市政府捷運工程局，捷運工程常見問題，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/123080）
- [public_service] 資料來源：台灣糖業股份有限公司，台灣糖業公司常見問答資料，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/110972）
- [public_service] 資料來源：農業部，臺東區農業改良場常見問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/41446）
- [public_service] 資料來源：農業部，高雄區農業改良場轄區常見農業相關問題(問答Q&A)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/9536）
- [public_service] 資料來源：農業部，病蟲害診斷服務問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/7301）
- [public_service] 資料來源：農業部，畜產農民常見問題集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/9807）
- [public_service] 資料來源：農業部，農藥所民意信箱問答集，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/24392）
- [public_service] 資料來源：農業部，水產試驗所漁業問答，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/114846）
- [public_service] 資料來源：金融監督管理委員會保險局，常見問題Q&A(財團法人汽車交通事故特別補償基金)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/14519）
- [public_service] 資料來源：金融監督管理委員會保險局，常見問題Q&A (財團法人住宅地震保險基金)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/11442）
- [public_service] 資料來源：警政署，165反詐騙諮詢專線－詐騙闢謠專區，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/38262）
- [public_service] 資料來源：臺北市政府法務局，臺北市消費資（警）訊，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/176413）
- [public_service] 資料來源：金融監督管理委員會保險局，教育宣導資訊(財團法人汽車交通事故特別補償基金)，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/11519）
- [press_release] 資料來源：大陸委員會，陸委會新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/55229）
- [press_release] 資料來源：農業部，漁業署新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/25848）
- [press_release] 資料來源：警政署，各警察機關新聞發布，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/7505）
- [press_release] 資料來源：資訊服務處，中央研究院院新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/94024）
- [press_release] 資料來源：行政院，行政院消費者保護會-消費者保護新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/6421）
- [press_release] 資料來源：臺北市政府資訊局，臺北市市政網站整合平台之新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/128337）
- [press_release] 資料來源：經濟部國際貿易署，貿易署新聞發布，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/174199）
- [press_release] 資料來源：國家發展委員會，國家發展委員會新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/22927）
- [press_release] 資料來源：國家文官學院，國家文官學院新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/166117）
- [press_release] 資料來源：台灣中油股份有限公司，台灣中油公司新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/175903）
- [press_release] 資料來源：臺灣金融控股股份有限公司，臺灣金融控股股份有限公司網站新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/32021）
- [press_release] 資料來源：農業部，水產試驗所新聞稿，依政府資料開放授權條款第1版釋出，https://data.gov.tw/license（https://data.gov.tw/dataset/68551）

## Python 執行期依賴（不隨 repository 散布，由使用者自行安裝）

| 套件 | License | 用途 |
|---|---|---|
| numpy | BSD-3-Clause | n-gram、近重複偵測、compact lexicon |
| psutil | BSD-3-Clause | 研究量測（選用） |
| pytest | MIT | 測試 |
