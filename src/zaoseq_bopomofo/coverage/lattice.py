from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from zaoseq_bopomofo.corpus.statistics import initial_history
from zaoseq_bopomofo.decoding.candidate import Candidate, CandidateKind, Segment
from zaoseq_bopomofo.decoding.scoring import LinearScorer, ScoreBreakdown
from zaoseq_bopomofo.lexicon.entry import LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon

NEUTRAL = "˙"
TONES = ("ˊ", "ˇ", "ˋ", NEUTRAL)


@dataclass(frozen=True)
class GenerationConfig:
    name: str = "v0"
    beam: int = 48
    nbest: int = 20
    max_entries_per_span: int | None = None
    # 在 total 分數的 beam 之外，額外保留 lexical 分數最高的幾個假設（不受語料 LM 早期剪枝影響）。
    lexical_slots: int = 0
    # 查詢時把輕聲與本調視為互通（例如 ㄇㄚ˙ 找得到只登錄 ㄇㄚ 的字），不改變使用者輸入。
    tone_variant_lookup: bool = False
    # beam 剪枝只看 lexical 分數，最後排序仍用 total（診斷語料 prior 是否太早剪枝）。
    prune_by_lexical: bool = False

    def __post_init__(self) -> None:
        if min(self.beam, self.nbest) < 1 or self.lexical_slots < 0:
            raise ValueError("beam / nbest 必須 >= 1，lexical_slots >= 0")
        if self.max_entries_per_span is not None and self.max_entries_per_span < 1:
            raise ValueError("max_entries_per_span 必須 >= 1")


@dataclass(frozen=True)
class _Hyp:
    total: float
    corpus: float
    lexical: float
    text: str
    history: str
    segments: tuple[Segment, ...]


@dataclass
class Timing:
    lookup_s: float = 0.0
    lm_s: float = 0.0
    prune_s: float = 0.0
    finalize_s: float = 0.0


@dataclass
class Trace:
    """`generated[p]` / `kept[p]`：長度 p 的 gold 前綴是否被產生、是否留在第 p 步的 beam。
    `final_rank` 為 None 表示 gold 沒有出現在任何完整假設中（不是排在後面）。"""

    generated: list[bool] = field(default_factory=list)
    kept: list[bool] = field(default_factory=list)
    final_rank: int | None = None
    complete_hypotheses: int = 0

    @property
    def first_lost(self) -> int | None:
        for position, (made, kept) in enumerate(zip(self.generated, self.kept)):
            if made and not kept:
                return position
        return None


@dataclass(frozen=True)
class Generation:
    candidates: tuple[Candidate, ...]
    trace: Trace | None
    timing: Timing


def tone_variants(reading: str) -> tuple[str, ...]:
    """同一音節主體的輕聲 / 本調寫法（不含其他聲調）。"""
    if reading.endswith(NEUTRAL):
        body = reading[: -len(NEUTRAL)]
        return (body,) + tuple(body + t for t in ("ˊ", "ˇ", "ˋ"))
    body = reading[:-1] if reading.endswith(("ˊ", "ˇ", "ˋ")) else reading
    return (body + NEUTRAL,)


