from __future__ import annotations

import pytest

from conftest import FakeBackend, prefer
from zaoseq_bopomofo.decoding.generator import CandidateGenerator
from zaoseq_bopomofo.evaluation.benchmark import RankerContractError, evaluate_case, run_benchmark
from zaoseq_bopomofo.evaluation.coverage import measure_coverage
from zaoseq_bopomofo.evaluation.dataset import CaseFormatError, RankingCase, Scenario, build_cases
from zaoseq_bopomofo.evaluation.metrics import CaseOutcome, percentile, summarize, summarize_temporal
from zaoseq_bopomofo.evaluation.order_bias import measure_order_bias
from zaoseq_bopomofo.lexicon.lexicon import Lexicon
from zaoseq_bopomofo.ranking.base import FallbackReason, RankingStatus
from zaoseq_bopomofo.ranking.contextual import ChoiceDistribution, ChoiceRequest, ContextualRanker
from zaoseq_bopomofo.ranking.frequency import FrequencyRanker


def outcome(case_id: str, rank: int, baseline: int, correct: bool = True, **extra: object) -> CaseOutcome:
    fields: dict[str, object] = {
        "status": RankingStatus.OK,
        "fallback_reason": None,
        "latency_ms": 1.0,
        "model_latency_ms": None,
        "top_text": "x",
        "target_text": "x",
        "ambiguous_at_t0": False,
    }
    fields.update(extra)
    return CaseOutcome(case_id, rank, baseline, target_correct=correct, **fields)  # type: ignore[arg-type]


def test_top1_mrr_and_regressions() -> None:
    summary = summarize([outcome("a", 0, 0), outcome("b", 1, 0), outcome("c", 0, 2), outcome("d", 3, 3)])
    assert summary.top1_accuracy == pytest.approx(0.5)
    assert summary.mrr == pytest.approx((1 + 0.5 + 1 + 0.25) / 4)
    assert (summary.regressions, summary.improvements, summary.unchanged) == (1, 1, 2)


def test_fallback_and_invalid_counts() -> None:
    items = [
        outcome("a", 0, 0, status=RankingStatus.FALLBACK, fallback_reason=FallbackReason.TIMEOUT),
        outcome("b", 0, 0, status=RankingStatus.FALLBACK, fallback_reason=FallbackReason.INVALID_PROBABILITY),
        outcome("c", 0, 0, status=RankingStatus.FALLBACK, fallback_reason=FallbackReason.UNKNOWN_CANDIDATE),
    ]
    summary = summarize(items)
    assert (summary.fallback_count, summary.timeout_count, summary.invalid_response_count) == (3, 1, 2)


def test_empty_summary_uses_none_not_zero() -> None:
    summary = summarize([])
    assert summary.top1_accuracy is None
    assert summary.rerank_latency.p50_ms is None


def test_percentile_linear_interpolation() -> None:
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(values, 50) == 3.0
    assert percentile(values, 95) == pytest.approx(4.8)
    assert percentile([7.0], 95) == 7.0
    assert percentile([], 50) is None
    with pytest.raises(ValueError):
        percentile(values, 101)


def test_temporal_confusion_counts() -> None:
    t0 = {
        "a": outcome("a", 1, 1, correct=False, top_text="在"),
        "b": outcome("b", 0, 0, correct=True, top_text="再"),
        "c": outcome("c", 1, 1, correct=False, top_text="在", ambiguous_at_t0=True),
        "d": outcome("d", 0, 0, correct=True, top_text="是"),
    }
    t1 = [
        outcome("a", 0, 1, correct=True, target_text="再"),
        outcome("b", 1, 0, correct=False, target_text="在"),
        outcome("c", 0, 1, correct=True, target_text="再", ambiguous_at_t0=True),
        outcome("d", 0, 0, correct=True, target_text="是"),
    ]
    summary = summarize_temporal(t0, t1)
    assert (summary.wrong_to_correct, summary.correct_to_wrong) == (2, 1)
    assert (summary.unchanged_correct, summary.unchanged_wrong) == (1, 0)
    assert summary.changed == 3
    assert summary.correction_precision == pytest.approx(2 / 3)
    assert summary.initial_top1_accuracy == 0.5
    assert summary.final_top1_accuracy == 0.75
    assert (summary.wrong_to_correct_ambiguous, summary.initial_wrong_ambiguous) == (1, 1)


