from __future__ import annotations

import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from zaoseq_bopomofo.corpus.normalize import han_ratio, is_han
from zaoseq_bopomofo.daily.script import ScriptClassifier, ScriptLabel

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_MARKUP = re.compile(r"</?[a-zA-Z][^>]*>|```|&[a-z]+;|\[[^\]]*\]\([^)]*\)")
_TW_ID = re.compile(r"\b[A-Z][12]\d{8}\b")
_PHONE = re.compile(r"(?:\+?886[-\s]?|0)9\d{2}[-\s]?\d{3}[-\s]?\d{3}|\(?0\d{1,2}\)?[-\s]?\d{3,4}[-\s]?\d{4}")
_LONG_NUMBER = re.compile(r"\d{6,}")
_CODE = re.compile(r"\b(?:def|import|return|function|class|print)\b|[{};]\s*$|==|=>", re.MULTILINE)

# 只做統計，不用來過濾；專案自行撰寫的短清單。
PROFANITY = ("幹你", "幹拎", "靠北", "靠腰", "他媽的", "媽的", "機掰", "雞掰", "王八蛋", "混蛋", "白癡", "智障", "去死")


class Drop(Enum):
    URL = "url"
    EMAIL = "email"
    MARKUP_OR_CODE = "markup_or_code"
    PERSONAL_ID = "personal_id"
    PHONE = "phone"
    LONG_NUMBER = "long_number"
    WEIRD_UNICODE = "weird_unicode"
    SIMPLIFIED = "simplified"
    NON_STANDARD_CHAR = "non_standard_char"
    TOO_SHORT_OR_LOW_HAN = "too_short_or_low_han"
    DUPLICATE_IN_SOURCE = "duplicate_in_source"
    DUPLICATE_OTHER_DAILY = "duplicate_other_daily_source"
    EVAL_OVERLAP = "eval_overlap"
    CROSS_SPLIT_NEAR_DUP = "cross_split_near_dup"


def weird_unicode(text: str) -> tuple[str, ...]:
    """私用區、控制與格式字元、注音符號混入漢字、CJK 相容字、康熙部首、半形片假名等。"""
    found: list[str] = []
    for ch in text:
        code = ord(ch)
        category = unicodedata.category(ch)
        if category in ("Co", "Cs") or (category in ("Cc", "Cf") and ch not in "\n\t"):
            found.append(f"U+{code:04X}")
        elif 0x3100 <= code <= 0x312F or 0x31A0 <= code <= 0x31BF:
            found.append("bopomofo")
        elif 0xF900 <= code <= 0xFAFF or 0x2F00 <= code <= 0x2FDF or 0x2E80 <= code <= 0x2EFF:
            found.append("compatibility_or_radical")
        elif 0xFF61 <= code <= 0xFF9F or 0x1F000 <= code <= 0x1FAFF:
            found.append("halfwidth_kana_or_emoji")
    return tuple(found)


def document_problems(text: str) -> tuple[Drop, ...]:
    problems: list[Drop] = []
    if _URL.search(text):
        problems.append(Drop.URL)
    if _EMAIL.search(text):
        problems.append(Drop.EMAIL)
    if _MARKUP.search(text) or len(_CODE.findall(text)) >= 2:
        problems.append(Drop.MARKUP_OR_CODE)
    if _TW_ID.search(text):
        problems.append(Drop.PERSONAL_ID)
    if _PHONE.search(text):
        problems.append(Drop.PHONE)
    if _LONG_NUMBER.search(text):
        problems.append(Drop.LONG_NUMBER)
    return tuple(problems)


