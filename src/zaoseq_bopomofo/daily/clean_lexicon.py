from __future__ import annotations

import itertools
import math
import statistics
from abc import ABC, abstractmethod
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from zaoseq_bopomofo.daily.lexicon import (
    DAILY,
    MAX_N,
    CorpusSentence,
    CorpusTables,
    DerivedLexiconEntry,
    NgramTable,
)

NUMERALS = frozenset("〇零一二三四五六七八九十百千萬兩0123456789０１２３４５６７８９")
WEIGHT_BOUNDS = (3.0, 200.0)
MEDIAN_WEIGHT = 10.0
FRAGMENT_SHARE = 0.9


# ---------------------------------------------------------------- reading policies


class ReadingEvidence:
    """讀音證據：CNS 單字讀音（全部字面）、builtin 多字詞的唯一明確讀音、builtin 單字的唯一明確讀音。"""

    def __init__(self, char_readings: Iterable[object], builtin: Iterable[object]) -> None:
        cns: dict[str, list[str]] = {}
        for row in char_readings:
            options = cns.setdefault(row.char, [])  # type: ignore[attr-defined]
            if row.reading not in options:  # type: ignore[attr-defined]
                options.append(row.reading)  # type: ignore[attr-defined]
        self.cns = cns
        words: dict[str, set[tuple[str, ...]]] = {}
        singles: dict[str, set[str]] = {}
        for row in builtin:
            if row.readings is None:  # type: ignore[attr-defined]
                continue
            if len(row.text) == 1:  # type: ignore[attr-defined]
                singles.setdefault(row.text, set()).add(row.readings[0])  # type: ignore[attr-defined]
            else:
                words.setdefault(row.text, set()).add(row.readings)  # type: ignore[attr-defined]
        self.words = {w: next(iter(r)) for w, r in words.items() if len(r) == 1}
        self.singles = {c: next(iter(r)) for c, r in singles.items() if len(r) == 1}
        self.max_word = max((len(w) for w in self.words), default=1)

    @classmethod
    def load(cls) -> ReadingEvidence:
        from zaoseq_bopomofo.lexicon.builder import read_builtin, read_char_readings
        from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

        return cls(read_char_readings(DEFAULT_CHAR_READINGS), read_builtin(DEFAULT_BUILTIN))

    def unique(self, char: str) -> str | None:
        options = self.cns.get(char, [])
        return options[0] if len(options) == 1 else None


class ReadingPolicy(ABC):
    """回傳一個詞的讀音序列；None 表示證據不足、不收這個詞。"""

    name: str
    single_reading = True

    def __init__(self, evidence: ReadingEvidence) -> None:
        self._evidence = evidence

    @abstractmethod
    def readings(self, text: str) -> tuple[tuple[str, ...], ...] | None: ...


class UnambiguousReadings(ReadingPolicy):
    """R1：每個字都只有一個 CNS 讀音。"""

    name = "R1_unambiguous"

    def readings(self, text: str) -> tuple[tuple[str, ...], ...] | None:
        sequence = [self._evidence.unique(c) for c in text]
        return (tuple(sequence),) if all(sequence) else None  # type: ignore[arg-type]


class KnownWordReadings(ReadingPolicy):
    """R2：多音字只能出現在 builtin 多字詞（唯一明確讀音、最長匹配）涵蓋的範圍內；其餘字必須只有一個 CNS 讀音。"""

    name = "R2_known_word"
    use_single_defaults = False

    def readings(self, text: str) -> tuple[tuple[str, ...], ...] | None:
        evidence = self._evidence
        out: list[str] = []
        i = 0
        while i < len(text):
            for length in range(min(evidence.max_word, len(text) - i), 1, -1):
                word = text[i : i + length]
                if word in evidence.words:
                    out.extend(evidence.words[word])
                    i += length
                    break
            else:
                reading = evidence.unique(text[i])
                if reading is None and self.use_single_defaults:
                    default = evidence.singles.get(text[i])
                    reading = default if default in evidence.cns.get(text[i], []) else None
                if reading is None:
                    return None
                out.append(reading)
                i += 1
        return (tuple(out),)


