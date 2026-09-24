"""Benchmark 指標，純函式。"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from zaoseq_bopomofo.ranking.base import FallbackReason, RankingStatus


@dataclass(frozen=True)
class CaseOutcome:
    """名次皆為 0-based，指「最前面的正確答案」的名次；答案必在候選中，所以一定有定義。

    `target_text` 是第一名候選中對應目標讀音的那一段（前 target_length 個字）。
    `model_latency_ms` 為 None 表示這個 ranker 沒有呼叫模型。
    `contextual_top_correct` / `context_confident` 為 None 表示沒有 contextual 分佈可評估；
    `forward_passes` 是這個 case 呼叫模型的 forward pass 次數（沒有呼叫為 0）。
    """

    case_id: str
    answer_rank: int
    baseline_answer_rank: int
    status: RankingStatus
    fallback_reason: FallbackReason | None
    latency_ms: float
    model_latency_ms: float | None
    top_text: str
    target_text: str
    target_correct: bool
    ambiguous_at_t0: bool
    tags: tuple[str, ...] = ()
    contextual_top_correct: bool | None = None
    context_confident: bool | None = None
    effective_weight: float | None = None
    forward_passes: int = 0
    questions: int = 0
    disagreement: float | None = None
    order_instability: float | None = None


@dataclass(frozen=True)
class LatencyStats:
    """線性內插百分位；沒有樣本時為 None，而不是 0。"""

    samples: int
    mean_ms: float | None
    p50_ms: float | None
    p95_ms: float | None


@dataclass(frozen=True)
class RankingSummary:
    """
    - regressions：baseline 第一名正確，ranker 之後不正確；improvements 反之。
    - unchanged：答案名次與 baseline 相同。fallback 的 case 依定義是 unchanged。
    - high_confidence_wrong：confidence gate 判定 confident，但 contextual 分佈的第一名是錯的。
    - low_confidence_correct：gate 判定不 confident，但 contextual 第一名其實是對的。
      兩者都只計算有 contextual 分佈的 case；confident 不代表正確。
    """

    cases: int
    top1_accuracy: float | None
    mrr: float | None
    regressions: int
    improvements: int
    unchanged: int
    fallback_count: int
    timeout_count: int
    invalid_response_count: int
    fallback_by_reason: dict[str, int]
    rerank_latency: LatencyStats
    model_latency: LatencyStats
    assessed_cases: int
    confident_cases: int
    high_confidence_wrong: int
    low_confidence_correct: int
    mean_effective_weight: float | None
    forward_passes: int
    questions: int
    mean_disagreement: float | None
    mean_order_instability: float | None


@dataclass(frozen=True)
class TemporalSummary:
    """同一個 ranker 在 t0（剛輸入目標讀音）與 t1（輸入後文後）對目標段的判斷。

    正確與否一律以使用者最終要的 target 判定，所以 t0 的「錯」包含資訊不足的 ambiguous case；
    這些 case 另外以 `*_ambiguous` 計數。
    correction_precision = wrong_to_correct / t1 目標段與 t0 第一名不同的 case 數；
    沒有任何改動時為 None。
    """

    paired_cases: int
    initial_top1_accuracy: float | None
    final_top1_accuracy: float | None
    final_sequence_top1: float | None
    wrong_to_correct: int
    correct_to_wrong: int
    unchanged_correct: int
    unchanged_wrong: int
    changed: int
    correction_precision: float | None
    wrong_to_correct_ambiguous: int
    initial_wrong_ambiguous: int


def percentile(values: Sequence[float], q: float) -> float | None:
    if not 0.0 <= q <= 100.0:
        raise ValueError("q 必須介於 [0, 100]")
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100.0
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_stats(values: Sequence[float]) -> LatencyStats:
    return LatencyStats(
        samples=len(values),
        mean_ms=math.fsum(values) / len(values) if values else None,
        p50_ms=percentile(values, 50.0),
        p95_ms=percentile(values, 95.0),
    )


def summarize(outcomes: Sequence[CaseOutcome]) -> RankingSummary:
    n = len(outcomes)
    reasons = [o.fallback_reason for o in outcomes if o.fallback_reason is not None]
    assessed = [o for o in outcomes if o.context_confident is not None]
    weights = [o.effective_weight for o in outcomes if o.effective_weight is not None]
    return RankingSummary(
        cases=n,
        top1_accuracy=sum(o.answer_rank == 0 for o in outcomes) / n if n else None,
        mrr=math.fsum(1.0 / (o.answer_rank + 1) for o in outcomes) / n if n else None,
        regressions=sum(o.baseline_answer_rank == 0 and o.answer_rank != 0 for o in outcomes),
        improvements=sum(o.baseline_answer_rank != 0 and o.answer_rank == 0 for o in outcomes),
        unchanged=sum(o.answer_rank == o.baseline_answer_rank for o in outcomes),
        fallback_count=sum(o.status is RankingStatus.FALLBACK for o in outcomes),
        timeout_count=sum(r is FallbackReason.TIMEOUT for r in reasons),
        invalid_response_count=sum(r.is_invalid_response for r in reasons),
        fallback_by_reason=dict(sorted(Counter(r.value for r in reasons).items())),
        rerank_latency=latency_stats([o.latency_ms for o in outcomes]),
        model_latency=latency_stats([o.model_latency_ms for o in outcomes if o.model_latency_ms is not None]),
        assessed_cases=len(assessed),
        confident_cases=sum(bool(o.context_confident) for o in assessed),
        high_confidence_wrong=sum(bool(o.context_confident) and o.contextual_top_correct is False for o in assessed),
        low_confidence_correct=sum(o.context_confident is False and bool(o.contextual_top_correct) for o in assessed),
        mean_effective_weight=math.fsum(weights) / len(weights) if weights else None,
        forward_passes=sum(o.forward_passes for o in outcomes),
        questions=sum(o.questions for o in outcomes),
        mean_disagreement=_mean([o.disagreement for o in outcomes]),
        mean_order_instability=_mean([o.order_instability for o in outcomes]),
    )


def _mean(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return math.fsum(present) / len(present) if present else None


def summarize_temporal(
    immediate: Mapping[str, CaseOutcome],
    composition: Sequence[CaseOutcome],
) -> TemporalSummary:
    """只計算兩種模式都有的情境。"""
    pairs = [(immediate[o.case_id], o) for o in composition if o.case_id in immediate]
    n = len(pairs)
    w2c = [(a, b) for a, b in pairs if not a.target_correct and b.target_correct]
    changed = sum(a.top_text != b.target_text for a, b in pairs)
    return TemporalSummary(
        paired_cases=n,
        initial_top1_accuracy=sum(a.target_correct for a, _ in pairs) / n if n else None,
        final_top1_accuracy=sum(b.target_correct for _, b in pairs) / n if n else None,
        final_sequence_top1=sum(b.answer_rank == 0 for _, b in pairs) / n if n else None,
        wrong_to_correct=len(w2c),
        correct_to_wrong=sum(a.target_correct and not b.target_correct for a, b in pairs),
        unchanged_correct=sum(a.target_correct and b.target_correct for a, b in pairs),
        unchanged_wrong=sum(not a.target_correct and not b.target_correct for a, b in pairs),
        changed=changed,
        correction_precision=len(w2c) / changed if changed else None,
        wrong_to_correct_ambiguous=sum(b.ambiguous_at_t0 for _, b in w2c),
        initial_wrong_ambiguous=sum(not a.target_correct and a.ambiguous_at_t0 for a, _ in pairs),
    )