@dataclass
class SourceQuality:
    """一個來源的品質統計；所有欄位都由資料計算，不含人工調整。"""

    source_id: str
    documents: int = 0
    documents_dropped: Counter[str] = field(default_factory=Counter)
    nfc_changed_documents: int = 0
    sentences_seen: int = 0
    sentences_kept: int = 0
    dropped: Counter[str] = field(default_factory=Counter)
    weird_unicode: Counter[str] = field(default_factory=Counter)
    simplified_markers: Counter[str] = field(default_factory=Counter)
    non_standard_chars: Counter[str] = field(default_factory=Counter)
    traditional_ratios: list[float] = field(default_factory=list)
    han_ratios: list[float] = field(default_factory=list)
    han_lengths: list[int] = field(default_factory=list)
    profanity: Counter[str] = field(default_factory=Counter)
    contributors: Counter[str] = field(default_factory=Counter)
    template_prefixes: Counter[str] = field(default_factory=Counter)
    splits: Counter[str] = field(default_factory=Counter)
    eval_overlap: Counter[str] = field(default_factory=Counter)

    def summary(self) -> dict[str, object]:
        lengths = self.han_lengths or [0]
        buckets = Counter(_bucket(n) for n in self.han_lengths)
        contributors = sum(self.contributors.values())
        top = self.contributors.most_common(10)
        templates = {p: c for p, c in self.template_prefixes.most_common(10) if c >= 20}
        return {
            "documents": self.documents,
            "documents_dropped": dict(self.documents_dropped.most_common()),
            "nfc_changed_documents": self.nfc_changed_documents,
            "sentences_seen": self.sentences_seen,
            "sentences_kept": self.sentences_kept,
            "sentences_dropped": dict(self.dropped.most_common()),
            "simplified_rate": round(self.dropped[Drop.SIMPLIFIED.value] / self.sentences_seen, 4) if self.sentences_seen else 0.0,
            "traditional_ratio_mean_all_seen": round(statistics.fmean(self.traditional_ratios), 4) if self.traditional_ratios else None,
            "han_ratio_mean_kept": round(statistics.fmean(self.han_ratios), 4) if self.han_ratios else None,
            "han_chars_kept": sum(self.han_lengths),
            "length_han_chars": {
                "mean": round(statistics.fmean(lengths), 2),
                "median": statistics.median(lengths),
                "p95": sorted(lengths)[int(0.95 * (len(lengths) - 1))],
                "buckets": dict(sorted(buckets.items())),
            },
            "weird_unicode": dict(self.weird_unicode.most_common()),
            "top_simplified_markers": dict(self.simplified_markers.most_common(15)),
            "top_non_standard_chars": dict(self.non_standard_chars.most_common(15)),
            "profanity_hits_kept": dict(self.profanity.most_common()),
            "source_concentration": {
                "contributors": len(self.contributors),
                "top1_share": round(top[0][1] / contributors, 4) if top else None,
                "top10_share": round(sum(c for _, c in top) / contributors, 4) if top else None,
            },
            "template_prefixes_ge_20": templates,
            "splits": dict(sorted(self.splits.items())),
            "eval_overlap_by_reference": dict(self.eval_overlap.most_common()),
        }


def _bucket(n: int) -> str:
    for upper, name in ((3, "01-03"), (7, "04-07"), (15, "08-15"), (31, "16-31")):
        if n <= upper:
            return name
    return "32+"


class SentenceInspector:
    """單句檢查：怪異字元、字體；回傳 None 表示保留。"""

    def __init__(self, classifier: ScriptClassifier) -> None:
        self._classifier = classifier

    def inspect(self, sentence: str, stats: SourceQuality) -> Drop | None:
        weird = weird_unicode(sentence)
        verdict = self._classifier.classify(sentence)
        stats.traditional_ratios.append(verdict.traditional_ratio)
        if weird:
            stats.weird_unicode.update(weird)
            return Drop.WEIRD_UNICODE
        if verdict.label is ScriptLabel.SIMPLIFIED:
            stats.simplified_markers.update(verdict.simplified_chars + verdict.simplified_words)
            return Drop.SIMPLIFIED
        if verdict.label is ScriptLabel.NON_STANDARD:
            stats.non_standard_chars.update(verdict.other_chars)
            return Drop.NON_STANDARD_CHAR
        return None

    @staticmethod
    def record_kept(sentence: str, stats: SourceQuality) -> None:
        stats.sentences_kept += 1
        stats.han_ratios.append(han_ratio(sentence))
        han = "".join(c for c in sentence if is_han(c))
        stats.han_lengths.append(len(han))
        stats.template_prefixes[han[:6]] += len(han) >= 10
        stats.profanity.update(w for w in PROFANITY if w in sentence)
