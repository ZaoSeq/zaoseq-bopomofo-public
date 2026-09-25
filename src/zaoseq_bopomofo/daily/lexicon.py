from __future__ import annotations

import itertools
import json
import math
import re
import statistics
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from zaoseq_bopomofo.daily.sources import DAILY_DIR

LEXICON_DIR = DAILY_DIR / "lexicon"
HAN_RUN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]+")
MAX_N = 4
DAILY = "daily"
DERIVED_TIER_BASE = 1000


def han_ngrams(text: str, n_values: Iterable[int]) -> Iterable[str]:
    """只在連續漢字內取 n-gram，不跨標點、數字或英文。"""
    sizes = tuple(n_values)
    for run in HAN_RUN.findall(text):
        for n in sizes:
            for i in range(len(run) - n + 1):
                yield run[i : i + n]


@dataclass(frozen=True)
class CorpusSentence:
    slice_name: str
    source_id: str
    doc_key: str
    text: str


@dataclass
class NgramTable:
    name: str
    counts: dict[str, int]
    total: int

    def probability(self, gram: str) -> float:
        return self.counts.get(gram, 0) / self.total if self.total else 0.0


class NgramCounter:
    """1..MAX_N 字元 n-gram；2 字以上計數 < min_count 的剪掉以控制記憶體。"""

    def __init__(self, min_count: int = 2) -> None:
        self._min_count = min_count

    def count(self, name: str, texts: Iterable[str]) -> NgramTable:
        counts: Counter[str] = Counter()
        for text in texts:
            counts.update(han_ngrams(text, range(1, MAX_N + 1)))
        total = sum(c for g, c in counts.items() if len(g) == 1)
        kept = {g: c for g, c in counts.items() if len(g) == 1 or c >= self._min_count}
        return NgramTable(name, kept, total)


class FrequencyEstimator(ABC):
    name: str

    @abstractmethod
    def probability(self, tables: CorpusTables, gram: str) -> float: ...


class PooledEstimator(FrequencyEstimator):
    """所有語料直接相加（raw frequency）。"""

    name = "pooled"

    def probability(self, tables: CorpusTables, gram: str) -> float:
        return tables.pooled_count(gram) / tables.pooled_total


@dataclass(frozen=True)
class InterpolatedEstimator(FrequencyEstimator):
    """λ·P_daily + (1−λ)·Σ_d w_d·P_d；政府部分與 V0 語言模型使用相同的領域權重。"""

    daily_weight: float

    @property
    def name(self) -> str:  # type: ignore[override]
        return f"interpolated_daily{self.daily_weight:g}"

    def probability(self, tables: CorpusTables, gram: str) -> float:
        return self.daily_weight * tables.daily.probability(gram) + (1 - self.daily_weight) * tables.gov_probability(gram)


@dataclass
class CorpusTables:
    gov: dict[str, NgramTable]
    gov_weights: dict[str, float]
    daily: NgramTable
    _pooled: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        pooled: Counter[str] = Counter()
        for table in (*self.gov.values(), self.daily):
            pooled.update(table.counts)
        self._pooled = dict(pooled)
        self.pooled_total = sum(t.total for t in (*self.gov.values(), self.daily))

    def pooled_count(self, gram: str) -> int:
        return self._pooled.get(gram, 0)

    def gov_probability(self, gram: str) -> float:
        return math.fsum(w * self.gov[d].probability(gram) for d, w in self.gov_weights.items())

    def grams(self, length: int) -> Iterable[str]:
        return (g for g in self._pooled if len(g) == length)

    def extension_share(self) -> dict[str, float]:
        """每個 n-gram 被單一左或右延伸（n+1 字）涵蓋的最大比例；接近 1 表示它只是更長詞的片段。"""
        best: dict[str, int] = {}
        for gram, count in self._pooled.items():
            if len(gram) < 3:
                continue
            for child in (gram[1:], gram[:-1]):
                if count > best.get(child, 0):
                    best[child] = count
        return {g: c / self._pooled[g] for g, c in best.items() if self._pooled.get(g)}


@dataclass(frozen=True)
class ExtractionPolicy:
    name: str
    estimator: FrequencyEstimator
    min_per_million: float = 2.0
    min_documents: int = 2
    min_pmi: float = 0.0
    fragment_share: float = 0.9
    max_readings: int = 4
    median_weight: float = 10.0
    weight_bounds: tuple[float, float] = (3.0, 200.0)