class BoundedReadings(KnownWordReadings):
    """R3：R2 再加上 builtin 單字列出的唯一明確讀音；每個詞仍只有一組讀音。"""

    name = "R3_bounded"
    use_single_defaults = True


class CartesianReadings(ReadingPolicy):
    """R0（只作對照）：R3 無法決定時列出 CNS 字面 1、2 的讀音組合，最多 `limit` 組。"""

    name = "R0_cartesian"
    single_reading = False

    def __init__(self, evidence: ReadingEvidence, plane_readings: Mapping[str, list[str]], limit: int = 4) -> None:
        super().__init__(evidence)
        self._bounded = BoundedReadings(evidence)
        self._planes = plane_readings
        self._limit = limit

    def readings(self, text: str) -> tuple[tuple[str, ...], ...] | None:
        bounded = self._bounded.readings(text)
        if bounded:
            return bounded
        options = list(itertools.islice(itertools.product(*(self._planes.get(c, []) for c in text)), self._limit + 1))
        return tuple(options) if options and len(options) <= self._limit else None


# ---------------------------------------------------------------- candidate statistics


@dataclass
class GramStats:
    """一個 n-gram 的所有過濾與先驗依據；counts 為 train split 的精確出現次數。"""

    text: str
    pooled_frequency: float
    pooled_pmi: float
    fragment_share: float
    count: int = 0
    documents: int = 0
    sources: int = 0
    daily_documents: int = 0
    numeral_adjacent: int = 0
    by_slice: Counter[str] = field(default_factory=Counter)
    by_source: Counter[str] = field(default_factory=Counter)
    daily_frequency: float = 0.0
    daily_pmi: float = -math.inf
    daily_fragment_share: float = 0.0
    interpolated_frequency: float = 0.0

    @property
    def numeral_share(self) -> float:
        return self.numeral_adjacent / self.count if self.count else 0.0

    def domain_concentration(self, totals: Mapping[str, int]) -> tuple[str, float]:
        rates = {s: self.by_slice.get(s, 0) / t for s, t in totals.items() if t}
        total = sum(rates.values())
        if not total:
            return "", 0.0
        top = max(sorted(rates), key=lambda s: rates[s])
        return top, rates[top] / total


class GramScanner:
    """只對候選 n-gram 做第二次掃描：精確次數、文件數、來源數、日常文件數與數字鄰接次數。"""

    def scan(self, sentences: Iterable[CorpusSentence], candidates: set[str]) -> dict[str, tuple[int, set[str], Counter[str], Counter[str], set[str], int]]:
        found: dict[str, list] = {}  # type: ignore[type-arg]
        sizes = sorted({len(c) for c in candidates})
        for sentence in sentences:
            text = sentence.text
            for start in range(len(text)):
                for n in sizes:
                    gram = text[start : start + n]
                    if len(gram) < n or gram not in candidates:
                        continue
                    row = found.setdefault(gram, [0, set(), Counter(), Counter(), set(), 0])
                    row[0] += 1
                    row[1].add(sentence.doc_key)
                    row[2][sentence.slice_name] += 1
                    row[3][sentence.source_id] += 1
                    if sentence.slice_name == DAILY:
                        row[4].add(sentence.doc_key)
                    before = text[start - 1] if start else ""
                    after = text[start + n] if start + n < len(text) else ""
                    row[5] += before in NUMERALS or after in NUMERALS
        return {g: tuple(v) for g, v in found.items()}  # type: ignore[misc]


def extension_share(counts: Mapping[str, int]) -> dict[str, float]:
    best: dict[str, int] = {}
    for gram, count in counts.items():
        if len(gram) < 3:
            continue
        for child in (gram[1:], gram[:-1]):
            if count > best.get(child, 0):
                best[child] = count
    return {g: c / counts[g] for g, c in best.items() if counts.get(g)}