def _case(**overrides: object) -> RankingCase:
    fields: dict[str, object] = {
        "case_id": "x",
        "left_context": "我明天會",
        "readings": ("ㄗㄞˋ",),
        "candidates": ("在", "再", "載"),
        "baseline_scores": (-2.0, -2.7, -3.3),
        "answers": ("再",),
        "target": "再",
        "target_length": 1,
        "ambiguous_at_t0": False,
    }
    fields.update(overrides)
    return RankingCase(**fields)  # type: ignore[arg-type]


def test_case_validation() -> None:
    with pytest.raises(CaseFormatError):
        _case(answers=("宰",))
    with pytest.raises(CaseFormatError):
        _case(candidates=())
    with pytest.raises(CaseFormatError):
        Scenario("s", "", "再", ("ㄗㄞˋ",), "", (), ("在",))


def test_ambiguous_case_accepts_any_answer() -> None:
    case = _case(answers=("在", "再"), ambiguous_at_t0=True)
    result = evaluate_case(FrequencyRanker(), case)
    assert result.answer_rank == 0
    assert result.target_correct is False


def test_contextual_outcome_records_model_latency() -> None:
    result = evaluate_case(ContextualRanker(FakeBackend(prefer("再"))), _case())
    assert result.answer_rank == 0 and result.baseline_answer_rank == 1
    assert result.model_latency_ms is not None


def test_contract_violation_fails_benchmark() -> None:
    class Broken:
        name = "broken"
        model_name = None

        def rank(self, context, candidates):  # type: ignore[no-untyped-def]
            result = FrequencyRanker().rank(context, candidates)
            return type(result)(**{**result.__dict__, "candidates": result.candidates[:1]})

    with pytest.raises(RankerContractError):
        evaluate_case(Broken(), _case())  # type: ignore[arg-type]


def test_build_cases_and_run(small_lexicon: Lexicon) -> None:
    scenarios = [
        Scenario("s1", "我明天會", "再", ("ㄗㄞˋ",), "去", ("ㄑㄩˋ",), ("在", "再")),
        Scenario("s2", "", "天氣", ("ㄊㄧㄢ", "ㄑㄧˋ"), "", (), ("天氣",)),
        Scenario("s3", "", "宰", ("ㄗㄞˋ",), "", (), ("宰",)),
    ]
    built = build_cases(scenarios, CandidateGenerator(small_lexicon))
    assert [c.case_id for c in built.immediate] == ["s1", "s2"]
    assert [c.answers for c in built.composition] == [("再去",), ("天氣",)]
    assert built.immediate[0].ambiguous_at_t0
    assert any("s3" in item for item in built.excluded)

    reports = run_benchmark([FrequencyRanker()], built.immediate, built.composition, warmup=0)
    assert reports[0].temporal.paired_cases == 2
    assert reports[0].immediate.top1_accuracy == 1.0


def test_coverage(small_lexicon: Lexicon) -> None:
    scenarios = [
        Scenario("s1", "", "再", ("ㄗㄞˋ",), "去", ("ㄑㄩˋ",), ("再",)),
        Scenario("s2", "", "天", ("ㄊㄧㄢ",), "器", ("ㄑㄧˋ",), ("天",)),
    ]
    summary = measure_coverage(scenarios, small_lexicon, CandidateGenerator(small_lexicon), ks=(1, 0))
    assert summary.recall_at_k[1] == 0.0
    assert summary.recall_at_k[0] == 1.0
    assert summary.oov_rate == 0.0
    assert summary.segmentation_coverage == 1.0


def test_order_bias_detects_first_position_preference() -> None:
    def first_wins(request: ChoiceRequest) -> ChoiceDistribution:
        k = len(request.options)
        probs = {o.candidate_id: (0.7 if i == 0 else 0.3 / (k - 1)) for i, o in enumerate(request.options)}
        return ChoiceDistribution("fake", probs, None)

    summary = measure_order_bias([_case()], first_wins, window=3)
    assert summary.orders_per_case == 6
    assert summary.first_position_win_rate == 1.0
    assert summary.top1_flip_rate == 1.0
