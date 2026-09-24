"""FrequencyRanker：只看詞庫 unigram 分數的 baseline。"""

from __future__ import annotations

import time
from collections.abc import Sequence

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.ranking.base import (
    RankingContext,
    RankingResult,
    RankingStatus,
    elapsed_ms,
    order_by_scores,
    validate_candidates,
)


class FrequencyRanker:
    """baseline 也走 CandidateRanker 介面，讓 benchmark 與 UI 對所有 ranker 使用同一條路徑。

    對 CandidateGenerator 的輸出而言這是恆等排序；對外部提供的候選則依分數重排。
    """

    def __init__(self, name: str = "frequency") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str | None:
        return None

    def rank(self, context: RankingContext, candidates: Sequence[Candidate]) -> RankingResult:
        started = time.perf_counter()
        validate_candidates(candidates)
        if not candidates:
            return RankingResult(self._name, None, RankingStatus.EMPTY, (), elapsed_ms(started))
        scores = {c.candidate_id: c.baseline_score for c in candidates}
        return RankingResult(
            ranker=self._name,
            model=None,
            status=RankingStatus.OK,
            candidates=order_by_scores(candidates, scores),
            latency_ms=elapsed_ms(started),
        )
