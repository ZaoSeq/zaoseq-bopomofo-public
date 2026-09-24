"""gate = 0 時 Hybrid 必須與 baseline ranker 逐項相同（候選、family、寫法與最終文字）。"""

from __future__ import annotations

import random
import time
from collections.abc import Mapping, Sequence

import pytest

from conftest import CONTEXT, FakeBackend
from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.decoding.family import VariantTable, group_families
from zaoseq_bopomofo.ranking.base import (
    RankingContext,
    RankingResult,
    RankingStatus,
    elapsed_ms,
    order_by_scores,
)
from zaoseq_bopomofo.ranking.confidence import ConfidenceConfig
from zaoseq_bopomofo.ranking.contextual import ChoiceRequest, ContextualRanker
from zaoseq_bopomofo.ranking.hybrid import ConfidenceAwareHybridRanker, HybridRanker

VARIANTS = VariantTable.load()


class ScoreRanker:
    """依外部分數重排的 baseline，模擬 CorpusRanker：順序可以與 decoder 的 baseline_rank 不同。"""

    name = "score"
    model_name = None

    def __init__(self, scores: Mapping[str, float]) -> None:
        self._scores = scores

    def rank(self, context: RankingContext, candidates: Sequence[Candidate]) -> RankingResult:
        started = time.perf_counter()
        scores = {c.candidate_id: self._scores[c.text] for c in candidates}
        return RankingResult(self.name, None, RankingStatus.OK, order_by_scores(candidates, scores), elapsed_ms(started))


def _flat(request: ChoiceRequest) -> dict[str, float]:
    return {o.candidate_id: 1.0 / len(request.options) for o in request.options}


def _candidates(texts: Sequence[str]) -> tuple[Candidate, ...]:
    return tuple(
        Candidate(text=t, readings=("ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ"), baseline_score=-1.0 - i, baseline_rank=i)
        for i, t in enumerate(texts)
    )


def _assert_identical(result: RankingResult, baseline: RankingResult) -> None:
    got = [rc.candidate for rc in result.candidates]
    want = [rc.candidate for rc in baseline.candidates]
    assert [c.candidate_id for c in got] == [c.candidate_id for c in want]
    assert got == want
    assert [VARIANTS.family_key(c.text) for c in got] == [VARIANTS.family_key(c.text) for c in want]
    got_families = [f.representative.candidate_id for f in group_families(got, VARIANTS)]
    want_families = [f.representative.candidate_id for f in group_families(want, VARIANTS)]
    assert got_families == want_families
    assert result.texts() == baseline.texts()
    assert result.texts()[0] == baseline.texts()[0]


# decoder 順序與 baseline ranker 順序不同，且 baseline 前幾名落在 decoder 前 k 名之外：
# 這正是 DEV 上 gate = 0 仍改變排序的情況（t014 / t015 / t046 / t063）。
TEXTS = ["在去台北", "在去臺北", "載去台北", "再去台北", "再去臺北", "在去抬北"]
SCORES = {"再去台北": -1.0, "在去台北": -1.2, "再去臺北": -1.3, "在去抬北": -2.0, "在去臺北": -2.5, "載去台北": -3.0}


def _hybrid(max_weight: float = 0.6, top_k: int = 2) -> tuple[ConfidenceAwareHybridRanker, ScoreRanker, FakeBackend]:
    baseline = ScoreRanker(SCORES)
    backend = FakeBackend(_flat)
    contextual = ContextualRanker(backend, timeout_s=0.5, top_k=top_k, variants=VARIANTS)
    return ConfidenceAwareHybridRanker(baseline, contextual, ConfidenceConfig(max_weight=max_weight)), baseline, backend


def test_zero_effective_weight_equals_baseline_ranking() -> None:
    hybrid, baseline, backend = _hybrid()
    candidates = _candidates(TEXTS)
    result = hybrid.rank(CONTEXT, candidates)
    assert result.context_confidence is not None and result.context_confidence.effective_weight == 0.0
    assert backend.requests, "gate = 0 仍要呼叫模型並保留診斷資料"
    _assert_identical(result, baseline.rank(CONTEXT, candidates))


def test_contextual_window_follows_baseline_ranker_order() -> None:
    hybrid, baseline, backend = _hybrid(top_k=2)
    hybrid.rank(CONTEXT, _candidates(TEXTS))
    # baseline 前兩個 family：再去台北（含臺北）與在去台北（含臺北）；載去台北不應進視窗。
    assert [o.text for o in backend.requests[0].options] == ["再去台北", "在去台北"]


@pytest.mark.parametrize("seed", range(30))
def test_invariant_holds_for_random_orders(seed: int) -> None:
    rng = random.Random(seed)
    texts = TEXTS[:]
    rng.shuffle(texts)
    scores = {t: rng.choice([-1.0, -1.5, -2.0, -40.0, -400.0]) for t in texts}
    baseline = ScoreRanker(scores)
    contextual = ContextualRanker(FakeBackend(_flat), timeout_s=0.5, top_k=rng.randint(2, 4), variants=VARIANTS)
    candidates = _candidates(texts)
    result = ConfidenceAwareHybridRanker(baseline, contextual).rank(CONTEXT, candidates)
    assert result.context_confidence is not None and result.context_confidence.effective_weight == 0.0
    _assert_identical(result, baseline.rank(CONTEXT, candidates))


@pytest.mark.parametrize("seed", range(30))
def test_fixed_hybrid_mix_at_zero_weight_is_baseline(seed: int) -> None:
    # 固定權重版的混合在 w → 0 時必須連續地退回 baseline，視窗外的候選不可被整批往後移。
    from zaoseq_bopomofo.ranking.hybrid import _mix

    rng = random.Random(seed)
    texts = TEXTS[:]
    rng.shuffle(texts)
    baseline = ScoreRanker({t: rng.choice([-1.0, -1.5, -2.0, -40.0, -400.0]) for t in texts})
    base = baseline.rank(CONTEXT, _candidates(texts))
    window = {rc.candidate.candidate_id: rng.random() for rc in base.candidates[:2]}
    ranked = _mix(base, window, 0.0)
    assert [rc.candidate for rc in ranked] == [rc.candidate for rc in base.candidates]


def test_fixed_hybrid_zero_weight_is_baseline() -> None:
    baseline = ScoreRanker(SCORES)
    backend = FakeBackend(_flat)
    contextual = ContextualRanker(backend, timeout_s=0.5, top_k=2, variants=VARIANTS)
    candidates = _candidates(TEXTS)
    _assert_identical(HybridRanker(baseline, contextual, 0.0).rank(CONTEXT, candidates), baseline.rank(CONTEXT, candidates))
    assert backend.requests == []
