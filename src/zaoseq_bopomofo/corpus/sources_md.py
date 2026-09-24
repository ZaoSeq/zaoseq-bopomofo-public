"""由 data/sources.json 產生 data/SOURCES.md，讓人讀的紀錄與機器讀的登錄不會分歧。

    python -m zaoseq_bopomofo.corpus.sources_md
"""

from __future__ import annotations


from zaoseq_bopomofo.corpus.source import REGISTRY_PATH, Registry, SourceRecord, load_registry

OUTPUT = REGISTRY_PATH.parent / "SOURCES.md"

_HEADER = """# 資料來源與授權紀錄

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
"""

_FOOTER = """
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
"""


def _row(record: SourceRecord) -> str:
    fields = [
        ("dataset_name", record.dataset_name),
        ("provider", record.provider),
        ("official_dataset_url", record.official_dataset_url),
        ("download_url", record.download_url),
        ("license", record.license),
        ("license_url", record.license_url),
        ("commercial_use", record.commercial_use),
        ("modification", record.modification),
        ("redistribution", record.redistribution),
        ("ai_training", record.ai_training),
        ("ai_training_explicit", str(record.ai_training_explicit).lower()),
        ("ai_training_basis", record.ai_training_basis or "—"),
        ("domain", record.domain.value),
        ("attribution", record.attribution),
        ("downloaded_at", record.downloaded_at),
        ("upstream_version_or_updated_at", record.upstream_version_or_updated_at),
        ("sha256", record.sha256),
        ("allowed_uses", ", ".join(record.allowed_uses)),
        ("text_fields", ", ".join(record.text_fields) or "—"),
        ("excluded_fields", ", ".join(record.excluded_fields) or "—"),
        ("status", record.status.value),
        ("production_ready", "yes" if record.production_ready else "NO: " + "; ".join(record.production_issues())),
        ("notes", record.notes or "—"),
    ]
    body = "\n".join(f"{name}: {value}" for name, value in fields)
    return f"### {record.id}\n\n```\n{body}\n```\n"


def render(registry: Registry) -> str:
    parts = [_HEADER, "## 已登錄來源\n"]
    parts.extend(_row(r) for r in registry.sources)
    parts.append("## 拒絕或排除的來源\n")
    parts.append("| id | 原因 |\n|---|---|")
    parts.extend(f"| {r['id']} | {r['reason']} |" for r in registry.rejected_sources)
    parts.append(_FOOTER)
    return "\n".join(parts)


def main() -> int:
    OUTPUT.write_text(render(load_registry()), encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
