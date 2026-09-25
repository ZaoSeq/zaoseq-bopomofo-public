from __future__ import annotations

import itertools
import math

import pytest

from conftest import entry
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams
from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig, reachable, tone_variants
from zaoseq_bopomofo.decoding.family import VariantTable, group_families
from zaoseq_bopomofo.decoding.lattice import LatticeConfig, LatticeDecoder
from zaoseq_bopomofo.decoding.scoring import LinearScorer
from zaoseq_bopomofo.lexicon.lexicon import Lexicon

READINGS = ("ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄧㄢ", "ㄑㄧˋ")


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon(
        [
            entry("在", "ㄗㄞˋ", 1000),
            entry("再", "ㄗㄞˋ", 200),
            entry("載", "ㄗㄞˋ", 50),
            entry("去", "ㄑㄩˋ", 1000),
            entry("趣", "ㄑㄩˋ", 50),
            entry("天", "ㄊㄧㄢ", 1000),
            entry("添", "ㄊㄧㄢ", 20),
            entry("氣", "ㄑㄧˋ", 200),
            entry("器", "ㄑㄧˋ", 50),
            entry("汽", "ㄑㄧˋ", 40),
            entry("天氣", "ㄊㄧㄢ ㄑㄧˋ", 200),
            entry("再去", "ㄗㄞˋ ㄑㄩˋ", 30),
            entry("嗎", "ㄇㄚ˙", 100),
            entry("媽", "ㄇㄚ", 100),
            entry("臺", "ㄊㄞˊ", 30),
            entry("台", "ㄊㄞˊ", 60),
        ]
    )


@pytest.fixture
def lm() -> CorpusLanguageModel:
    sentences = ["我明天會再去看天氣", "在去年的天氣", "再去一次", "汽車在路上"]
    return CorpusLanguageModel(count_ngrams(sentences, min_trigram_count=1), vocabulary_size=40)


SCORER = LinearScorer(corpus_weight=1.0, lexical_weight=1.0)


def _texts(lattice: CoverageLattice, readings=READINGS, left: str = "") -> list[str]:  # type: ignore[no-untyped-def]
    return [c.text for c in lattice.generate(readings, left).candidates]


def test_default_config_matches_frozen_lattice(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    for beam, nbest in ((48, 20), (2, 3), (1, 1)):
        frozen = LatticeDecoder(lexicon, lm, SCORER, config=LatticeConfig(beam=beam, nbest=nbest))
        mine = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=beam, nbest=nbest))
        for left in ("", "我明天會"):
            a = [(s.text, round(s.total, 9)) for s in frozen.decode(READINGS, left)]
            b = [(c.text, round(c.baseline_score, 9)) for c in mine.generate(READINGS, left).candidates]
            assert a == b


def _all_paths(lexicon: Lexicon, readings: tuple[str, ...]) -> set[str]:
    texts: set[str] = set()

    def walk(position: int, text: str) -> None:
        if position == len(readings):
            texts.add(text)
            return
        for length in range(1, lexicon.max_word_length + 1):
            for e in lexicon.lookup(readings[position : position + length]):
                walk(position + length, text + e.text)

    walk(0, "")
    return texts


def test_unlimited_generation_contains_every_lexicon_path(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    exhaustive = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=10_000, nbest=10_000))
    assert set(_texts(exhaustive)) == _all_paths(lexicon, READINGS)
    for beam in (1, 2, 4, 8):
        limited = set(_texts(CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=beam, nbest=10_000))))
        assert limited <= _all_paths(lexicon, READINGS)


def test_larger_nbest_only_extends_the_list(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    short = _texts(CoverageLattice(lexicon, lm, SCORER, GenerationConfig(nbest=3)))
    long = _texts(CoverageLattice(lexicon, lm, SCORER, GenerationConfig(nbest=10)))
    assert long[: len(short)] == short and len(long) >= len(short)


def test_exhaustive_beam_is_monotone_superset(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    """beam 足以容納所有假設之後，再加大 beam 不會改變任何結果；任何有限 beam 的輸出都是它的子集。"""
    reference = _texts(CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=1000, nbest=1000)))
    assert reference == _texts(CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=5000, nbest=1000)))
    for beam in range(1, 12):
        assert set(_texts(CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=beam, nbest=1000)))) <= set(reference)


def test_deterministic_ordering(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    lattice = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(nbest=50))
    runs = [lattice.generate(READINGS, "我明天會").candidates for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]
    scores = [(-c.baseline_score, c.text) for c in runs[0]]
    assert scores == sorted(scores)
    shuffled = Lexicon(list(reversed([e for r in _readings_of(lexicon) for e in lexicon.lookup(r)])))
    assert [c.text for c in CoverageLattice(shuffled, lm, SCORER, GenerationConfig(nbest=50)).generate(READINGS, "我明天會").candidates] == [
        c.text for c in runs[0]
    ]


def _readings_of(lexicon: Lexicon) -> list[tuple[str, ...]]:
    return [r for r in lexicon._by_reading]  # noqa: SLF001


