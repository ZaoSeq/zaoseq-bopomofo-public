"""斷句、去重與 train/dev/test 切分。"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum

from zaoseq_bopomofo.corpus.importer import RawDocument
from zaoseq_bopomofo.corpus.normalize import han_ratio, is_han, normalize_text

_SENTENCE_END = re.compile(r"(?<=[。！？；])|\n")
# 條列編號（「一、」「（一）」「1.」「第 3 條」）是格式 metadata，不是語句內容。
_LEADING_MARKER = re.compile(
    r"^\s*(?:第\s*[0-9一二三四五六七八九十百千]+\s*[條項款目編章節]\s*|"
    r"[（(]?[0-9一二三四五六七八九十]+[)）、.．]\s*)+"
)
MIN_HAN = 4
MAX_CHARS = 120
MIN_HAN_RATIO = 0.6


class Split(Enum):
    TRAIN = "train"
    DEV = "dev"
    TEST = "test"


@dataclass(frozen=True)
class Sentence:
    source_id: str
    doc_id: str
    text: str
    split: Split


def split_sentences(text: str) -> list[str]:
    """先依句末標點與換行斷句；過長的句子再依逗號切成子句，避免單一法條變成數百字的一句。"""
    pieces: list[str] = []
    for chunk in _SENTENCE_END.split(normalize_text(text)):
        chunk = _LEADING_MARKER.sub("", chunk).strip()
        if not chunk:
            continue
        if len(chunk) <= MAX_CHARS:
            pieces.append(chunk)
            continue
        buffer = ""
        for part in re.split(r"(?<=，)", chunk):
            if buffer and len(buffer) + len(part) > MAX_CHARS:
                pieces.append(buffer)
                buffer = ""
            buffer += part
        if buffer:
            pieces.append(buffer)
    return [p for p in pieces if _usable(p)]


def _usable(sentence: str) -> bool:
    return sum(is_han(ch) for ch in sentence) >= MIN_HAN and han_ratio(sentence) >= MIN_HAN_RATIO


def dedupe_key(sentence: str) -> str:
    """只保留漢字作為去重鍵：標點、空白與數字不同的近重複句（例如條號不同的相同條文）視為同一句。"""
    return "".join(ch for ch in sentence if is_han(ch))


def assign_split(source_id: str, doc_id: str, dev_percent: int = 5, test_percent: int = 5) -> Split:
    """以文件為單位做 deterministic hash 切分，同一份文件的句子不會跨 split。"""
    bucket = int(hashlib.sha256(f"{source_id}\x00{doc_id}".encode("utf-8")).hexdigest(), 16) % 100
    if bucket < test_percent:
        return Split.TEST
    if bucket < test_percent + dev_percent:
        return Split.DEV
    return Split.TRAIN


def build_sentences(documents: Iterable[RawDocument], seen: set[str]) -> Iterator[Sentence]:
    """`seen` 是跨來源共用的去重鍵集合：同一句只保留第一次出現（依來源處理順序），
    所以近重複句不可能同時出現在 train 與 test。"""
    for document in documents:
        split = assign_split(document.source_id, document.doc_id)
        for text in split_sentences(document.text):
            key = dedupe_key(text)
            if key in seen:
                continue
            seen.add(key)
            yield Sentence(document.source_id, document.doc_id, text, split)