def pmi(gram: str, probability) -> float:  # type: ignore[no-untyped-def]
    joint = probability(gram)
    values = []
    for cut in range(1, len(gram)):
        left, right = probability(gram[:cut]), probability(gram[cut:])
        values.append(math.log2(joint / (left * right)) if joint and left and right else -math.inf)
    return min(values)


class CandidateStatistics:
    """事前固定的候選範圍：pooled ≥ 2/M 或日常計數 ≥ 3 的 2..4 字漢字 n-gram（排除 builtin 詞）。"""

    POOLED_MIN_PER_MILLION = 2.0
    DAILY_MIN_COUNT = 3
    INTERPOLATION_DAILY_WEIGHT = 0.25

    def __init__(self, tables: CorpusTables, sentences: Sequence[CorpusSentence], known: set[str]) -> None:
        self.tables = tables
        self.totals = {**{d: t.total for d, t in tables.gov.items()}, DAILY: tables.daily.total}
        pooled_share = extension_share({g: tables.pooled_count(g) for n in range(1, MAX_N + 1) for g in tables.grams(n)})
        daily_share = extension_share(tables.daily.counts)
        threshold = self.POOLED_MIN_PER_MILLION / 1e6
        candidates = {
            g
            for n in range(2, MAX_N + 1)
            for g in tables.grams(n)
            if g not in known
            and (tables.pooled_count(g) / tables.pooled_total >= threshold or tables.daily.counts.get(g, 0) >= self.DAILY_MIN_COUNT)
        }
        scanned = GramScanner().scan(sentences, candidates)
        pooled = lambda g: tables.pooled_count(g) / tables.pooled_total  # noqa: E731
        daily: NgramTable = tables.daily
        self.stats: dict[str, GramStats] = {}
        for gram in sorted(candidates):
            count, docs, by_slice, by_source, daily_docs, numeral = scanned.get(gram, (0, set(), Counter(), Counter(), set(), 0))
            self.stats[gram] = GramStats(
                text=gram,
                pooled_frequency=pooled(gram),
                pooled_pmi=pmi(gram, pooled),
                fragment_share=pooled_share.get(gram, 0.0) if len(gram) < MAX_N else 0.0,
                count=count,
                documents=len(docs),
                sources=len(by_source),
                daily_documents=len(daily_docs),
                numeral_adjacent=numeral,
                by_slice=by_slice,
                by_source=by_source,
                daily_frequency=daily.probability(gram),
                daily_pmi=pmi(gram, daily.probability),
                daily_fragment_share=daily_share.get(gram, 0.0) if len(gram) < MAX_N else 0.0,
                interpolated_frequency=self.INTERPOLATION_DAILY_WEIGHT * daily.probability(gram)
                + (1 - self.INTERPOLATION_DAILY_WEIGHT) * tables.gov_probability(gram),
            )


# ---------------------------------------------------------------- extraction filters


class ExtractionFilter(ABC):
    """回傳 None 表示通過，否則回傳排除原因。"""

    name: str

    @abstractmethod
    def reject(self, stats: GramStats, context: CandidateStatistics) -> str | None: ...


class MixedFilter(ExtractionFilter):
    """L1：政府 + 日常，pooled ≥ 2/M、文件數 ≥ 2、非片段。"""

    name = "L1_mixed"

    def reject(self, stats: GramStats, context: CandidateStatistics) -> str | None:
        if stats.pooled_frequency < context.POOLED_MIN_PER_MILLION / 1e6:
            return "below_pooled_frequency"
        if stats.documents < 2:
            return "too_few_documents"
        if stats.fragment_share >= FRAGMENT_SHARE:
            return "fragment_of_longer_ngram"
        return None


class DailyOnlyFilter(ExtractionFilter):
    """L2：只看日常語料：日常次數 ≥ 3、日常文件 ≥ 3、日常 PMI ≥ 3、日常計數下非片段。"""

    name = "L2_daily_only"

    def reject(self, stats: GramStats, context: CandidateStatistics) -> str | None:
        if context.tables.daily.counts.get(stats.text, 0) < context.DAILY_MIN_COUNT:
            return "below_daily_count"
        if stats.daily_documents < 3:
            return "too_few_daily_documents"
        if stats.daily_pmi < 3.0:
            return "low_daily_pmi"
        if stats.daily_fragment_share >= FRAGMENT_SHARE:
            return "fragment_of_longer_ngram"
        return None