@dataclass(frozen=True)
class DerivedLexiconEntry:
    text: str
    readings: tuple[tuple[str, ...], ...]
    corpus_count: int
    document_count: int
    daily_count: int
    government_count: int
    domain_distribution: Mapping[str, int]
    pmi: float
    estimated_frequency: float
    weight: float
    source_ids: tuple[str, ...]
    provenance: str
    eligibility: str

    @property
    def eligible(self) -> bool:
        return self.eligibility == "eligible"

    def to_json(self) -> dict[str, object]:
        row = asdict(self)
        row["readings"] = [list(r) for r in self.readings]
        row["domain_distribution"] = dict(self.domain_distribution)
        row["source_ids"] = list(self.source_ids)
        return row


@dataclass
class Occurrence:
    count: int = 0
    by_slice: Counter[str] = field(default_factory=Counter)
    by_source: Counter[str] = field(default_factory=Counter)
    documents: set[str] = field(default_factory=set)


class OccurrenceScanner:
    """第二次掃描：只對候選詞計算精確的來源、領域與文件數（provenance 用）。"""

    def scan(self, sentences: Iterable[CorpusSentence], candidates: set[str]) -> dict[str, Occurrence]:
        found: dict[str, Occurrence] = {}
        sizes = sorted({len(c) for c in candidates})
        for sentence in sentences:
            for gram in han_ngrams(sentence.text, sizes):
                if gram in candidates:
                    occurrence = found.setdefault(gram, Occurrence())
                    occurrence.count += 1
                    occurrence.by_slice[sentence.slice_name] += 1
                    occurrence.by_source[sentence.source_id] += 1
                    occurrence.documents.add(sentence.doc_key)
        return found


class ReadingResolver:
    """標注器能無歧義標注時用單一讀音；否則列出 CNS 讀音組合，超過上限就不收。"""

    def __init__(self) -> None:
        from zaoseq_bopomofo.corpus.annotate import ReadingAnnotator
        from zaoseq_bopomofo.lexicon.builder import read_builtin, read_char_readings
        from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

        rows = read_char_readings(DEFAULT_CHAR_READINGS)
        self._annotator = ReadingAnnotator(rows, read_builtin(DEFAULT_BUILTIN))
        self._cns: dict[str, list[str]] = {}
        for row in rows:
            if row.plane in (1, 2) and row.reading not in self._cns.setdefault(row.char, []):
                self._cns[row.char].append(row.reading)

    def resolve(self, text: str, limit: int) -> tuple[tuple[str, ...], ...] | None:
        annotation = self._annotator.annotate(text)
        if hasattr(annotation, "readings"):
            return (tuple(annotation.readings),)  # type: ignore[union-attr]
        options = list(itertools.islice(itertools.product(*(self._cns.get(c, []) for c in text)), limit + 1))
        if not options or len(options) > limit:
            return None
        return tuple(options)


class FrequencyAwareExtractor:
    def __init__(self, tables: CorpusTables, resolver: ReadingResolver, known: set[str]) -> None:
        self._tables = tables
        self._resolver = resolver
        self._known = known
        self._extension = tables.extension_share()

    def pmi(self, gram: str, estimator: FrequencyEstimator) -> float:
        joint = estimator.probability(self._tables, gram)
        values = []
        for cut in range(1, len(gram)):
            left = estimator.probability(self._tables, gram[:cut])
            right = estimator.probability(self._tables, gram[cut:])
            values.append(math.log2(joint / (left * right)) if joint and left and right else -math.inf)
        return min(values)

    def frequent(self, policy: ExtractionPolicy) -> list[str]:
        threshold = policy.min_per_million / 1e6
        grams = (g for n in range(2, MAX_N + 1) for g in self._tables.grams(n))
        return sorted(g for g in grams if policy.estimator.probability(self._tables, g) >= threshold)

    def extract(self, policy: ExtractionPolicy, occurrences: Mapping[str, Occurrence], gov_slices: set[str]) -> list[DerivedLexiconEntry]:
        rows: list[tuple[str, float, float, tuple[tuple[str, ...], ...], str]] = []
        for gram in self.frequent(policy):
            occurrence = occurrences.get(gram, Occurrence())
            pmi = self.pmi(gram, policy.estimator)
            frequency = policy.estimator.probability(self._tables, gram) * 1e6
            readings: tuple[tuple[str, ...], ...] = ()
            if gram in self._known:
                reason = "known_builtin"
            elif len(occurrence.documents) < policy.min_documents:
                reason = "too_few_documents"
            elif pmi < policy.min_pmi:
                reason = "low_pmi"
            elif len(gram) <= 3 and self._extension.get(gram, 0.0) >= policy.fragment_share:
                reason = "fragment_of_longer_ngram"
            else:
                resolved = self._resolver.resolve(gram, policy.max_readings)
                reason = "eligible" if resolved else "readings_unresolved"
                readings = resolved or ()
            rows.append((gram, pmi, frequency, readings, reason))
        eligible = [f for _, _, f, _, r in rows if r == "eligible"]
        median = statistics.median(eligible) if eligible else 1.0
        low, high = policy.weight_bounds
        provenance = (
            f"char n-gram (2..{MAX_N}), estimator={policy.estimator.name}, >= {policy.min_per_million}/M, "
            f"docs >= {policy.min_documents}, PMI >= {policy.min_pmi}, fragment share < {policy.fragment_share}"
        )
        entries = []
        for gram, pmi, frequency, readings, reason in rows:
            occurrence = occurrences.get(gram, Occurrence())
            government = sum(c for s, c in occurrence.by_slice.items() if s in gov_slices)
            entries.append(
                DerivedLexiconEntry(
                    text=gram,
                    readings=readings,
                    corpus_count=occurrence.count,
                    document_count=len(occurrence.documents),
                    daily_count=occurrence.count - government,
                    government_count=government,
                    domain_distribution=dict(sorted(occurrence.by_slice.items())),
                    pmi=round(pmi, 4),
                    estimated_frequency=round(frequency, 4),
                    weight=round(min(high, max(low, policy.median_weight * frequency / median)), 4),
                    source_ids=tuple(sorted(occurrence.by_source)),
                    provenance=provenance,
                    eligibility=reason,
                )
            )
        return entries


