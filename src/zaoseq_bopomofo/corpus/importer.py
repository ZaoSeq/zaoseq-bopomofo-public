"""官方資料集下載與欄位抽取。每一筆文字都保留 source_id，只讀登錄在 text_fields 的欄位。"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.corpus.records import read_records
from zaoseq_bopomofo.corpus.source import SourceKind, SourceRecord

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"


class SourceIntegrityError(RuntimeError):
    """本機原始檔的 SHA-256 與登錄不符：上游可能已更新，必須重新檢查授權並更新登錄後才能使用。"""


@dataclass(frozen=True)
class RawDocument:
    """`doc_id` 在來源內唯一（例如法規名稱、FAQ 列號），train/dev/test 以文件為單位切分。"""

    source_id: str
    doc_id: str
    field: str
    text: str


def raw_path(record: SourceRecord, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / record.id / record.raw_file


def verify(record: SourceRecord, raw_dir: Path = RAW_DIR) -> Path:
    path = raw_path(record, raw_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} 不存在；請依 data/SOURCES.md 下載")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != record.sha256:
        raise SourceIntegrityError(f"{record.id}: sha256 {digest} 與登錄 {record.sha256} 不符")
    return path


def iter_documents(record: SourceRecord, raw_dir: Path = RAW_DIR) -> Iterator[RawDocument]:
    path = verify(record, raw_dir)
    if record.kind is SourceKind.LAW_XML:
        yield from _law_documents(record, path)
    elif record.kind is SourceKind.FAQ_CSV:
        yield from _csv_documents(record, path)
    elif record.kind is SourceKind.PRESS_JSON:
        yield from _press_documents(record, path)
    elif record.kind is SourceKind.TERM_CSV:
        yield from _term_documents(record, path)
    elif record.kind is SourceKind.TABULAR:
        yield from _tabular_documents(record, path)
    else:
        raise ValueError(f"{record.id}: {record.kind.value} 不是語料來源")


def _law_documents(record: SourceRecord, path: Path) -> Iterator[RawDocument]:
    with zipfile.ZipFile(path) as archive:
        with archive.open("FalV.xml") as handle:
            root = ET.parse(handle).getroot()
    for law in root.iter("法規"):
        name = (law.findtext("法規名稱") or "").strip()
        if not name:
            continue
        # 廢止法規仍是合法文本，但通常是過時用語；保留並在 doc_id 標示，方便日後篩選。
        doc_id = name + ("#廢止" if (law.findtext("廢止註記") or "").strip() else "")
        if "法規名稱" in record.text_fields:
            yield RawDocument(record.id, doc_id, "法規名稱", name)
        if "前言" in record.text_fields and (law.findtext("前言") or "").strip():
            yield RawDocument(record.id, doc_id, "前言", law.findtext("前言") or "")
        if "條文內容" in record.text_fields:
            for article in law.iter("條文內容"):
                if article.text and article.text.strip():
                    yield RawDocument(record.id, doc_id, "條文內容", article.text)


def _csv_rows(record: SourceRecord, path: Path) -> list[dict[str, str]]:
    text = path.read_bytes().decode(record.encoding)
    return list(csv.DictReader(io.StringIO(text)))


def _csv_documents(record: SourceRecord, path: Path) -> Iterator[RawDocument]:
    for index, row in enumerate(_csv_rows(record, path)):
        for field in record.text_fields:
            value = (row.get(field) or "").strip()
            if value.startswith("Ans:"):
                value = value[4:]
            if value:
                yield RawDocument(record.id, f"row{index}", field, value)


def _press_documents(record: SourceRecord, path: Path) -> Iterator[RawDocument]:
    items = json.loads(path.read_text(encoding=record.encoding))
    for index, item in enumerate(items):
        for field in record.text_fields:
            value = item.get(field) or ""
            if value.strip():
                yield RawDocument(record.id, f"item{index}", field, value)


def _term_documents(record: SourceRecord, path: Path) -> Iterator[RawDocument]:
    for index, row in enumerate(_csv_rows(record, path)):
        value = (row.get("中文名稱") or "").strip()
        # 同一英文詞的多個中文譯名以全形分號分隔，各自是一個詞條。
        for term in value.replace(";", "；").split("；"):
            if term.strip():
                yield RawDocument(record.id, f"row{index}", "中文名稱", term.strip())


def _tabular_documents(record: SourceRecord, path: Path) -> Iterator[RawDocument]:
    """每一列（一則問答、一篇新聞稿）是一份文件；只讀 text_fields，其他欄位（網址、日期、機關）一律忽略。"""
    for index, row in enumerate(read_records(path, record.file_format, record.encoding or None)):
        for field in record.text_fields:
            value = (row.get(field) or "").strip().strip('"')
            if value:
                yield RawDocument(record.id, f"row{index}", field, value)
