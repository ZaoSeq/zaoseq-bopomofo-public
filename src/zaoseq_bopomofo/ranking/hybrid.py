"""Hybrid ranking：固定權重（對照組）與 confidence-aware（production）兩種。"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.ranking.base import (
    CandidateRanker,
    RankedCandidate,
    RankingContext,
    RankingResult,
    RankingStatus,
    elapsed_ms,
    order_by_scores,
    validate_candidates,
)
from zaoseq_bopomofo.ranking.confidence import ConfidenceConfig, assess_confidence


class HybridRanker:
    """固定權重版本，保留為對照組。final = (1 - w) * p_baseline + w * p_contextual。

    contextual 視窗取 baseline ranker 排序的前 k 個 family；p_baseline 對全部候選正規化，視窗外的 p_contextual 為 0。

    用機率而非 log 空間相加：contextual 給 0 時 log 會變成 -inf，一個過度自信的
    zero-shot 判斷就能把 baseline 第一名壓到最後；線性混合下 baseline 仍保有 (1 - w) 的份量。
    contextual ranker fallback 時，結果與 baseline ranker 的輸出逐項相同。
    """

    def __init__(
        self,
        baseline_ranker: CandidateRanker,
        contextual_ranker: CandidateRanker,
        contextual_weight: float = 0.5,
        name: str = "hybrid",
    ) -> None:
        if isinstance(contextual_weight, bool) or not isinstance(contextual_weight, (int, float)):
            raise TypeError("contextual_weight 必須是數值")
        if not math.isfinite(contextual_weight) or not 0.0 <= contextual_weight <= 1.0:
            raise ValueError(f"contextual_weight 必須介於 [0, 1]：{contextual_weight!r}")
        self._baseline = baseline_ranker
        self._contextual = contextual_ranker
        self._weight = float(contextual_weight)
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str | None:
        return self._contextual.model_name

    @property
    def contextual_weight(self) -> float:
        return self._weight

    def rank(self, context: RankingContext, candidates: Sequence[Candidate]) -> RankingResult:
        started = time.perf_counter()
        validate_candidates(candidates)
        base = self._baseline.rank(context, candidates)
        if base.status is RankingStatus.EMPTY:
            return RankingResult(self._name, self.model_name, RankingStatus.EMPTY, (), elapsed_ms(started))
        if self._weight == 0.0:
            # w = 0 時 contextual 不可能影響結果，不呼叫模型，也不會因模型逾時而變慢。
            return self._as_baseline(base, started, notes=("contextual_weight=0: 未呼叫模型",))

        contextual = _contextual_on_baseline(self._contextual, context, base)
        if contextual.result.fallback is not None:
            return _fallback(self._name, self.model_name, base, contextual.result, started)
        if not contextual.probabilities:
            return self._as_baseline(base, started, notes=contextual.result.notes)
        return RankingResult(
            ranker=self._name,
            model=contextual.result.model,
            status=RankingStatus.OK,
            candidates=_mix(base, contextual.probabilities, self._weight),
            latency_ms=elapsed_ms(started),
            confidence=contextual.result.confidence,
            notes=contextual.result.notes,
            model_latency_ms=contextual.result.model_latency_ms,
            signal=contextual.result.signal,
        )

    def _as_baseline(self, base: RankingResult, started: float, notes: tuple[str, ...]) -> RankingResult:
        return RankingResult(
            ranker=self._name,
            model=self.model_name,
            status=RankingStatus.OK,
            candidates=base.candidates,
            latency_ms=elapsed_ms(started),
            notes=notes,
        )


@dataclass(frozen=True)
class _Contextual:
    result: RankingResult
    # 以原始 candidate_id 為 key；只含 contextual 視窗內的候選。
    probabilities: dict[str, float]
    representatives: dict[str, float]


def _contextual_on_baseline(ranker: CandidateRanker, context: RankingContext, base: RankingResult) -> _Contextual:
    """以 baseline ranker 的順序呼叫 contextual ranker，讓模型視窗等於 baseline 的前 k 個 family。

    candidate_id 由 baseline_rank 決定，重排後的 id 與原始 id 不同，結果要換回原始 id。
    """
    ordered = [replace(rc.candidate, baseline_rank=i) for i, rc in enumerate(base.candidates)]
    original = {c.candidate_id: rc.candidate.candidate_id for c, rc in zip(ordered, base.candidates)}
    result = ranker.rank(context, ordered)
    probabilities: dict[str, float] = {}
    representatives: dict[str, float] = {}
    for rc in result.candidates:
        if rc.contextual_probability is None:
            continue
        cid = original[rc.candidate.candidate_id]
        probabilities[cid] = rc.contextual_probability
        if rc.family_representative:
            representatives[cid] = rc.contextual_probability
    return _Contextual(result, probabilities, representatives)


def _mix(base: RankingResult, p_contextual: dict[str, float], weight: float) -> tuple[RankedCandidate, ...]:
    """final = (1 - w) · p_baseline + w · p_contextual，對 baseline 的全部候選計算；視窗外的 p_contextual 為 0。

    p_baseline 對 baseline 分數單調，同分時依 baseline 位置，因此 w = 0 時結果與 baseline 逐項相同。
    """
    candidates = [rc.candidate for rc in base.candidates]
    p_baseline = _baseline_distribution(base)
    combined = {
        cid: (1.0 - weight) * p + weight * p_contextual.get(cid, 0.0) for cid, p in p_baseline.items()
    }
    base_position = {c.candidate_id: i for i, c in enumerate(candidates)}
    return order_by_scores(candidates, combined, p_contextual, base_position)


def _baseline_distribution(base: RankingResult) -> dict[str, float]:
    # 使用 baseline ranker 自己的分數（log10 尺度），而不是 candidate.baseline_score：
    # baseline 可能是 CorpusRanker，它的分數與 decoder 原始分數不同。
    # 先減最大值再取指數，避免低分候選 underflow 成 0。
    scores = {
        rc.candidate.candidate_id: (rc.score if rc.score is not None else rc.candidate.baseline_score)
        for rc in base.candidates
    }
    top = max(scores.values())
    weights = {cid: 10.0 ** (score - top) for cid, score in scores.items()}
    total = math.fsum(weights.values())
    return {cid: w / total for cid, w in weights.items()}


def _fallback(name: str, model: str | None, base: RankingResult, contextual: RankingResult, started: float) -> RankingResult:
    return RankingResult(
        ranker=name,
        model=model,
        status=RankingStatus.FALLBACK,
        candidates=base.candidates,
        latency_ms=elapsed_ms(started),
        fallback=contextual.fallback,
        notes=contextual.notes,
        model_latency_ms=contextual.model_latency_ms,
        signal=contextual.signal,
    )


class ConfidenceAwareHybridRanker:
    """造序注音的 production ranking。

    final = (1 - w_eff) * p_baseline + w_eff * p_contextual，其中 w_eff 由 ContextConfidence 決定：
    contextual 分佈平坦、第一二名差距小、或雙向比較不一致時，w_eff 趨近 0，結果退回 baseline。
    混合方式與 HybridRanker 相同；w_eff = 0 時輸出的候選物件與 baseline 逐項相同。
    gating 只代表「不確定時少干預」，不代表 confident 時一定正確。
    """

    def __init__(
        self,
        baseline_ranker: CandidateRanker,
        contextual_ranker: CandidateRanker,
        config: ConfidenceConfig | None = None,
        name: str = "hybrid-confidence",
    ) -> None:
        self._baseline = baseline_ranker
        self._contextual = contextual_ranker
        self._config = config or ConfidenceConfig()
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str | None:
        return self._contextual.model_name

    @property
    def config(self) -> ConfidenceConfig:
        return self._config

    def rank(self, context: RankingContext, candidates: Sequence[Candidate]) -> RankingResult:
        started = time.perf_counter()
        validate_candidates(candidates)
        base = self._baseline.rank(context, candidates)
        if base.status is RankingStatus.EMPTY:
            return RankingResult(self._name, self.model_name, RankingStatus.EMPTY, (), elapsed_ms(started))
        if self._config.max_weight == 0.0:
            return _baseline_copy(self._name, self.model_name, base, started, ("max_weight=0: 未呼叫模型",))

        contextual = _contextual_on_baseline(self._contextual, context, base)
        if contextual.result.fallback is not None:
            return _fallback(self._name, self.model_name, base, contextual.result, started)
        if not contextual.probabilities:
            return _baseline_copy(self._name, self.model_name, base, started, contextual.result.notes)

        confidence = assess_confidence(contextual.representatives, contextual.result.signal, self._config)
        weight = confidence.effective_weight
        # gate 為 0 時 contextual 不得影響任何位置：直接沿用 baseline 的候選物件，只附上診斷資料。
        ranked = base.candidates if weight == 0.0 else _mix(base, contextual.probabilities, weight)
        return RankingResult(
            ranker=self._name,
            model=contextual.result.model,
            status=RankingStatus.OK,
            candidates=ranked,
            latency_ms=elapsed_ms(started),
            notes=contextual.result.notes,
            model_latency_ms=contextual.result.model_latency_ms,
            signal=contextual.result.signal,
            context_confidence=confidence,
        )


def _baseline_copy(
    name: str, model: str | None, base: RankingResult, started: float, notes: tuple[str, ...]
) -> RankingResult:
    return RankingResult(name, model, RankingStatus.OK, base.candidates, elapsed_ms(started), notes=notes)