class DerivedLexiconBuilder:
    """builtin 詞表 + 合格衍生詞；每個衍生詞以自己的權重建立獨立等級（多讀音時平分）。"""

    def build(self, entries: Sequence[DerivedLexiconEntry]):  # type: ignore[no-untyped-def]
        from zaoseq_bopomofo.lexicon.builder import BuiltinRow, FrequencyConfig, build_lexicon, read_builtin, read_char_readings
        from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

        builtin = list(read_builtin(DEFAULT_BUILTIN))
        existing = {(r.text, r.readings) for r in builtin}
        tiers: dict[int, float] = {}
        rows: list[BuiltinRow] = []
        for index, entry in enumerate(e for e in entries if e.eligible):
            tier = DERIVED_TIER_BASE + index
            tiers[tier] = entry.weight / len(entry.readings)
            for readings in entry.readings:
                if (entry.text, readings) not in existing:
                    existing.add((entry.text, readings))
                    rows.append(BuiltinRow(entry.text, tier, readings, -1))
        frequency = FrequencyConfig(tier_weights={**FrequencyConfig().tier_weights, **tiers})
        report = build_lexicon(read_char_readings(DEFAULT_CHAR_READINGS), [*builtin, *rows], frequency)
        if report.errors:
            raise ValueError(report.errors[:5])
        return report.lexicon, len(rows)


def corpus_sentences(gov_domains: Iterable[str], daily_sources: Iterable[str] | None = None) -> list[CorpusSentence]:
    """政府語料與日常語料的 train split；`daily_sources` 為 None 時使用全部日常來源。"""
    from zaoseq_bopomofo.daily.corpus import load_sentences
    from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

    wanted = set(gov_domains)
    rows: list[CorpusSentence] = []
    for path in sorted((PROJECT_ROOT / "data" / "corpus").glob("*/sentences.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["split"] == "train" and row.get("domain") in wanted:
                rows.append(CorpusSentence(row["domain"], row["source_id"], f"{row['source_id']}:{row['doc_id']}", row["text"]))
    for sentence in load_sentences(sources=daily_sources):
        if sentence.split == "train":
            rows.append(CorpusSentence(DAILY, sentence.source_id, f"{sentence.source_id}:{sentence.doc_id}", sentence.text))
    return rows


def build_tables(sentences: Sequence[CorpusSentence], gov_weights: Mapping[str, float], counter: NgramCounter | None = None) -> CorpusTables:
    counter = counter or NgramCounter()
    gov = {d: counter.count(d, (s.text for s in sentences if s.slice_name == d)) for d in gov_weights}
    daily = counter.count(DAILY, (s.text for s in sentences if s.slice_name == DAILY))
    return CorpusTables(gov, dict(gov_weights), daily)


def write_entries(path: Path, entries: Sequence[DerivedLexiconEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(json.dumps(entry.to_json(), ensure_ascii=False) + "\n")
