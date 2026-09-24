from __future__ import annotations

import random

import pytest

from conftest import CONTEXT, FakeBackend, entry, make_candidates, prefer
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams
from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.decoding.correction import ErrorKind, ErrorSource
from zaoseq_bopomofo.decoding.errors import ErrorCosts, ReadingErrorModel
from zaoseq_bopomofo.decoding.family import VariantRule, VariantTable, group_families
from zaoseq_bopomofo.decoding.lattice import LatticeConfig, LatticeDecoder
from zaoseq_bopomofo.decoding.scoring import LinearScorer, ScoreBreakdown
from zaoseq_bopomofo.decoding.tolerant import ExpansionReason, TolerancePolicy, TolerantDecoder
from zaoseq_bopomofo.evaluation.decoding import (
    DecodingItem,
    SystemOutput,
    clean_input_safety,
    inject_noise,
    score_outputs,
)
from zaoseq_bopomofo.lexicon.lexicon import Lexicon
from zaoseq_bopomofo.phonetics.keyboard import StandardKeyboardLayout
from zaoseq_bopomofo.ranking.contextual import ContextualRanker
from zaoseq_bopomofo.ranking.corpus import CorpusRanker
from zaoseq_bopomofo.ranking.frequency import FrequencyRanker
from zaoseq_bopomofo.ranking.hybrid import ConfidenceAwareHybridRanker

INVENTORY = frozenset({"ㄗㄞˋ", "ㄗㄞ", "ㄗㄞˇ", "ㄘㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ", "ㄗㄚˋ", "ㄓㄞˋ", "ㄗㄠˋ"})


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon(
        [
            entry("在", "ㄗㄞˋ", 1000),
            entry("再", "ㄗㄞˋ", 200),
            entry("載", "ㄗㄞˇ", 50),
            entry("菜", "ㄘㄞˋ", 50),
            entry("去", "ㄑㄩˋ", 1000),
            entry("台", "ㄊㄞˊ", 500),
            entry("臺", "ㄊㄞˊ", 200),
            entry("北", "ㄅㄟˇ", 500),
            entry("台北", "ㄊㄞˊ ㄅㄟˇ", 300),
            entry("臺北", "ㄊㄞˊ ㄅㄟˇ", 100),
        ]
    )


@pytest.fixture
def lm() -> CorpusLanguageModel:
    counts = count_ngrams(["我明天會再去台北。", "他再去台北。", "我明天會再去。"] * 3, min_trigram_count=1)
    return CorpusLanguageModel(counts, vocabulary_size=len(set(counts.unigrams) | set("在再載菜去台臺北")))


def test_error_model_kinds_sources_and_inventory() -> None:
    model = ReadingErrorModel(INVENTORY)
    alternatives = {a.reading: a.edit for a in model.alternatives("ㄗㄞ", 0)}
    assert alternatives["ㄗㄞˋ"].kind is ErrorKind.TONE_MISSING
    assert alternatives["ㄗㄞˋ"].source is ErrorSource.TONE
    confusion = {a.reading: a.edit for a in model.alternatives("ㄗㄞˋ", 0)}
    assert confusion["ㄓㄞˋ"].kind is ErrorKind.PHONETIC_CONFUSION
    assert confusion["ㄓㄞˋ"].source is ErrorSource.PRONUNCIATION
    assert confusion["ㄘㄞˋ"].kind is ErrorKind.ADJACENT_KEY
    assert confusion["ㄘㄞˋ"].source is ErrorSource.KEYBOARD
    assert confusion["ㄗㄞˇ"].kind is ErrorKind.TONE_WRONG
    assert all(reading in INVENTORY for reading in confusion)
    assert "ㄗㄞˋ" not in confusion
    costs = [a.edit.cost for a in model.alternatives("ㄗㄞˋ", 0)]
    assert costs == sorted(costs) and all(c > 0 for c in costs)


def test_transposition_swaps_adjacent_tones() -> None:
    model = ReadingErrorModel(INVENTORY | {"ㄑㄩˇ", "ㄗㄞˋ"})
    swapped = model.transposition(("ㄗㄞˇ", "ㄑㄩˋ"), 0)
    assert swapped is not None and swapped[:2] == ("ㄗㄞˋ", "ㄑㄩˇ")
    assert swapped[2].kind is ErrorKind.TRANSPOSITION
    assert model.transposition(("ㄗㄞˋ", "ㄑㄩˋ"), 0) is None