def test_candidate_family_never_erases_surfaces(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    candidates = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(nbest=50)).generate(("ㄊㄞˊ", "ㄊㄧㄢ"), "").candidates
    families = group_families(candidates, VariantTable.load())
    members = [m.text for f in families for m in f.members]
    assert sorted(members) == sorted(c.text for c in candidates)
    assert len(families) < len(candidates)  # 台／臺 同族，但兩種寫法都保留
    assert {"台天", "臺天"} <= set(members)


def test_empty_pruned_and_missing_are_distinct(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    lattice = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=1, nbest=1))
    empty = lattice.generate((), "")
    assert empty.candidates == ()
    unknown = lattice.generate(("ㄅㄚ",), "")
    assert unknown.candidates == ()
    gold = "載趣添汽"
    traced = lattice.generate(
        READINGS,
        "",
        gold_keys=lambda t: t == gold,
        gold_prefix=lambda p, texts: gold[:p] in set(texts),
    )
    assert traced.trace is not None
    assert traced.trace.final_rank is None  # 被剪枝：不是「排在後面」
    assert traced.trace.first_lost is not None
    assert reachable(lexicon, READINGS, lambda i, j, t: t == gold[i:j])  # 詞庫可以拼出，所以是 pruning 不是缺字
    assert not reachable(lexicon, READINGS, lambda i, j, t: t == "在去天霧"[i:j])
    wide = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(beam=1000, nbest=1000))
    ranked = wide.generate(READINGS, "", gold_keys=lambda t: t == gold, gold_prefix=lambda p, texts: gold[:p] in set(texts))
    assert ranked.trace is not None and ranked.trace.final_rank is not None and ranked.trace.first_lost is None


def test_tone_variant_lookup_is_opt_in(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    assert tone_variants("ㄇㄚ˙") == ("ㄇㄚ", "ㄇㄚˊ", "ㄇㄚˇ", "ㄇㄚˋ")
    assert tone_variants("ㄇㄚ") == ("ㄇㄚ˙",)
    default = CoverageLattice(lexicon, lm, SCORER, GenerationConfig())
    variant = CoverageLattice(lexicon, lm, SCORER, GenerationConfig(tone_variant_lookup=True))
    assert _texts(default, ("ㄇㄚ˙",)) == ["嗎"]
    assert set(_texts(variant, ("ㄇㄚ˙",))) == {"嗎", "媽"}


def test_config_validation() -> None:
    for kwargs in ({"beam": 0}, {"nbest": 0}, {"lexical_slots": -1}, {"max_entries_per_span": 0}):
        with pytest.raises(ValueError):
            GenerationConfig(**kwargs)  # type: ignore[arg-type]


def test_scores_are_finite(lexicon: Lexicon, lm: CorpusLanguageModel) -> None:
    for c in CoverageLattice(lexicon, lm, SCORER, GenerationConfig(nbest=100)).generate(READINGS, "").candidates:
        assert math.isfinite(c.baseline_score)
    assert list(itertools.islice(_all_paths(lexicon, ("ㄗㄞˋ",)), 3))


def test_coverage_dev_is_consistent() -> None:
    import json
    from collections import Counter

    from zaoseq_bopomofo.coverage.dataset import ITEMS, MANIFEST, SOURCE, _hash, load_items, read_source

    items = load_items()
    assert [i.to_json() for i in items] == [i.to_json() for i in read_source()]
    assert set(Counter(i.category for i in items).values()) == {25} and len(items) == 300
    for item in items:
        assert len(item.text) == len(item.readings)
        assert item.acceptable[0] == item.text
        assert sum(len(w.text) for w in item.words) == len(item.text)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["files"]["benchmarks/coverage_v1/source.tsv"] == _hash(SOURCE)
    assert manifest["files"]["benchmarks/coverage_v1/coverage_dev.jsonl"] == _hash(ITEMS)
    assert manifest["leakage"]["external_hits"] == {} and manifest["leakage"]["internal_hits"] == []


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_coverage_versions_match_manifest(version: str) -> None:
    from zaoseq_bopomofo.coverage.dataset import DATASETS

    dataset = DATASETS[version]
    assert dataset.verify() == []
    assert [i.to_json() for i in dataset.load()] == [i.to_json() for i in dataset.read_source()]


def test_coverage_v1_1_differs_from_v1_0_only_in_recorded_items() -> None:
    import json

    from zaoseq_bopomofo.coverage.dataset import V1_0, V1_1, file_hash

    manifest = json.loads(V1_1.manifest_file.read_text(encoding="utf-8"))
    assert manifest["parent"]["source_sha256"] == file_hash(V1_0.source)
    assert manifest["changed_items"] == V1_1.changed_items() == ["coverage:cv19"]
    assert manifest["changes"]
    before = {i.item_id: i for i in V1_0.load()}
    after = {i.item_id: i for i in V1_1.load()}
    assert before.keys() == after.keys()
    cv19 = after["coverage:cv19"]
    assert cv19.text == before["coverage:cv19"].text and cv19.readings == before["coverage:cv19"].readings
    assert set(cv19.acceptable) - set(before["coverage:cv19"].acceptable) == {"你幫我看一下這個字怎麼念"}
