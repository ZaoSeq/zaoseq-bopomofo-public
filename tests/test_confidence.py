from __future__ import annotations

import threading
from typing import Any

import pytest

from conftest import CONTEXT, FakeBackend, prefer
from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.ranking.base import FallbackReason, RankingStatus
from zaoseq_bopomofo.ranking.confidence import ConfidenceConfig, assess_confidence
from zaoseq_bopomofo.ranking.contextual import ChoiceDistribution, ChoiceRequest, ContextualRanker
from zaoseq_bopomofo.ranking.frequency import FrequencyRanker
from zaoseq_bopomofo.ranking.hybrid import ConfidenceAwareHybridRanker
from zaoseq_bopomofo.ranking.signal import ContextSignal

CONFIG = ConfidenceConfig()


def test_flat_distribution_gets_near_zero_weight() -> None:
    confidence = assess_confidence({"a": 0.279, "b": 0.264, "c": 0.256, "d": 0.201}, None, CONFIG)
    assert confidence.margin == pytest.approx(0.015)
    assert confidence.entropy > 0.95
    assert confidence.effective_weight == 0.0
    assert confidence.confident is False


def test_sharp_consistent_distribution_gets_full_weight() -> None:
    signal = ContextSignal(forward_passes=1, questions=12, disagreement=0.0)
    confidence = assess_confidence({"a": 0.85, "b": 0.05, "c": 0.05, "d": 0.05}, signal, CONFIG)
    assert confidence.effective_weight == pytest.approx(CONFIG.max_weight)
    assert confidence.confident is True


def test_disagreement_and_instability_reduce_weight() -> None:
    probabilities = {"a": 0.85, "b": 0.05, "c": 0.05, "d": 0.05}
    half = assess_confidence(probabilities, ContextSignal(1, 12, disagreement=0.25), CONFIG)
    none = assess_confidence(probabilities, ContextSignal(1, 12, disagreement=0.6), CONFIG)
    unstable = assess_confidence(probabilities, ContextSignal(1, 4, order_instability=0.5), CONFIG)
    assert half.effective_weight == pytest.approx(CONFIG.max_weight * 0.5)
    assert none.effective_weight == 0.0
    assert unstable.effective_weight == 0.0


def test_single_option_has_no_confidence() -> None:
    assert assess_confidence({"a": 1.0}, None, CONFIG).effective_weight == 0.0


@pytest.mark.parametrize(
    "kwargs",
    [{"max_weight": 1.5}, {"margin_low": 0.4, "margin_high": 0.3}, {"disagreement_high": 0.0}],
)
def test_config_validation(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        ConfidenceConfig(**kwargs)


def _hybrid(backend: Any, config: ConfidenceConfig = CONFIG) -> ConfidenceAwareHybridRanker:
    return ConfidenceAwareHybridRanker(FrequencyRanker(), ContextualRanker(backend, timeout_s=0.05), config)


def test_flat_contextual_keeps_baseline_order(zai: tuple[Candidate, ...]) -> None:
    backend = FakeBackend(lambda r: {"c0": 0.32, "c1": 0.34, "c2": 0.34})
    result = _hybrid(backend).rank(CONTEXT, zai)
    assert [rc.candidate.text for rc in result.candidates] == ["在", "再", "載"]
    assert result.context_confidence is not None and result.context_confidence.effective_weight == 0.0


def test_confident_contextual_can_override(zai: tuple[Candidate, ...]) -> None:
    result = _hybrid(FakeBackend(prefer("再", top=0.96))).rank(CONTEXT, zai)
    assert result.candidates[0].candidate.text == "再"
    assert result.context_confidence is not None
    assert result.context_confidence.effective_weight == pytest.approx(CONFIG.max_weight)


def test_high_disagreement_blocks_override(zai: tuple[Candidate, ...]) -> None:
    class Disagreeing:
        model_name = "fake"

        def decide(self, request: ChoiceRequest) -> ChoiceDistribution:
            probs = prefer("再", top=0.96)(request)
            return ChoiceDistribution("fake", probs, None, ContextSignal(1, 6, disagreement=0.9))  # type: ignore[arg-type]

    result = _hybrid(Disagreeing()).rank(CONTEXT, zai)
    assert result.candidates[0].candidate.text == "在"


def test_zero_max_weight_skips_model(zai: tuple[Candidate, ...]) -> None:
    backend = FakeBackend(prefer("再", top=0.96))
    result = _hybrid(backend, ConfidenceConfig(max_weight=0.0)).rank(CONTEXT, zai)
    assert [rc.candidate.text for rc in result.candidates] == ["在", "再", "載"]
    assert backend.requests == []


@pytest.mark.parametrize(
    "backend",
    [FakeBackend(error=RuntimeError("down")), FakeBackend(lambda r: {"x": 1.0}), FakeBackend(lambda r: {})],
    ids=["error", "unknown", "empty"],
)
def test_contextual_failure_is_exactly_baseline(zai: tuple[Candidate, ...], backend: FakeBackend) -> None:
    result = _hybrid(backend).rank(CONTEXT, zai)
    assert result.status is RankingStatus.FALLBACK
    assert result.candidates == FrequencyRanker().rank(CONTEXT, zai).candidates


def test_timeout_is_exactly_baseline(zai: tuple[Candidate, ...]) -> None:
    release = threading.Event()
    try:
        result = _hybrid(FakeBackend(prefer("載"), block=release)).rank(CONTEXT, zai)
        assert result.fallback is not None and result.fallback.reason is FallbackReason.TIMEOUT
        assert result.candidates == FrequencyRanker().rank(CONTEXT, zai).candidates
    finally:
        release.set()