def test_exact_path_has_zero_edit_cost(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    decoder = LatticeDecoder(lexicon, lm, LinearScorer(), ReadingErrorModel(INVENTORY))
    results = decoder.decode(("ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ"), "我明天會")
    assert results[0].text == "再去台北"
    assert all(r.edits == () and r.breakdown.pronunciation == 0 for r in results)
    with pytest.raises(ValueError):
        decoder.decode(("ㄗㄞˋ",), max_edits=2)


def test_tolerant_decoder_records_correction_and_keeps_exact(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    errors = ReadingErrorModel(INVENTORY)
    decoder = TolerantDecoder(LatticeDecoder(lexicon, lm, LinearScorer(), errors), errors, TolerancePolicy(quality_threshold=0.0))
    outcome = decoder.decode(("ㄗㄞ", "ㄑㄩˋ"), "我明天會")
    assert outcome.reason is ExpansionReason.NO_EXACT_CANDIDATE
    top = outcome.candidates[0]
    assert top.text == "再去"
    assert top.correction is not None
    assert top.correction.original == ("ㄗㄞ", "ㄑㄩˋ")
    assert top.correction.inferred == ("ㄗㄞˋ", "ㄑㄩˋ")
    assert top.correction.operations[0].kind is ErrorKind.TONE_MISSING
    assert top.breakdown is not None and top.breakdown.pronunciation == -ErrorCosts().tone_missing

    clean = decoder.decode(("ㄗㄞˋ", "ㄑㄩˋ"), "我明天會")
    exact = [c for c in clean.candidates if c.correction is None]
    assert exact and exact[0].text == "再去"
    assert [c.baseline_rank for c in clean.candidates] == list(range(len(clean.candidates)))


def test_good_exact_quality_skips_expansion(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    errors = ReadingErrorModel(INVENTORY)
    decoder = TolerantDecoder(LatticeDecoder(lexicon, lm, LinearScorer(), errors), errors, TolerancePolicy(quality_threshold=-50))
    outcome = decoder.decode(("ㄗㄞˋ", "ㄑㄩˋ"), "我明天會")
    assert outcome.reason is ExpansionReason.NOT_EXPANDED
    assert all(c.correction is None for c in outcome.candidates)


def test_disabled_policy_never_corrects(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    errors = ReadingErrorModel(INVENTORY)
    decoder = TolerantDecoder(LatticeDecoder(lexicon, lm, LinearScorer(), errors), errors, TolerancePolicy(enabled=False))
    assert decoder.decode(("ㄗㄞ", "ㄑㄩˋ")).candidates == ()


def test_beam_bounds_candidate_count(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    errors = ReadingErrorModel(INVENTORY)
    decoder = LatticeDecoder(lexicon, lm, LinearScorer(), errors, LatticeConfig(beam=2, nbest=3))
    assert len(decoder.decode(("ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ"), max_edits=1)) <= 3


def test_scorer_components_are_explicit() -> None:
    breakdown = ScoreBreakdown(pronunciation=-2.0, lexical=-5.0, corpus=-10.0)
    assert LinearScorer(1.0, 0.0, 1.0).total(breakdown) == -12.0
    assert LinearScorer(1.0, 1.0, 0.5).total(breakdown) == -16.0
    assert LinearScorer(0.0, 1.0, 1.0).total(ScoreBreakdown(0.0, -3.0, None)) == -3.0
    with pytest.raises(ValueError):
        LinearScorer(corpus_weight=-1.0)


def test_variant_family_grouping() -> None:
    table = VariantTable([VariantRule("台", "臺", "")])
    candidates = make_candidates(["在去台北", "在去臺北", "再去台北", "再去臺北"])
    families = group_families(candidates, table)
    assert [f.key for f in families] == ["在去台北", "再去台北"]
    assert [m.text for m in families[1].members] == ["再去台北", "再去臺北"]
    with pytest.raises(ValueError):
        VariantTable([VariantRule("台", "台", "")])
    with pytest.raises(ValueError):
        VariantTable([VariantRule("台", "臺", ""), VariantRule("台", "臺", "")])


def test_family_window_keeps_variants_out_of_contextual_top_k() -> None:
    table = VariantTable([VariantRule("台", "臺", "")])
    candidates = make_candidates(["在去台北", "在去臺北", "再去台北", "再去臺北", "載去台北"])
    backend = FakeBackend(prefer("再去台北", top=0.8))
    result = ContextualRanker(backend, top_k=3, variants=table).rank(CONTEXT, candidates)
    assert [o.text for o in backend.requests[0].options] == ["在去台北", "再去台北", "載去台北"]
    texts = [rc.candidate.text for rc in result.candidates]
    assert texts[:2] == ["再去台北", "再去臺北"]
    representatives = [rc.candidate.text for rc in result.candidates if rc.family_representative and rc.contextual_probability]
    assert set(representatives) == {"在去台北", "再去台北", "載去台北"}


def test_hybrid_confidence_ignores_duplicate_variants() -> None:
    table = VariantTable([VariantRule("台", "臺", "")])
    candidates = make_candidates(["在去台北", "在去臺北", "再去台北", "再去臺北"], [-2.0, -2.1, -2.2, -2.3])
    ranker = ConfidenceAwareHybridRanker(
        FrequencyRanker(), ContextualRanker(FakeBackend(prefer("再去台北", top=0.95)), variants=table)
    )
    result = ranker.rank(CONTEXT, candidates)
    assert result.context_confidence is not None and result.context_confidence.margin == pytest.approx(0.9)
    assert result.candidates[0].candidate.text == "再去台北"


def test_corpus_ranker_uses_left_context(lm: CorpusLanguageModel) -> None:
    candidates = make_candidates(["在去", "再去"], [-1.0, -2.0])
    result = CorpusRanker(lm).rank(CONTEXT, candidates)
    assert [rc.candidate.text for rc in result.candidates] == ["再去", "在去"]
    assert CorpusRanker(lm).rank(CONTEXT, ()).candidates == ()


def test_noise_injection_is_deterministic_and_valid() -> None:
    layout = StandardKeyboardLayout()
    readings = ("ㄗㄞˋ", "ㄑㄩˋ")
    first = inject_noise(readings, ErrorKind.TONE_MISSING, random.Random("x"), INVENTORY, layout)
    second = inject_noise(readings, ErrorKind.TONE_MISSING, random.Random("x"), INVENTORY, layout)
    assert first == second and first is not None
    noisy, position = first
    assert noisy[position] in INVENTORY and noisy != readings
    adjacent = inject_noise(("ㄗㄞˋ",), ErrorKind.ADJACENT_KEY, random.Random("y"), INVENTORY, layout)
    assert adjacent is not None and adjacent[0][0] in {"ㄘㄞˋ", "ㄗㄚˋ"}
    assert inject_noise(("ㄗㄞˋ",), ErrorKind.DELETION, random.Random("z"), frozenset({"ㄗㄞˋ"}), layout) is None


def test_decoding_metrics_and_clean_input_safety() -> None:
    items = [DecodingItem("a", "hand", "", ("ㄗㄞˋ",), "再"), DecodingItem("b", "hand", "", ("ㄗㄞˋ",), "在")]
    exact = [SystemOutput(("再", "在"), False, 1.0), SystemOutput(("在",), False, 1.0)]
    tolerant = [SystemOutput(("菜", "再"), True, 2.0), SystemOutput(("在",), False, 3.0)]
    score = score_outputs(list(zip(items, tolerant)))
    assert score.sentence_accuracy == 0.5 and score.recall_at[5] == 1.0 and score.corrected_top == 1
    assert score.character_accuracy == 0.5
    safety = clean_input_safety(items, tolerant, exact)
    assert safety.false_correction_rate == 0.5
    assert safety.exact_input_regressions == 1


def test_candidate_without_breakdown_is_backward_compatible() -> None:
    candidate = Candidate("在", ("ㄗㄞˋ",), -1.0, 0)
    assert candidate.breakdown is None and candidate.correction is None
