from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from dataclasses import MISSING, asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

DAILY_DIR = PROJECT_ROOT / "data" / "daily"
SOURCES_FILE = DAILY_DIR / "SOURCES.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "daily"

UNKNOWN = "unknown"
YES = "yes"


class Status(Enum):
    APPROVED = "APPROVED"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


class ApprovalScope(Enum):
    """PRODUCTION：官方版本且授權明確；DEV_EXPERIMENT：只能用於 DEV 實驗，production freeze 前須重新審查權利。"""

    PRODUCTION = "production"
    DEV_EXPERIMENT = "dev_experiment"
    NONE = "none"


class Purpose(Enum):
    PRODUCTION = "production"
    DEV_EXPERIMENT = "dev_experiment"


class TrainingBasis(Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceFile:
    path: str
    url: str
    sha256: str
    bytes: int

    def local(self, raw_dir: Path = RAW_DIR) -> Path:
        return raw_dir / self.path


@dataclass(frozen=True)
class DailySource:
    """一個語料來源的授權與出處紀錄。權利欄位用 yes / no / conditional: … / unknown；
    training_use（AI / 統計模型訓練）與 redistribution 分開記錄；platform_restrictions 記錄授權之外的平台使用限制；
    archive_members_sha256 記錄官方 archive 內各檔案的 SHA-256，用來確認解壓副本與 archive 相同。"""

    source_id: str
    dataset_name: str
    provider: str
    official_page: str
    urls: tuple[str, ...]
    version: str
    retrieved_at: str
    license_name: str
    license_url: str
    commercial_use: str
    modification: str
    redistribution: str
    attribution: str
    training_use: str
    training_basis: TrainingBasis
    inference_basis: str
    data_type: str
    zh_tw_relevance: str
    fields_used: tuple[str, ...]
    fields_excluded: tuple[str, ...]
    document_identity: str
    files: tuple[SourceFile, ...]
    status: Status
    approval_scope: ApprovalScope
    reason: str
    platform_restrictions: tuple[str, ...] = ()
    archive_members_sha256: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, object]:
        row = asdict(self)
        row["training_basis"] = self.training_basis.value
        row["status"] = self.status.value
        row["approval_scope"] = self.approval_scope.value
        return row

    @classmethod
    def from_json(cls, row: dict[str, object]) -> DailySource:
        missing = [f.name for f in fields(cls) if f.name not in row and f.default is MISSING and f.default_factory is MISSING]
        if missing:
            raise ValueError(f"{row.get('source_id')}: 缺少欄位 {missing}")
        values = dict(row)
        values["urls"] = tuple(row["urls"])  # type: ignore[arg-type]
        values["fields_used"] = tuple(row["fields_used"])  # type: ignore[arg-type]
        values["fields_excluded"] = tuple(row["fields_excluded"])  # type: ignore[arg-type]
        values["platform_restrictions"] = tuple(row.get("platform_restrictions", ()))  # type: ignore[arg-type]
        values["files"] = tuple(SourceFile(**f) for f in row["files"])  # type: ignore[arg-type,union-attr]
        values["training_basis"] = TrainingBasis(row["training_basis"])
        values["status"] = Status(row["status"])
        values["approval_scope"] = ApprovalScope(row["approval_scope"])
        return cls(**values)  # type: ignore[arg-type]


class LicenseError(RuntimeError):
    pass


class LicenseGate:
    """只有 APPROVED 且每個授權欄位都已確定的來源可以匯入；任何欄位不確定就拒絕。
    production 用途另外要求 approval_scope 為 PRODUCTION。"""

    REQUIRED_YES = ("commercial_use", "modification", "training_use")
    DETERMINED = (
        "dataset_name",
        "provider",
        "official_page",
        "version",
        "retrieved_at",
        "license_name",
        "license_url",
        "redistribution",
        "attribution",
        "data_type",
        "zh_tw_relevance",
        "document_identity",
        "reason",
    )

    def problems(self, source: DailySource, purpose: Purpose = Purpose.DEV_EXPERIMENT) -> list[str]:
        found: list[str] = []
        if source.status is not Status.APPROVED:
            found.append(f"status {source.status.value}")
        allowed = {ApprovalScope.PRODUCTION} if purpose is Purpose.PRODUCTION else {ApprovalScope.PRODUCTION, ApprovalScope.DEV_EXPERIMENT}
        if source.approval_scope not in allowed:
            found.append(f"approval_scope {source.approval_scope.value} 不允許 {purpose.value}")
        for name in self.DETERMINED:
            value = str(getattr(source, name)).strip()
            if not value or value.lower().startswith(UNKNOWN):
                found.append(f"{name} 未確定")
        for name in self.REQUIRED_YES:
            if not str(getattr(source, name)).startswith(YES):
                found.append(f"{name} = {getattr(source, name)}")
        if source.training_basis is TrainingBasis.UNKNOWN:
            found.append("training_basis 未確定")
        if source.training_basis is TrainingBasis.INFERRED and not source.inference_basis.strip():
            found.append("training_basis 為 inferred 但沒有 inference_basis")
        if not source.urls or not source.files:
            found.append("沒有 URL 或檔案")
        found += [f"{f.path} 沒有 SHA-256" for f in source.files if len(f.sha256) != 64]
        if not source.fields_used:
            found.append("fields_used 為空")
        return found

    def require(self, source: DailySource, purpose: Purpose = Purpose.DEV_EXPERIMENT) -> None:
        found = self.problems(source, purpose)
        if found:
            raise LicenseError(f"{source.source_id}: " + "；".join(found))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class RawFiles:
    """匯入前確認本機原始檔與 manifest 記錄的 SHA-256 相同。"""

    def __init__(self, raw_dir: Path = RAW_DIR) -> None:
        self.raw_dir = raw_dir

    def verify(self, source: DailySource) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for record in source.files:
            path = record.local(self.raw_dir)
            if not path.exists():
                raise LicenseError(f"{source.source_id}: 找不到 {path}")
            actual = sha256_file(path)
            if actual != record.sha256:
                raise LicenseError(f"{source.source_id}: {record.path} SHA-256 不符（{actual}）")
            paths[Path(record.path).name] = path
        return paths


class SourceRegistry:
    def __init__(self, sources: Iterable[DailySource]) -> None:
        self._sources = {s.source_id: s for s in sources}

    @classmethod
    def load(cls, path: Path = SOURCES_FILE) -> SourceRegistry:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(DailySource.from_json(row) for row in data["sources"])

    def __iter__(self) -> Iterator[DailySource]:
        return iter(self._sources.values())

    def __getitem__(self, source_id: str) -> DailySource:
        return self._sources[source_id]

    def with_status(self, status: Status) -> list[DailySource]:
        return [s for s in self if s.status is status]
