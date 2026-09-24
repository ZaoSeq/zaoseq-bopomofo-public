"""以語料語言模型與詞庫做 beam search 的讀音解碼器，可選擇允許有限的讀音修正。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from zaoseq_bopomofo.corpus.domains import LanguageModel
from zaoseq_bopomofo.corpus.statistics import initial_history
from zaoseq_bopomofo.decoding.candidate import Segment
from zaoseq_bopomofo.decoding.correction import ReadingEdit
from zaoseq_bopomofo.decoding.errors import ReadingErrorModel
from zaoseq_bopomofo.decoding.scoring import LinearScorer, ScoreBreakdown, SequenceScorer
from zaoseq_bopomofo.lexicon.entry import LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon


@dataclass(frozen=True)
class LatticeConfig:
    """`beam`：每個讀音位置保留的部分假設數。
    `edit_entries_per_span`：修正路徑每個 span 只展開詞庫排序前幾名，控制候選空間；
    正常路徑不設上限，讓語料模型決定所有同音字。"""

    beam: int = 48
    nbest: int = 20
    edit_entries_per_span: int = 8
    max_alternatives_per_syllable: int = 24

    def __post_init__(self) -> None:
        if min(self.beam, self.nbest, self.edit_entries_per_span, self.max_alternatives_per_syllable) < 1:
            raise ValueError("LatticeConfig 的數值必須 >= 1")


@dataclass(frozen=True)
class DecodedSequence:
    text: str
    segments: tuple[Segment, ...]
    inferred: tuple[str, ...]
    breakdown: ScoreBreakdown
    total: float
    edits: tuple[ReadingEdit, ...]


@dataclass(frozen=True)
class _Hypothesis:
    total: float
    corpus: float
    lexical: float
    edit_cost: float
    text: str
    history: str
    segments: tuple[Segment, ...]
    inferred: tuple[str, ...]
    edits: tuple[ReadingEdit, ...]


class LatticeDecoder:
    def __init__(
        self,
        lexicon: Lexicon,
        language_model: LanguageModel | None,
        scorer: SequenceScorer | None = None,
        error_model: ReadingErrorModel | None = None,
        config: LatticeConfig | None = None,
    ) -> None:
        self._lexicon = lexicon
        self._lm = language_model
        self._scorer = scorer or LinearScorer(lexical_weight=0.0 if language_model else 1.0)
        self._errors = error_model
        self._config = config or LatticeConfig()

    @property
    def scorer(self) -> SequenceScorer:
        return self._scorer

    def decode(
        self,
        readings: Sequence[str],
        left_context: str = "",
        max_edits: int = 0,
    ) -> tuple[DecodedSequence, ...]:
        """回傳依總分排序的 N-best；讀音無法完整覆蓋時回傳空 tuple。

        `max_edits` 目前只支援 0 或 1：更大的 edit distance 會讓候選空間爆炸，預設禁止。
        """
        if max_edits not in (0, 1):
            raise ValueError("max_edits 只能是 0 或 1")
        if max_edits and self._errors is None:
            raise ValueError("允許修正時必須提供 ReadingErrorModel")
        observed = tuple(readings)
        n = len(observed)
        if n == 0:
            return ()
        history = initial_history(left_context) if self._lm else ""
        start = _Hypothesis(0.0, 0.0, 0.0, 0.0, "", history, (), (), ())
        beams: list[dict[str, _Hypothesis]] = [dict() for _ in range(n + 1)]
        beams[0][""] = start
        max_len = max(1, self._lexicon.max_word_length)

        for position in range(n):
            frontier = sorted(beams[position].values(), key=lambda h: (-h.total, h.text))[: self._config.beam]
            for hypothesis in frontier:
                for length in range(1, min(max_len, n - position) + 1):
                    span = observed[position : position + length]
                    self._extend(beams[position + length], hypothesis, span, self._lexicon.lookup(span), (), None)
                    if max_edits and not hypothesis.edits:
                        self._extend_with_edits(beams[position + length], hypothesis, position, span)

        finals = sorted(beams[n].values(), key=lambda h: (-h.total, h.text))[: self._config.nbest]
        return tuple(
            DecodedSequence(
                text=h.text,
                segments=h.segments,
                inferred=h.inferred,
                breakdown=self._breakdown(h),
                total=h.total,
                edits=h.edits,
            )
            for h in finals
        )

    def _extend_with_edits(
        self, target: dict[str, _Hypothesis], hypothesis: _Hypothesis, position: int, span: tuple[str, ...]
    ) -> None:
        assert self._errors is not None
        for offset, observed in enumerate(span):
            alternatives = self._errors.alternatives(observed, position + offset)
            for alternative in alternatives[: self._config.max_alternatives_per_syllable]:
                variant = span[:offset] + (alternative.reading,) + span[offset + 1 :]
                entries = self._lexicon.lookup(variant)[: self._config.edit_entries_per_span]
                self._extend(target, hypothesis, variant, entries, (alternative.edit,), alternative.edit.cost)

    def _extend(
        self,
        target: dict[str, _Hypothesis],
        hypothesis: _Hypothesis,
        span: tuple[str, ...],
        entries: Sequence[LexiconEntry],
        edits: tuple[ReadingEdit, ...],
        edit_cost: float | None,
    ) -> None:
        for entry in entries:
            corpus = hypothesis.corpus
            history = hypothesis.history
            if self._lm is not None:
                for char in entry.text:
                    delta, history = self._lm.extend(history, char)
                    corpus += delta
            lexical = hypothesis.lexical + self._lexicon.log10_probability(entry)
            cost = hypothesis.edit_cost + (edit_cost or 0.0)
            text = hypothesis.text + entry.text
            breakdown = ScoreBreakdown(-cost, lexical, corpus if self._lm is not None else None)
            candidate = _Hypothesis(
                total=self._scorer.total(breakdown),
                corpus=corpus,
                lexical=lexical,
                edit_cost=cost,
                text=text,
                history=history,
                segments=hypothesis.segments + (Segment(entry.text, span),),
                inferred=hypothesis.inferred + span,
                edits=hypothesis.edits + edits,
            )
            # 同一段文字只保留分數最高的一種分段與讀音解讀，避免 N-best 被重複文字塞滿。
            key = f"{text}\x00{len(candidate.edits)}"
            existing = target.get(key)
            if existing is None or (candidate.total, candidate.text) > (existing.total, existing.text):
                target[key] = candidate

    def _breakdown(self, hypothesis: _Hypothesis) -> ScoreBreakdown:
        return ScoreBreakdown(
            pronunciation=-hypothesis.edit_cost,
            lexical=hypothesis.lexical,
            corpus=hypothesis.corpus if self._lm is not None else None,
        )