class DailySupportedFilter(MixedFilter):
    """L3：L1 且至少出現在 2 份日常文件。"""

    name = "L3_daily_supported"

    def reject(self, stats: GramStats, context: CandidateStatistics) -> str | None:
        return super().reject(stats, context) or ("no_daily_support" if stats.daily_documents < 2 else None)


class DomainRatioFilter(MixedFilter):
    """L4：L1 再排除集中於單一政府領域（正規化比率 ≥ 0.8）或與數字相鄰比例 ≥ 0.5 的 n-gram。"""

    name = "L4_domain_ratio"

    def reject(self, stats: GramStats, context: CandidateStatistics) -> str | None:
        reason = super().reject(stats, context)
        if reason:
            return reason
        top, share = stats.domain_concentration(context.totals)
        if top != DAILY and share >= 0.8:
            return "government_domain_concentrated"
        if stats.numeral_share >= 0.5:
            return "numeral_template"
        return None


class DocumentFrequencyFilter(MixedFilter):
    """L5：L1 且文件數 ≥ 5、獨立來源 ≥ 3。"""

    name = "L5_doc_frequency"

    def reject(self, stats: GramStats, context: CandidateStatistics) -> str | None:
        reason = super().reject(stats, context)
        if reason:
            return reason
        if stats.documents < 5:
            return "too_few_documents"
        if stats.sources < 3:
            return "too_few_sources"
        return None


# ---------------------------------------------------------------- lexical priors


def clip(value: float) -> float:
    low, high = WEIGHT_BOUNDS
    return min(high, max(low, value))


class LexicalPrior(ABC):
    name: str

    @abstractmethod
    def weights(self, stats: Sequence[GramStats]) -> list[float]: ...


class FlatPrior(LexicalPrior):
    name = "flat"

    def weights(self, stats: Sequence[GramStats]) -> list[float]:
        return [MEDIAN_WEIGHT] * len(stats)


class RatioPrior(LexicalPrior):
    """w = 10 · x / median(x)；x 由子類別決定。"""

    def value(self, stats: GramStats) -> float:
        return stats.pooled_frequency

    def weights(self, stats: Sequence[GramStats]) -> list[float]:
        values = [self.value(s) for s in stats]
        positive = [v for v in values if v > 0]
        median = statistics.median(positive) if positive else 1.0
        return [clip(MEDIAN_WEIGHT * v / median) if v > 0 else WEIGHT_BOUNDS[0] for v in values]


class RawPrior(RatioPrior):
    name = "raw"


class DocumentPrior(RatioPrior):
    name = "doc"

    def value(self, stats: GramStats) -> float:
        return float(stats.documents)


class DailyOnlyPrior(RatioPrior):
    name = "daily_only"

    def value(self, stats: GramStats) -> float:
        return stats.daily_frequency


class InterpolatedPrior(RatioPrior):
    name = "interpolated"

    def value(self, stats: GramStats) -> float:
        return stats.interpolated_frequency


class LogPrior(LexicalPrior):
    name = "log"

    def weights(self, stats: Sequence[GramStats]) -> list[float]:
        median = statistics.median(s.pooled_frequency for s in stats) if stats else 1.0
        return [clip(MEDIAN_WEIGHT * (1 + math.log10(s.pooled_frequency / median))) if s.pooled_frequency > 0 else WEIGHT_BOUNDS[0] for s in stats]


