from __future__ import annotations

import math
import random

from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams
from zaoseq_bopomofo.coverage.lattice import CoverageLattice
from zaoseq_bopomofo.decoder_v3.lattice import GuardedLattice
from zaoseq_bopomofo.decoder_v3.ngram import KneserNeyModel, NgramBuilder, NgramMixture, WittenBellModel, history_of
from zaoseq_bopomofo.decoder_v3.script_guard import ScriptGuard, count_grams
from zaoseq_bopomofo.decoding.scoring import LinearScorer
from zaoseq_bopomofo.lexicon.entry import EntrySource, LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon

TEXTS = ["我明天會再去台北", "你今天要去哪裡", "我們在這裡等你", "這裡的天氣很好", "他在台北工作", "我在這裡", "我在這裡等", "你在哪裡"] * 3


# ---------------------------------------------------------------- script guard


def test_guard_blocks_unattested_simplified_forms_and_keeps_accepted_variants() -> None:
    standard = set("這裡里哪台臺北在們你我天好的")
    variants = {"裡": frozenset({"里"}), "臺": frozenset({"台"}), "這": frozenset({"这"})}
    texts = ["這裡很好"] * 10 + ["台北很好"] * 10 + ["臺北很好"] * 10 + ["哪裡"] * 10
    guard = ScriptGuard.build(standard, variants, texts, accepted_pairs=[("台", "臺")], extra_forms=())
    assert guard.violates("這里", final=True)
    assert guard.violates("哪里", final=True)
    assert guard.violates("这")
    assert not guard.violates("台北", final=True) and not guard.violates("這裡", final=True)
    assert guard.violates("我在這里", final=True)
    assert not guard.violates("這里等", start=2)


def test_guard_accepts_simplified_looking_characters_with_traditional_evidence() -> None:
    standard = set("這裡里德馬嗎會徵征服")
    variants = {"裡": frozenset({"里"}), "徵": frozenset({"征"})}
    texts = ["在這裡嗎"] * 10 + ["馬德里"] * 5 + ["委員會徵求"] * 10 + ["征服"] * 5
    guard = ScriptGuard.build(standard, variants, texts, extra_forms=())
    assert "裡嗎" not in guard.forms and "里嗎" in guard.forms
    assert not guard.violates("去馬德里嗎", final=True)
    assert not guard.violates("機會征服", final=True)
    assert guard.violates("這里嗎", final=True)
    assert not guard.violates("會征", start=1)


def test_guard_keeps_forms_that_are_common_in_traditional_text() -> None:
    standard = set("里長鄰")
    variants = {"裡": frozenset({"里"})}
    texts = ["裡長"] * 10 + ["里長"] * 10
    assert not ScriptGuard.build(standard, variants, texts, extra_forms=()).violates("里長")


def test_count_grams_counts_windows_touching_the_alphabet() -> None:
    counts = count_grams(["甲裡乙"], frozenset("裡"))
    assert counts["甲裡"] == 1 and counts["裡乙"] == 1 and counts["甲裡乙"] == 1
    assert "甲" not in counts


# ---------------------------------------------------------------- n-gram models


def test_order_three_witten_bell_reproduces_corpus_language_model() -> None:
    old = CorpusLanguageModel(count_ngrams(TEXTS), 50)
    new = WittenBellModel(NgramBuilder(3).build(TEXTS), 50)
    for text in ("我在台北", "這裡", "你們在哪", "陌生字"):
        assert math.isclose(old.score(text), new.score(text), abs_tol=1e-12)
        assert math.isclose(old.score(text, "我"), new.score(text, "我"), abs_tol=1e-12)


def test_higher_orders_use_longer_context_and_stay_normalised() -> None:
    tables = NgramBuilder(5, min_count=1).build(TEXTS)
    vocabulary = sorted(tables.counts[1])
    for model in (WittenBellModel(tables, len(vocabulary)), KneserNeyModel(tables, len(vocabulary))):
        for history in ("^^^^", "我在這裡", "台北"):
            assert math.isclose(math.fsum(model.probability(c, history[-4:]) for c in vocabulary), 1.0, abs_tol=1e-9)
        assert model.extend("我在這裡", "等")[1] == "在這裡等"
    assert history_of("你好", 5) == "^^你好"


def test_mixture_history_follows_the_longest_component() -> None:
    small = WittenBellModel(NgramBuilder(3).build(TEXTS), 50)
    large = KneserNeyModel(NgramBuilder(5).build(TEXTS), 50)
    mixture = NgramMixture([("a", small, 0.5), ("b", large, 0.5)])
    assert mixture.order == 5
    assert mixture.initial_history("今天我在") == "今天我在"
    random.seed(0)
    assert mixture.score("這裡") < 0


# ---------------------------------------------------------------- lattice


def lexicon() -> Lexicon:
    rows = [("這", "ㄓㄜˋ"), ("裡", "ㄌㄧˇ"), ("里", "ㄌㄧˇ"), ("理", "ㄌㄧˇ"), ("哪", "ㄋㄚˇ")]
    return Lexicon(LexiconEntry(text, (reading,), 1.0, EntrySource.CNS11643) for text, reading in rows)


def test_guarded_lattice_without_guard_matches_coverage_lattice() -> None:
    lm = WittenBellModel(NgramBuilder(3).build(TEXTS), 50)
    old = CorpusLanguageModel(count_ngrams(TEXTS), 50)
    scorer = LinearScorer()
    a = CoverageLattice(lexicon(), old, scorer).generate(("ㄓㄜˋ", "ㄌㄧˇ"), "我在")
    b = GuardedLattice(lexicon(), lm, scorer, None).generate(("ㄓㄜˋ", "ㄌㄧˇ"), "我在")
    assert [c.text for c in a.candidates] == [c.text for c in b.candidates]


def test_guarded_lattice_never_outputs_simplified_forms() -> None:
    lm = WittenBellModel(NgramBuilder(3).build(TEXTS), 50)
    guard = ScriptGuard(simplified_chars=(), forms={"這里": (1,), "哪里": (1,)})
    lattice = GuardedLattice(lexicon(), lm, LinearScorer(), guard)
    texts = [c.text for c in lattice.generate(("ㄓㄜˋ", "ㄌㄧˇ"), "").candidates]
    assert "這里" not in texts and "這裡" in texts and "這理" in texts
    assert lattice.rejected >= 1
