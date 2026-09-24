"""CorpusRanker：用語料語言模型重新評分既有候選（例如 benchmark 中固定的候選集合）。"""

from __future__ import annotations

import time
from collections.abc import Sequence

from zaoseq_bopomofo.corpus.domains import LanguageModel
from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.ranking.base import (
    RankingContext,
    RankingResult,
    RankingStatus,
    elapsed_ms,
    order_by_scores,
    validate_candidates,
)


class CorpusRanker:
    """score = corpus LM log10 P(text | left_context) + lexical_weight × candidate.baseline_score。

    這是 deterministic baseline，不是 contextual model：它只看字元 trigram，
    `lexical_weight` 預設 0，也就是完全不使用人工詞頻等級。
    """

    def __init__(self, language_model: LanguageModel, lexical_weight: float = 0.0, name: str = "corpus") -> None:
        if lexical_weight < 0:
            raise ValueError("lexical_weight 不可為負")
        self._lm = language_model
        self._lexical_weight = lexical_weight
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
        scores = {
            c.candidate_id: self._lm.score(c.text, context.left_context) + self._lexical_weight * c.baseline_score
            for c in candidates
        }
        return RankingResult(
            ranker=self._name,
            model=None,
            status=RankingStatus.OK,
            candidates=order_by_scores(candidates, scores),
            latency_ms=elapsed_ms(started),
        )
