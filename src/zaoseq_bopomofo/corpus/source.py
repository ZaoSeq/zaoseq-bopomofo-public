"""資料來源授權登錄（data/sources.json）。任何來源進 production corpus 前都必須在這裡通過檢查。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "data" / "sources.json"

# 授權欄位的合法值；"unknown" 或空字串一律視為狀態不明，不得進 production。
KNOWN_PERMISSIONS = frozenset({"allowed", "allowed_with_attribution", "allowed_under_general_grant", "not_allowed"})


class SourceStatus(Enum):
    APPROVED = "approved"
    # 已登錄但尚未完成下載或檢查，不得使用。
    PENDING = "pending"
    REJECTED = "rejected"


class Domain(Enum):
    """語料領域。language model 以領域為單位加權，不讓單一領域依原始句數主導。"""

    LEGAL = "legal"
    GOVERNMENT_FAQ = "government_faq"
    PUBLIC_SERVICE = "public_service"
    PRESS_RELEASE = "press_release"
    TERMINOLOGY = "terminology"
    OTHER_FORMAL = "other_formal"
    CHARACTER_DATA = "character_data"


class SourceKind(Enum):
    LAW_XML = "law_xml"
    # 通用 CSV / JSON / XML 表格資料，欄位由 text_fields 指定。
    TABULAR = "tabular"
    FAQ_CSV = "faq_csv"
    PRESS_JSON = "press_json"
    TERM_CSV = "term_csv"
    CHARACTER_TABLE = "character_table"
    NONE = "none"


@dataclass(frozen=True)
class SourceRecord:
    """一個資料來源的授權 provenance。

    授權欄位以資料集官方頁面的 license metadata 為準，不以搜尋結果為準。
    `text_fields` 是實際匯入的欄位；資料集中指向外部網站的網址不在授權範圍內，一律不抓取。
    """

    id: str
    dataset_name: str
    provider: str
    official_dataset_url: str
    download_url: str
    license: str
    license_url: str
    commercial_use: str
    modification: str
    redistribution: str
    ai_training: str
    attribution: str
    downloaded_at: str
    upstream_version_or_updated_at: str
    sha256: str
    allowed_uses: tuple[str, ...]
    notes: str
    status: SourceStatus
    kind: SourceKind
    ai_training_explicit: bool = False
    ai_training_basis: str = ""
    domain: Domain = Domain.OTHER_FORMAL
    file_format: str = ""
    raw_file: str = ""
    text_fields: tuple[str, ...] = ()
    excluded_fields: tuple[str, ...] = ()
    encoding: str = "utf-8-sig"

    def production_issues(self) -> tuple[str, ...]:
        """回傳不能進 production corpus 的原因；空 tuple 表示可以使用。"""
        issues: list[str] = []
        if self.status is not SourceStatus.APPROVED:
            issues.append(f"status={self.status.value}")
        for name in ("commercial_use", "modification", "redistribution", "ai_training"):
            value = getattr(self, name)
            if value not in KNOWN_PERMISSIONS:
                issues.append(f"{name} 狀態不明：{value!r}")
            elif value == "not_allowed":
                issues.append(f"{name} 不允許")
        if self.ai_training == "allowed_under_general_grant" and not self.ai_training_basis:
            issues.append("ai_training_basis 未說明一般授權依據")
        for name in ("license", "license_url", "attribution", "downloaded_at", "sha256", "official_dataset_url"):
            if not getattr(self, name):
                issues.append(f"{name} 未填")
        if "corpus" not in self.allowed_uses and self.kind is not SourceKind.CHARACTER_TABLE:
            issues.append("allowed_uses 未包含 corpus")
        return tuple(issues)

    @property
    def production_ready(self) -> bool:
        return not self.production_issues()


@dataclass(frozen=True)
class Registry:
    sources: tuple[SourceRecord, ...]
    rejected_sources: tuple[dict[str, str], ...] = field(default=())

    def get(self, source_id: str) -> SourceRecord:
        for record in self.sources:
            if record.id == source_id:
                return record
        raise KeyError(source_id)

    def production_sources(self, kinds: Iterable[SourceKind] | None = None) -> tuple[SourceRecord, ...]:
        wanted = set(kinds) if kinds is not None else None
        return tuple(
            s for s in self.sources if s.production_ready and (wanted is None or s.kind in wanted)
        )


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for raw in data["sources"]:
        values = dict(raw)
        values["status"] = SourceStatus(values["status"])
        values["kind"] = SourceKind(values["kind"])
        values["domain"] = Domain(values.get("domain", Domain.OTHER_FORMAL.value))
        for key in ("allowed_uses", "text_fields", "excluded_fields"):
            values[key] = tuple(values.get(key, ()))
        records.append(SourceRecord(**values))
    ids = [r.id for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError("sources.json 中 id 重複")
    return Registry(tuple(records), tuple(data.get("rejected_sources", ())))


def save_registry(registry: Registry, path: Path = REGISTRY_PATH) -> None:
    def encode(record: SourceRecord) -> dict[str, object]:
        values = asdict(record)
        values["status"] = record.status.value
        values["kind"] = record.kind.value
        values["domain"] = record.domain.value
        for key in ("allowed_uses", "text_fields", "excluded_fields"):
            values[key] = list(values[key])
        return values

    payload = {
        "schema": "zaoseq-bopomofo/sources/v1",
        "sources": [encode(r) for r in registry.sources],
        "rejected_sources": list(registry.rejected_sources),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