class RankBucketPrior(LexicalPrior):
    """依 pooled 頻率排名：前 10% → 50、接著 20% → 20、接著 40% → 10、最後 30% → 3。"""

    name = "rank_bucket"
    BUCKETS = ((0.1, 50.0), (0.3, 20.0), (0.7, 10.0), (1.0, 3.0))

    def weights(self, stats: Sequence[GramStats]) -> list[float]:
        order = sorted(range(len(stats)), key=lambda i: (-stats[i].pooled_frequency, stats[i].text))
        out = [0.0] * len(stats)
        for rank, index in enumerate(order):
            share = (rank + 1) / len(stats)
            out[index] = next(w for limit, w in self.BUCKETS if share <= limit + 1e-12)
        return out


PRIORS: tuple[type[LexicalPrior], ...] = (FlatPrior, RawPrior, LogPrior, DocumentPrior, DailyOnlyPrior, InterpolatedPrior, RankBucketPrior)
FILTERS: tuple[type[ExtractionFilter], ...] = (MixedFilter, DailyOnlyFilter, DailySupportedFilter, DomainRatioFilter, DocumentFrequencyFilter)


# ---------------------------------------------------------------- recipe


@dataclass(frozen=True)
class LexiconRecipe:
    reading: ReadingPolicy
    extraction: ExtractionFilter
    prior: LexicalPrior

    @property
    def name(self) -> str:
        return f"{self.reading.name}|{self.extraction.name}|{self.prior.name}"


@dataclass(frozen=True)
class RecipeResult:
    entries: tuple[DerivedLexiconEntry, ...]
    rejected: Mapping[str, int]


class CleanLexiconFactory:
    """同一份候選統計，依 recipe 決定哪些詞可收、讀音與權重；輸出依文字排序，完全 deterministic。"""

    def __init__(self, context: CandidateStatistics, gov_slices: set[str]) -> None:
        self._context = context
        self._gov = gov_slices

    def build(self, recipe: LexiconRecipe) -> RecipeResult:
        rejected: Counter[str] = Counter()
        kept: list[tuple[GramStats, tuple[tuple[str, ...], ...]]] = []
        for gram, stats in sorted(self._context.stats.items()):
            reason = recipe.extraction.reject(stats, self._context)
            if reason is None:
                readings = recipe.reading.readings(gram)
                reason = None if readings else "readings_unresolved"
            if reason is not None:
                rejected[reason] += 1
                continue
            kept.append((stats, readings))  # type: ignore[arg-type]
        weights = recipe.prior.weights([s for s, _ in kept])
        entries = []
        for (stats, readings), weight in zip(kept, weights):
            government = sum(c for s, c in stats.by_slice.items() if s in self._gov)
            entries.append(
                DerivedLexiconEntry(
                    text=stats.text,
                    readings=readings,
                    corpus_count=stats.count,
                    document_count=stats.documents,
                    daily_count=stats.count - government,
                    government_count=government,
                    domain_distribution=dict(sorted(stats.by_slice.items())),
                    pmi=round(stats.pooled_pmi, 4),
                    estimated_frequency=round(stats.pooled_frequency * 1e6, 4),
                    weight=round(weight, 4),
                    source_ids=tuple(sorted(stats.by_source)),
                    provenance=recipe.name,
                    eligibility="eligible",
                )
            )
        return RecipeResult(tuple(entries), dict(sorted(rejected.items())))


def false_competitors(entries: Sequence[DerivedLexiconEntry], supported: ReadingPolicy, base_lexicon: object) -> dict[str, int]:
    """讀音不受 `supported` 證據支持、且與另一個同長度詞同音的衍生（詞, 讀音）數。"""
    by_reading: dict[tuple[str, ...], set[str]] = {}
    for entry in entries:
        for reading in entry.readings:
            by_reading.setdefault(reading, set()).add(entry.text)
    unsupported = competing = 0
    for entry in entries:
        evidence = supported.readings(entry.text) or ()
        for reading in entry.readings:
            if reading in evidence:
                continue
            unsupported += 1
            rivals = {e.text for e in base_lexicon.lookup(reading) if len(e.text) == len(entry.text)} | by_reading[reading]  # type: ignore[attr-defined]
            competing += bool(rivals - {entry.text})
    return {"unsupported_readings": unsupported, "false_competitors": competing}
