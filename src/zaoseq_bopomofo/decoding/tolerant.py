"""TolerantDecoder：先照原輸入解碼，只有在結果很差或沒有候選時才展開讀音修正。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from zaoseq_bopomofo.decoding.candidate import Candidate, CandidateKind
from zaoseq_bopomofo.decoding.correction import ReadingCorrection
from zaoseq_bopomofo.decoding.errors import ReadingErrorModel
from zaoseq_bopomofo.decoding.lattice import DecodedSequence, LatticeDecoder


class ExpansionReason(Enum):
    # 沒有展開修正：exact 結果品質足夠，或政策停用修正。
    NOT_EXPANDED = "not_expanded"
    NO_EXACT_CANDIDATE = "no_exact_candidate"
    LOW_EXACT_QUALITY = "low_exact_quality"


@dataclass(frozen=True)
class TolerancePolicy:
    """`quality_threshold`：exact 最佳候選的每字 corpus log10 分數低於此值才展開修正（事前選定）。
    -4.0 約等於平均每字機率低於萬分之一，正常文字很少到這麼低；沒有語料模型時只在沒有 exact 候選時展開。"""

    enabled: bool = True
    quality_threshold: float = -4.0
    include_transposition: bool = True
    max_candidates: int = 20


@dataclass(frozen=True)
class DecodeOutcome:
    candidates: tuple[Candidate, ...]
    reason: ExpansionReason
    exact_count: int


class TolerantDecoder:
    def __init__(
        self,
        decoder: LatticeDecoder,
        error_model: ReadingErrorModel | None,
        policy: TolerancePolicy | None = None,
        has_language_model: bool = True,
    ) -> None:
        self._decoder = decoder
        self._errors = error_model
        self._policy = policy or TolerancePolicy()
        self._has_lm = has_language_model

    @property
    def policy(self) -> TolerancePolicy:
        return self._policy

    def candidates_for(self, readings: tuple[str, ...], left_context: str = "") -> tuple[Candidate, ...]:
        return self.decode(readings, left_context).candidates

    def decode(self, readings: tuple[str, ...], left_context: str = "") -> DecodeOutcome:
        if not readings:
            return DecodeOutcome((), ExpansionReason.NOT_EXPANDED, 0)
        exact = self._decoder.decode(readings, left_context, max_edits=0)
        reason = self._expansion_reason(exact, len(readings))
        pool: list[DecodedSequence] = list(exact)
        if reason is not ExpansionReason.NOT_EXPANDED:
            pool.extend(s for s in self._decoder.decode(readings, left_context, max_edits=1) if s.edits)
            if self._policy.include_transposition:
                pool.extend(self._transpositions(readings, left_context))
        return DecodeOutcome(self._to_candidates(readings, pool), reason, len(exact))

    def _expansion_reason(self, exact: Sequence[DecodedSequence], length: int) -> ExpansionReason:
        if not self._policy.enabled or self._errors is None:
            return ExpansionReason.NOT_EXPANDED
        if not exact:
            return ExpansionReason.NO_EXACT_CANDIDATE
        best = exact[0].breakdown.corpus
        if self._has_lm and best is not None and best / length < self._policy.quality_threshold:
            return ExpansionReason.LOW_EXACT_QUALITY
        return ExpansionReason.NOT_EXPANDED

    def _transpositions(self, readings: tuple[str, ...], left_context: str) -> list[DecodedSequence]:
        assert self._errors is not None
        results: list[DecodedSequence] = []
        for position in range(len(readings) - 1):
            swapped = self._errors.transposition(readings, position)
            if swapped is None:
                continue
            first, second, edit = swapped
            variant = readings[:position] + (first, second) + readings[position + 2 :]
            for sequence in self._decoder.decode(variant, left_context, max_edits=0)[:3]:
                breakdown = type(sequence.breakdown)(
                    pronunciation=-edit.cost, lexical=sequence.breakdown.lexical, corpus=sequence.breakdown.corpus
                )
                results.append(
                    DecodedSequence(
                        text=sequence.text,
                        segments=sequence.segments,
                        inferred=sequence.inferred,
                        breakdown=breakdown,
                        total=self._decoder.scorer.total(breakdown),
                        edits=(edit,),
                    )
                )
        return results

    def _to_candidates(self, readings: tuple[str, ...], pool: Sequence[DecodedSequence]) -> tuple[Candidate, ...]:
        # 同一文字同時有 exact 與修正解讀時保留分數較高者；同分時 exact 優先（排序鍵含修正成本）。
        best: dict[str, DecodedSequence] = {}
        for sequence in pool:
            current = best.get(sequence.text)
            if current is None or _rank_key(sequence) < _rank_key(current):
                best[sequence.text] = sequence
        ordered = sorted(best.values(), key=_rank_key)[: self._policy.max_candidates]
        candidates = []
        for rank, sequence in enumerate(ordered):
            correction = None
            if sequence.edits:
                correction = ReadingCorrection(
                    original=readings,
                    inferred=sequence.inferred,
                    operations=sequence.edits,
                    cost=sum(e.cost for e in sequence.edits),
                )
            candidates.append(
                Candidate(
                    text=sequence.text,
                    readings=sequence.inferred,
                    baseline_score=sequence.total,
                    baseline_rank=rank,
                    kind=CandidateKind.WORD if len(sequence.segments) == 1 else CandidateKind.COMPOSITION,
                    segments=sequence.segments,
                    breakdown=sequence.breakdown,
                    correction=correction,
                )
            )
        return tuple(candidates)


def _rank_key(sequence: DecodedSequence) -> tuple[float, float, str]:
    return (-sequence.total, sum(e.cost for e in sequence.edits), sequence.text)
