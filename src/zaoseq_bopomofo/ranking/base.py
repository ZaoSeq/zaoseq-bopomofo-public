"""排序介面與共用型別。"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.ranking.signal import ContextConfidence, ContextSignal


@dataclass(frozen=True)
class RankingContext:
    """`left_context` 是使用者已確認送出的文字，可以為空字串。"""

    left_context: str
    readings: tuple[str, ...]


@dataclass(frozen=True)
class RankedCandidate:
    """`score` 只在同一個 ranker 內可比較。

    `score is None` 表示這個 ranker 沒有替它評分（例如在模型 top-k 視窗外），
    `contextual_probability is None` 表示模型沒有評估它；兩者都不等於 0。
    """

    candidate: Candidate
    score: float | None
    contextual_probability: float | None = None
    # 同一 semantic family（例如台北／臺北）的非代表成員沿用代表的 contextual 機率，
    # 但不參與 confidence 計算，否則重複的機率會讓 margin 看起來是 0。
    family_representative: bool = True


class RankingStatus(Enum):
    OK = "ok"
    # 沒有取得 contextual 訊號，結果與 baseline 順序完全相同。
    FALLBACK = "fallback"
    # 候選集合為空，沒有任何決策可做。
    EMPTY = "empty"


class FallbackReason(Enum):
    TIMEOUT = "timeout"
    BACKEND_ERROR = "backend_error"
    UNAVAILABLE = "unavailable"
    UNKNOWN_CANDIDATE = "unknown_candidate"
    INVALID_PROBABILITY = "invalid_probability"
    EMPTY_RESPONSE = "empty_response"

    @property
    def is_invalid_response(self) -> bool:
        """模型有回應但內容不可用；與 timeout、例外、未載入分開統計。"""
        return self in (
            FallbackReason.UNKNOWN_CANDIDATE,
            FallbackReason.INVALID_PROBABILITY,
            FallbackReason.EMPTY_RESPONSE,
        )


@dataclass(frozen=True)
class FallbackInfo:
    reason: FallbackReason
    detail: str


@dataclass(frozen=True)
class RankingResult:
    """`latency_ms` 是整個 rank() 的時間；`model_latency_ms` 只含 contextual backend 呼叫，
    沒有呼叫模型時為 None。`signal` 是 backend 的成本與穩定度，`context_confidence` 只有做了
    confidence gating 的 ranker 才會填。"""

    ranker: str
    model: str | None
    status: RankingStatus
    candidates: tuple[RankedCandidate, ...]
    latency_ms: float
    confidence: float | None = None
    fallback: FallbackInfo | None = None
    notes: tuple[str, ...] = ()
    model_latency_ms: float | None = None
    signal: ContextSignal | None = None
    context_confidence: ContextConfidence | None = None

    def __post_init__(self) -> None:
        if (self.status is RankingStatus.FALLBACK) != (self.fallback is not None):
            raise ValueError("fallback 資訊必須且只能出現在 FALLBACK 狀態")
        if self.status is RankingStatus.EMPTY and self.candidates:
            raise ValueError("EMPTY 狀態不可包含候選")

    def texts(self) -> tuple[str, ...]:
        return tuple(rc.candidate.text for rc in self.candidates)


@runtime_checkable
class CandidateRanker(Protocol):
    """只負責重新排列已有候選，不得生成候選集合外的新文字。

    模型層的任何失敗都必須以 FALLBACK 結果回傳而不是丟例外，
    輸入法主流程因此永遠拿得到可用的順序。
    """

    @property
    def name(self) -> str: ...

    @property
    def model_name(self) -> str | None: ...

    def rank(self, context: RankingContext, candidates: Sequence[Candidate]) -> RankingResult: ...


def validate_candidates(candidates: Sequence[Candidate]) -> None:
    """tiebreak 與 fallback 都假設 baseline_rank 等於位置；不成立代表呼叫端的程式錯誤。"""
    texts: set[str] = set()
    for position, candidate in enumerate(candidates):
        if candidate.baseline_rank != position:
            raise ValueError(f"{candidate.text!r} 的 baseline_rank={candidate.baseline_rank} 與位置 {position} 不符")
        if candidate.text in texts:
            raise ValueError(f"候選文字重複：{candidate.text!r}")
        texts.add(candidate.text)


def baseline_ranked(candidates: Sequence[Candidate]) -> tuple[RankedCandidate, ...]:
    return tuple(RankedCandidate(candidate=c, score=c.baseline_score) for c in candidates)


def order_by_scores(
    candidates: Sequence[Candidate],
    scores: Mapping[str, float],
    probabilities: Mapping[str, float] | None = None,
    base_position: Mapping[str, int] | None = None,
) -> tuple[RankedCandidate, ...]:
    """依 `scores`（以 candidate_id 為 key）排序，其餘候選依 baseline 順序接在後面。

    同分時依 `base_position`（預設為 baseline_rank）決定，不依賴 dict 迭代順序。
    """
    for key, value in scores.items():
        if not math.isfinite(value):
            raise ValueError(f"{key} 的分數不是有限數值：{value!r}")
    position = base_position or {c.candidate_id: c.baseline_rank for c in candidates}
    scored = sorted(
        (c for c in candidates if c.candidate_id in scores),
        key=lambda c: (-scores[c.candidate_id], position[c.candidate_id]),
    )
    rest = sorted(
        (c for c in candidates if c.candidate_id not in scores),
        key=lambda c: position[c.candidate_id],
    )
    probs = probabilities or {}
    return tuple(
        RankedCandidate(candidate=c, score=scores[c.candidate_id], contextual_probability=probs.get(c.candidate_id))
        for c in scored
    ) + tuple(RankedCandidate(candidate=c, score=None) for c in rest)


def elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0