class CoverageLattice:
    """與 frozen LatticeDecoder（exact）演算法相同；`GenerationConfig()` 即 V0 設定。"""

    def __init__(
        self,
        lexicon: Lexicon,
        language_model: object | None,
        scorer: LinearScorer,
        config: GenerationConfig | None = None,
    ) -> None:
        self._lexicon = lexicon
        self._lm = language_model
        self._scorer = scorer
        self.config = config or GenerationConfig()

    def _lookup(self, span: tuple[str, ...]) -> Sequence[LexiconEntry]:
        entries = list(self._lexicon.lookup(span))
        if self.config.tone_variant_lookup:
            seen = {e.text for e in entries}
            for index, reading in enumerate(span):
                for variant in tone_variants(reading):
                    alt = span[:index] + (variant,) + span[index + 1 :]
                    for entry in self._lexicon.lookup(alt):
                        if entry.text not in seen:
                            seen.add(entry.text)
                            entries.append(entry)
        if self.config.max_entries_per_span is not None:
            entries = entries[: self.config.max_entries_per_span]
        return entries

    def generate(
        self,
        readings: Sequence[str],
        left_context: str = "",
        gold_keys: Callable[[str], bool] | None = None,
        gold_prefix: Callable[[int, Iterable[str]], bool] | None = None,
        timed: bool = False,
    ) -> Generation:
        cfg = self.config
        timing = Timing()
        clock = time.perf_counter if timed else (lambda: 0.0)
        observed = tuple(readings)
        n = len(observed)
        trace = Trace() if gold_prefix is not None else None
        if n == 0:
            return Generation((), trace, timing)
        start = _Hyp(0.0, 0.0, 0.0, "", initial_history(left_context) if self._lm else "", ())
        beams: list[dict[str, _Hyp]] = [dict() for _ in range(n + 1)]
        beams[0][""] = start
        max_len = max(1, self._lexicon.max_word_length)
        prune_key = (lambda h: (-h.lexical, h.text)) if cfg.prune_by_lexical else (lambda h: (-h.total, h.text))

        for position in range(n):
            t0 = clock()
            pool = beams[position].values()
            frontier = sorted(pool, key=prune_key)[: cfg.beam]
            if cfg.lexical_slots:
                chosen = {h.text for h in frontier}
                extra = sorted((h for h in pool if h.text not in chosen), key=lambda h: (-h.lexical, h.text))
                frontier += extra[: cfg.lexical_slots]
            timing.prune_s += clock() - t0
            if trace is not None:
                trace.generated.append(gold_prefix(position, beams[position].keys()))  # type: ignore[misc]
                trace.kept.append(gold_prefix(position, (h.text for h in frontier)))  # type: ignore[misc]
            for hypothesis in frontier:
                for length in range(1, min(max_len, n - position) + 1):
                    span = observed[position : position + length]
                    t1 = clock()
                    entries = self._lookup(span)
                    timing.lookup_s += clock() - t1
                    self._extend(beams[position + length], hypothesis, span, entries, timing, clock)

        t2 = clock()
        ordered = sorted(beams[n].values(), key=lambda h: (-h.total, h.text))
        finals = ordered[: cfg.nbest]
        candidates = tuple(
            Candidate(
                text=h.text,
                readings=observed,
                baseline_score=h.total,
                baseline_rank=rank,
                kind=CandidateKind.WORD if len(h.segments) == 1 else CandidateKind.COMPOSITION,
                segments=h.segments,
                breakdown=ScoreBreakdown(0.0, h.lexical, h.corpus if self._lm is not None else None),
            )
            for rank, h in enumerate(finals)
        )
        timing.finalize_s += clock() - t2
        if trace is not None:
            trace.complete_hypotheses = len(ordered)
            trace.generated.append(gold_prefix(n, beams[n].keys()))  # type: ignore[misc]
            trace.kept.append(trace.generated[-1])
            if gold_keys is not None:
                trace.final_rank = next((i for i, h in enumerate(ordered) if gold_keys(h.text)), None)
        return Generation(candidates, trace, timing)

    def _extend(
        self,
        target: dict[str, _Hyp],
        hypothesis: _Hyp,
        span: tuple[str, ...],
        entries: Sequence[LexiconEntry],
        timing: Timing,
        clock: Callable[[], float],
    ) -> None:
        for entry in entries:
            corpus = hypothesis.corpus
            history = hypothesis.history
            if self._lm is not None:
                t = clock()
                for char in entry.text:
                    delta, history = self._lm.extend(history, char)  # type: ignore[attr-defined]
                    corpus += delta
                timing.lm_s += clock() - t
            lexical = hypothesis.lexical + self._lexicon.log10_probability(entry)
            text = hypothesis.text + entry.text
            breakdown = ScoreBreakdown(-0.0, lexical, corpus if self._lm is not None else None)
            candidate = _Hyp(
                total=self._scorer.total(breakdown),
                corpus=corpus,
                lexical=lexical,
                text=text,
                history=history,
                segments=hypothesis.segments + (Segment(entry.text, span),),
            )
            existing = target.get(text)
            if existing is None or (candidate.total, candidate.text) > (existing.total, existing.text):
                target[text] = candidate


def reachable(lexicon: Lexicon, readings: Sequence[str], accepts: Callable[[int, int, str], bool], tone_variant_lookup: bool = False) -> bool:
    """gold 是否能由詞庫詞條完整拼出（不受 beam 限制）。`accepts(i, j, text)` 判斷 text 是否等於 gold[i:j]。"""
    n = len(readings)
    ok = [False] * (n + 1)
    ok[0] = True
    probe = CoverageLattice(lexicon, None, LinearScorer(), GenerationConfig(tone_variant_lookup=tone_variant_lookup))
    for i in range(n):
        if not ok[i]:
            continue
        for j in range(i + 1, min(n, i + lexicon.max_word_length) + 1):
            if any(accepts(i, j, e.text) for e in probe._lookup(tuple(readings[i:j]))):  # noqa: SLF001
                ok[j] = True
    return ok[n]
