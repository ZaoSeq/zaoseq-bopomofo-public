from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams
from zaoseq_bopomofo.daily.corpus import DailyCorpusBuilder
from zaoseq_bopomofo.daily.guard import EvaluationGuard, ReferenceSet
from zaoseq_bopomofo.daily.importers import DailyDocument, DailyImporter
from zaoseq_bopomofo.daily.lexicon import (
    CorpusSentence,
    ExtractionPolicy,
    FrequencyAwareExtractor,
    InterpolatedEstimator,
    OccurrenceScanner,
    PooledEstimator,
    build_tables,
)
from zaoseq_bopomofo.daily.mixture import MixtureLanguageModel
from zaoseq_bopomofo.daily.quality import Drop, SentenceInspector, document_problems, weird_unicode
from zaoseq_bopomofo.daily.script import ScriptClassifier, ScriptLabel
from zaoseq_bopomofo.daily.sources import (
    ApprovalScope,
    DailySource,
    LicenseError,
    LicenseGate,
    Purpose,
    RawFiles,
    SourceFile,
    SourceRegistry,
    Status,
    TrainingBasis,
)

STANDARD = set("我們今天去公園散步你好嗎這裡很安靜天氣真好吃飯了沒有他說明早再來看書學生老師上課下雨帶傘大家一起唱歌")


def approved(**changes: object) -> DailySource:
    source = DailySource(
        source_id="fixture",
        dataset_name="fixture corpus",
        provider="tests",
        official_page="https://example.org",
        urls=("https://example.org/a.txt",),
        version="1",
        retrieved_at="2026-09-24",
        license_name="CC0 1.0",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        commercial_use="yes",
        modification="yes",
        redistribution="yes",
        attribution="not required",
        training_use="yes",
        training_basis=TrainingBasis.EXPLICIT,
        inference_basis="",
        data_type="sentences",
        zh_tw_relevance="high",
        fields_used=("text",),
        fields_excluded=(),
        document_identity="line",
        files=(SourceFile("fixture/a.txt", "https://example.org/a.txt", "0" * 64, 1),),
        status=Status.APPROVED,
        approval_scope=ApprovalScope.PRODUCTION,
        reason="fixture",
    )
    return replace(source, **changes)  # type: ignore[arg-type]


def classifier() -> ScriptClassifier:
    return ScriptClassifier(STANDARD, simplified_characters=set("们这说吗书"))


class ListImporter:
    def __init__(self, source_id: str, documents: list[DailyDocument]) -> None:
        self.source_id = source_id
        self._documents = documents

    def documents(self) -> Iterator[DailyDocument]:
        return iter(self._documents)


def no_guard() -> EvaluationGuard:
    return EvaluationGuard([], threshold=0.6)


# ---------------------------------------------------------------- license gate


def test_license_gate_accepts_complete_approved_source() -> None:
    assert LicenseGate().problems(approved()) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"status": Status.HOLD},
        {"status": Status.REJECTED},
        {"training_use": "unknown"},
        {"commercial_use": "no"},
        {"modification": "conditional: no derivatives"},
        {"license_name": "unknown"},
        {"redistribution": ""},
        {"training_basis": TrainingBasis.UNKNOWN},
        {"training_basis": TrainingBasis.INFERRED, "inference_basis": " "},
        {"files": ()},
        {"fields_used": ()},
        {"approval_scope": ApprovalScope.NONE},
    ],
)
def test_license_gate_rejects_uncertain_or_restricted_fields(changes: dict[str, object]) -> None:
    source = approved(**changes)
    assert LicenseGate().problems(source)
    with pytest.raises(LicenseError):
        LicenseGate().require(source)


def test_dev_experiment_scope_is_blocked_for_production() -> None:
    source = approved(approval_scope=ApprovalScope.DEV_EXPERIMENT)
    assert LicenseGate().problems(source, Purpose.DEV_EXPERIMENT) == []
    assert LicenseGate().problems(source, Purpose.PRODUCTION)
    with pytest.raises(LicenseError):
        LicenseGate().require(source, Purpose.PRODUCTION)
    assert LicenseGate().problems(approved(), Purpose.PRODUCTION) == []


def test_importer_refuses_hold_source_before_reading(tmp_path: Path) -> None:
    class Fixture(DailyImporter):
        source_id = "fixture"
        read = False

        def _read(self, files: dict[str, Path]) -> Iterator[DailyDocument]:
            Fixture.read = True
            yield DailyDocument("fixture", "d", "我們今天去公園散步")

    registry = SourceRegistry([approved(status=Status.HOLD)])
    with pytest.raises(LicenseError):
        list(Fixture(registry, raw=RawFiles(tmp_path)).documents())
    assert not Fixture.read


def test_production_importer_rejects_dev_only_and_hold_sources(tmp_path: Path) -> None:
    from zaoseq_bopomofo.daily.importers import OasstPrompterImporter, TatoebaImporter

    registry = SourceRegistry.load()
    with pytest.raises(LicenseError):
        next(OasstPrompterImporter(registry, raw=RawFiles(tmp_path), purpose=Purpose.PRODUCTION).documents())
    with pytest.raises(LicenseError, match="找不到"):
        next(TatoebaImporter(registry, raw=RawFiles(tmp_path), purpose=Purpose.PRODUCTION).documents())
    held = [s for s in registry if s.status is not Status.APPROVED]
    assert held and all(LicenseGate().problems(s, Purpose.PRODUCTION) for s in held)


def test_raw_files_verify_sha256(tmp_path: Path) -> None:
    path = tmp_path / "fixture" / "a.txt"
    path.parent.mkdir()
    path.write_bytes("我們今天去公園散步\n".encode())
    good = SourceFile("fixture/a.txt", "https://example.org/a.txt", hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
    assert RawFiles(tmp_path).verify(approved(files=(good,)))["a.txt"] == path
    with pytest.raises(LicenseError):
        RawFiles(tmp_path).verify(approved(files=(replace(good, sha256="f" * 64),)))


def test_source_manifest_is_complete_and_consistent() -> None:
    registry = SourceRegistry.load()
    gate = LicenseGate()
    sources = list(registry)
    assert len({s.source_id for s in sources}) == len(sources)
    for source in sources:
        assert source.reason.strip() and source.official_page.strip()
        assert source.training_use.strip() and source.redistribution.strip()
        if source.status is Status.APPROVED:
            assert gate.problems(source) == [], source.source_id
            assert all(f.url.startswith("https://") and len(f.sha256) == 64 and f.bytes > 0 for f in source.files)
        else:
            assert gate.problems(source), source.source_id
    held = {s.source_id for s in registry.with_status(Status.HOLD)}
    assert {
        "cv_sentence_collector_zh_tw",
        "twllm_data",
        "mdc_common_voice_zh_tw",
        "cv_zh_tw_chatlogs",
        "cv_zh_tw_lms",
        "cv_zh_tw_taipei_city_gov",
    } <= held
    for source in sources:
        if source.status is not Status.APPROVED:
            assert source.approval_scope is ApprovalScope.NONE, source.source_id
    production = {s.source_id for s in sources if not gate.problems(s, Purpose.PRODUCTION)}
    assert production == {"tatoeba_cmn_hant", "mdc_common_voice_zh_tw_27_0", "unihan_variants"}


def test_attribution_is_preserved_for_sources_that_require_authors() -> None:
    from zaoseq_bopomofo.daily.corpus import ATTRIBUTION_DIR

    registry = SourceRegistry.load()
    for source in registry.with_status(Status.APPROVED):
        if any("attribution" in f for f in source.fields_used):
            path = ATTRIBUTION_DIR / f"{source.source_id}.tsv"
            lines = path.read_text(encoding="utf-8").splitlines()
            assert source.license_url in lines[1]
            assert sum(not line.startswith("#") for line in lines) > 0


def test_every_importer_reads_an_approved_source() -> None:
    from zaoseq_bopomofo.daily.importers import IMPORTERS

    registry = SourceRegistry.load()
    for importer in IMPORTERS:
        assert LicenseGate().problems(registry[importer.source_id]) == []


# ---------------------------------------------------------------- script / quality


def test_script_classifier_never_converts() -> None:
    c = classifier()
    assert c.classify("我們今天去公園散步").label is ScriptLabel.TRADITIONAL
    assert c.classify("我们今天去公园散步").label is ScriptLabel.SIMPLIFIED
    assert c.classify("你吃什么").label is ScriptLabel.SIMPLIFIED
    assert c.classify("我們去堃").label is ScriptLabel.NON_STANDARD
    assert c.classify("abc").label is ScriptLabel.NO_HAN


def test_document_problems_and_weird_unicode() -> None:
    assert Drop.URL in document_problems("請看 https://example.org")
    assert Drop.EMAIL in document_problems("寄到 a.b@example.org")
    assert Drop.PERSONAL_ID in document_problems("身分證 A123456789")
    assert Drop.PHONE in document_problems("手機 0912-345-678")
    assert Drop.MARKUP_OR_CODE in document_problems("<b>粗體</b>")
    assert document_problems("我們今天去公園散步") == ()
    assert weird_unicode("ㄧ國兩制") == ("bopomofo",)
    assert weird_unicode("零寬\u200b空白") == ("U+200B",)


# ---------------------------------------------------------------- corpus build


def build(documents: dict[str, list[DailyDocument]], guard: EvaluationGuard | None = None, splitter=None):  # type: ignore[no-untyped-def]
    importers = [ListImporter(s, d) for s, d in documents.items()]
    kwargs = {"splitter": splitter} if splitter else {}
    return DailyCorpusBuilder(importers, SentenceInspector(classifier()), guard or no_guard(), **kwargs).build()  # type: ignore[arg-type]


def test_simplified_text_is_dropped_not_converted() -> None:
    docs = [DailyDocument("s", "1", "我們今天去公園散步。"), DailyDocument("s", "2", "我们今天去公园散步。")]
    kept, stats = build({"s": docs})
    assert [k.text for k in kept] == ["我們今天去公園散步。"]
    assert stats["s"].dropped[Drop.SIMPLIFIED.value] == 1
    assert all(k.text in d.text for k in kept for d in docs if d.doc_id == k.doc_id)


def test_duplicates_are_dropped_within_and_across_sources() -> None:
    kept, stats = build(
        {
            "a": [DailyDocument("a", "1", "我們今天去公園散步。"), DailyDocument("a", "2", "我們今天去公園散步！")],
            "b": [DailyDocument("b", "1", "我們今天，去公園散步。")],
        }
    )
    assert len(kept) == 1
    assert stats["a"].dropped[Drop.DUPLICATE_IN_SOURCE.value] == 1
    assert stats["b"].dropped[Drop.DUPLICATE_OTHER_DAILY.value] == 1


def test_evaluation_overlap_is_excluded() -> None:
    guard = EvaluationGuard([ReferenceSet("coverage_dev", (("cv01", "大家一起唱歌吃飯了沒有"),))], threshold=0.6)
    kept, stats = build({"s": [DailyDocument("s", "1", "大家一起唱歌吃飯了沒有。"), DailyDocument("s", "2", "老師上課下雨帶傘。")]}, guard)
    assert [k.text for k in kept] == ["老師上課下雨帶傘。"]
    assert stats["s"].dropped[Drop.EVAL_OVERLAP.value] == 1
    assert guard.check("他說大家一起唱歌吃飯了") is not None


def test_splits_are_document_level_and_cross_split_near_duplicates_removed() -> None:
    from zaoseq_bopomofo.corpus.sentences import Split

    def splitter(source_id: str, doc_id: str) -> Split:
        return Split.DEV if doc_id.startswith("dev") else Split.TRAIN

    docs = [
        DailyDocument("s", "train1", "我們今天去公園散步。老師上課下雨帶傘。"),
        DailyDocument("s", "dev1", "你好嗎這裡很安靜。我們今天去公園散步了。"),
    ]
    kept, stats = build({"s": docs}, splitter=splitter)
    by_doc: dict[str, set[str]] = {}
    for sentence in kept:
        by_doc.setdefault(sentence.doc_id, set()).add(sentence.split)
    assert all(len(splits) == 1 for splits in by_doc.values())
    assert "我們今天去公園散步了。" not in {k.text for k in kept}
    assert stats["s"].dropped[Drop.CROSS_SPLIT_NEAR_DUP.value] == 1


def test_default_split_is_deterministic() -> None:
    from zaoseq_bopomofo.corpus.sentences import assign_split

    assert [assign_split("tatoeba_cmn_hant", str(i)) for i in range(50)] == [assign_split("tatoeba_cmn_hant", str(i)) for i in range(50)]


# ---------------------------------------------------------------- frequency-aware lexicon


class FixedResolver:
    def resolve(self, text: str, limit: int) -> tuple[tuple[str, ...], ...] | None:
        return (tuple("ㄅ" for _ in text),)


def lexicon_fixture() -> tuple[FrequencyAwareExtractor, dict, list[CorpusSentence]]:  # type: ignore[type-arg]
    sentences: list[CorpusSentence] = []
    for i in range(30):
        sentences.append(CorpusSentence("legal", "gov_a", f"gov_a:{i}", f"主管機關辦理公園維護第{i}次"))
        sentences.append(CorpusSentence("daily", "daily_x", f"daily_x:{i}", "我們今天去公園散步"))
    for i in range(40):
        sentences.append(CorpusSentence("daily", "daily_x", "daily_x:single", "老師上課下雨帶傘"))
    tables = build_tables(sentences, {"legal": 1.0})
    extractor = FrequencyAwareExtractor(tables, FixedResolver(), known={"公園"})  # type: ignore[arg-type]
    candidates = set().union(*(extractor.frequent(p) for p in policies()))
    return extractor, OccurrenceScanner().scan(sentences, candidates), sentences


def policies() -> tuple[ExtractionPolicy, ...]:
    return (
        ExtractionPolicy("raw", PooledEstimator(), min_per_million=1.0, min_documents=2, min_pmi=0.0),
        ExtractionPolicy("daily", InterpolatedEstimator(0.75), min_per_million=1.0, min_documents=5, min_pmi=1.0),
    )


def test_frequency_aware_extraction_is_deterministic() -> None:
    first, occ1, _ = lexicon_fixture()
    second, occ2, _ = lexicon_fixture()
    for policy in policies():
        a = [e.to_json() for e in first.extract(policy, occ1, {"legal"})]
        b = [e.to_json() for e in second.extract(policy, occ2, {"legal"})]
        assert a == b
        assert [row["text"] for row in a] == sorted(row["text"] for row in a)


def test_derived_entries_carry_provenance_and_filters() -> None:
    extractor, occurrences, _ = lexicon_fixture()
    entries = {e.text: e for e in extractor.extract(policies()[0], occurrences, {"legal"})}
    assert entries["公園"].eligibility == "known_builtin"
    assert entries["帶傘"].eligibility == "too_few_documents"
    eligible = [e for e in entries.values() if e.eligible]
    assert eligible
    low, high = policies()[0].weight_bounds
    for entry in eligible:
        assert entry.daily_count + entry.government_count == entry.corpus_count
        assert entry.corpus_count == sum(entry.domain_distribution.values())
        assert entry.document_count >= 2 and entry.source_ids and entry.provenance and entry.readings
        assert set(entry.source_ids) <= {"gov_a", "daily_x"}
        assert low <= entry.weight <= high and math.isfinite(entry.pmi)
    ordered = sorted(eligible, key=lambda e: e.estimated_frequency)
    assert [e.weight for e in ordered] == sorted(e.weight for e in ordered)


def test_fragments_are_not_eligible() -> None:
    extractor, occurrences, _ = lexicon_fixture()
    entries = {e.text: e for e in extractor.extract(policies()[0], occurrences, {"legal"})}
    assert entries["主管機"].eligibility == "fragment_of_longer_ngram"
    assert entries["主管機關"].eligible


def test_interpolated_estimator_weights_daily_counts() -> None:
    extractor, occurrences, _ = lexicon_fixture()
    daily_word = next(e for e in extractor.extract(policies()[1], occurrences, {"legal"}) if e.text == "散步")
    pooled_word = next(e for e in extractor.extract(policies()[0], occurrences, {"legal"}) if e.text == "散步")
    assert daily_word.government_count == 0
    assert daily_word.estimated_frequency > pooled_word.estimated_frequency


# ---------------------------------------------------------------- mixture LM invariants


def small_lm(texts: list[str]) -> CorpusLanguageModel:
    return CorpusLanguageModel(count_ngrams(texts, min_trigram_count=1), vocabulary_size=200)


def test_mixture_single_component_is_bitwise_identical() -> None:
    gov = small_lm(["我們今天去公園散步", "老師上課"])
    mix = MixtureLanguageModel([("gov", gov, 1.0), ("daily", small_lm(["你好嗎"]), 0.0)])
    for text in ("我們今天", "你好嗎這裡", "雨"):
        assert mix.score(text, "他說") == gov.score(text, "他說")


def test_mixture_is_weighted_sum_and_validates() -> None:
    a, b = small_lm(["我們今天去公園散步"]), small_lm(["你好嗎這裡很安靜"])
    mix = MixtureLanguageModel([("a", a, 0.25), ("b", b, 0.75)])
    for token, history in (("們", "^我"), ("嗎", "你好"), ("雨", "^^")):
        assert mix.probability(token, history) == pytest.approx(0.25 * a.probability(token, history) + 0.75 * b.probability(token, history))
    with pytest.raises(ValueError):
        MixtureLanguageModel([("a", a, 0.5), ("b", b, 0.6)])
    with pytest.raises(ValueError):
        MixtureLanguageModel([("a", a, 0.0)])


def test_selection_rule_respects_gov_constraint() -> None:
    from zaoseq_bopomofo.daily.experiments import SelectionRule

    def result(cov_r5: float, gov_r1: float, window: float = 0.5) -> dict:  # type: ignore[type-arg]
        return {
            "coverage_dev": {"metrics": {"recall": {"@5": cov_r5}, "window_recall_top4_families": window}},
            "gov_dev": {"metrics": {"recall": {"@1": gov_r1}}},
        }

    base = result(0.7, 0.6)
    choice = SelectionRule().select({"x": result(0.9, 0.5), "y": result(0.8, 0.59), "z": result(0.8, 0.595, 0.6)}, base)
    assert choice["selected"] == "z" and choice["constraint_satisfied"]
    fallback = SelectionRule().select({"x": result(0.9, 0.5), "y": result(0.8, 0.55)}, base)
    assert fallback["selected"] == "y" and not fallback["constraint_satisfied"]


# ---------------------------------------------------------------- selection plan


def score(name: str, **changes: object):  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.selection import ConfigScore

    base = ConfigScore(name, True, 0.80, 0.86, 0.70, 5, 0.5, 0.6, 0.8, 0.75, 200.0, 10.0, 1.0)
    return replace(base, **changes)  # type: ignore[arg-type]


def test_selection_plan_is_frozen() -> None:
    from zaoseq_bopomofo.daily.selection import PLAN_RECORD, SelectionPlan
    from zaoseq_bopomofo.evaluation.freeze import verify

    assert verify(PLAN_RECORD) == {"changed": [], "missing": []}
    plan = SelectionPlan()
    assert plan.gov_baseline_max_drop == 0.02 and plan.gov_teacher_max_drop == 0.02
    assert [layer["name"] for layer in plan.plan["rule"]] == ["production_eligibility", "regression_gates", "primary", "tie_break"]


def test_selection_plan_detects_changes(tmp_path: Path) -> None:
    import json

    from zaoseq_bopomofo.daily.selection import PLAN_FILE, PLAN_RECORD, PlanChangedError, SelectionPlan
    from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

    record = json.loads(PLAN_RECORD.read_text(encoding="utf-8"))
    record["files"] = {PLAN_FILE.relative_to(PROJECT_ROOT).as_posix(): "0" * 64}
    fake = tmp_path / "record.json"
    fake.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(PlanChangedError):
        SelectionPlan(record_file=fake)


def test_selection_rule_gates_primary_and_tie_break() -> None:
    from zaoseq_bopomofo.daily.selection import Reference, SelectionPlan

    plan = SelectionPlan()
    reference = Reference(gov_baseline_top1=0.80, gov_teacher_top1=0.86)
    scores = [
        score("dev_only", production_eligible=False, coverage_teacher_top1=0.95),
        score("gov_drop", gov_baseline_top1=0.775, coverage_teacher_top1=0.90),
        score("teacher_drop", gov_teacher_top1=0.835, coverage_teacher_top1=0.90),
        score("best", coverage_teacher_top1=0.780, coverage_teacher_correct_to_wrong=9),
        score("near_tie", coverage_teacher_top1=0.780 - 1 / 300, coverage_teacher_correct_to_wrong=4),
        score("behind", coverage_teacher_top1=0.770, coverage_teacher_correct_to_wrong=0),
    ]
    decision = plan.select(scores, reference)
    assert decision.failed_gates == {
        "dev_only": ("not_production_eligible",),
        "gov_drop": ("gov_baseline_regression",),
        "teacher_drop": ("gov_teacher_regression",),
    }
    assert decision.selected == "near_tie"
    assert decision.tie_set == ("near_tie", "best")
    edge = plan.select([score("edge", gov_baseline_top1=0.78, gov_teacher_top1=0.84)], reference)
    assert edge.selected == "edge"


# ---------------------------------------------------------------- Round 2: readings, compact lexicon, LM cache


class Row:
    def __init__(self, char: str, reading: str) -> None:
        self.char, self.reading = char, reading


class Builtin:
    def __init__(self, text: str, readings: tuple[str, ...] | None) -> None:
        self.text, self.readings = text, readings


def evidence():  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.clean_lexicon import ReadingEvidence

    chars = [
        Row("銀", "ㄧㄣˊ"),
        Row("行", "ㄏㄤˊ"),
        Row("行", "ㄒㄧㄥˊ"),
        Row("卡", "ㄎㄚˇ"),
        Row("卡", "ㄑㄧㄚˇ"),
        Row("的", "ㄉㄜ˙"),
        Row("的", "ㄉㄧˋ"),
        Row("好", "ㄏㄠˇ"),
        Row("人", "ㄖㄣˊ"),
    ]
    return ReadingEvidence(chars, [Builtin("銀行", ("ㄧㄣˊ", "ㄏㄤˊ")), Builtin("的", ("ㄉㄜ˙",))])


def test_reading_policies_never_expand_cartesian_products() -> None:
    from zaoseq_bopomofo.daily.clean_lexicon import BoundedReadings, CartesianReadings, KnownWordReadings, UnambiguousReadings

    ev = evidence()
    r1, r2, r3 = UnambiguousReadings(ev), KnownWordReadings(ev), BoundedReadings(ev)
    assert r1.readings("好人") == (("ㄏㄠˇ", "ㄖㄣˊ"),)
    assert r1.readings("銀行") is None
    assert r2.readings("銀行卡") is None
    assert r2.readings("好銀行") == (("ㄏㄠˇ", "ㄧㄣˊ", "ㄏㄤˊ"),)
    assert r2.readings("好的") is None and r3.readings("好的") == (("ㄏㄠˇ", "ㄉㄜ˙"),)
    for policy in (r1, r2, r3):
        for word in ("銀行卡", "行卡", "好的", "好人", "卡行"):
            result = policy.readings(word)
            assert result is None or len(result) == 1
    cartesian = CartesianReadings(ev, {"行": ["ㄏㄤˊ", "ㄒㄧㄥˊ"], "卡": ["ㄎㄚˇ", "ㄑㄧㄚˇ"]})
    assert len(cartesian.readings("行卡")) == 4  # type: ignore[arg-type]


def test_unambiguous_policy_only_uses_single_reading_characters() -> None:
    from zaoseq_bopomofo.daily.clean_lexicon import ReadingEvidence, UnambiguousReadings

    real = ReadingEvidence.load()
    policy = UnambiguousReadings(real)
    for word in ("我們", "銀行", "今天", "學校", "星期"):
        result = policy.readings(word)
        if result is not None:
            assert all(len(real.cns[c]) == 1 and real.cns[c][0] == r for c, r in zip(word, result[0]))


def small_lexicon():  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.lexicon.entry import EntrySource, LexiconEntry
    from zaoseq_bopomofo.lexicon.lexicon import Lexicon

    rows = [
        ("我們", ("ㄨㄛˇ", "ㄇㄣ˙"), 200.0, EntrySource.BUILTIN),
        ("我", ("ㄨㄛˇ",), 1.0, EntrySource.CNS11643),
        ("握", ("ㄨㄛˋ",), 0.1, EntrySource.CNS11643),
        ("沃", ("ㄨㄛˋ",), 0.1, EntrySource.CNS11643),
        ("們", ("ㄇㄣ˙",), 1.0, EntrySource.CNS11643),
        ("散步", ("ㄙㄢˋ", "ㄅㄨˋ"), 10.0, EntrySource.BUILTIN),
        ("散", ("ㄙㄢˋ",), 1.0, EntrySource.CNS11643),
        ("步", ("ㄅㄨˋ",), 1.0, EntrySource.CNS11643),
        ("布", ("ㄅㄨˋ",), 1.0, EntrySource.CNS11643),
    ]
    return Lexicon(LexiconEntry(t, r, f, s) for t, r, f, s in rows)


def test_compact_lexicon_roundtrip_is_exactly_equivalent(tmp_path: Path) -> None:
    from zaoseq_bopomofo.daily.compact import CompactLexicon, CompactLexiconWriter, LexiconSnapshot

    lexicon = small_lexicon()
    path = tmp_path / "lex.bin"
    CompactLexiconWriter().write(LexiconSnapshot.of(lexicon), path)
    compact = CompactLexicon(path, cache_size=2)
    assert len(compact) == len(lexicon)
    assert compact.words() == lexicon.words() and compact.syllables == lexicon.syllables
    assert compact.max_word_length == lexicon.max_word_length
    for reading in [("ㄨㄛˇ",), ("ㄨㄛˋ",), ("ㄨㄛˇ", "ㄇㄣ˙"), ("ㄙㄢˋ", "ㄅㄨˋ"), ("ㄅㄨˋ",), ("ㄓ",), ("ㄨㄛˋ",)]:
        assert compact.lookup(reading) == lexicon.lookup(reading)
        for a, b in zip(compact.lookup(reading), lexicon.lookup(reading)):
            assert compact.log10_probability(a) == lexicon.log10_probability(b)


def test_compact_artifact_build_is_deterministic(tmp_path: Path) -> None:
    from zaoseq_bopomofo.daily.compact import CompactLexiconWriter, LexiconSnapshot

    snapshot = LexiconSnapshot.of(small_lexicon())
    CompactLexiconWriter().write(snapshot, tmp_path / "a.bin", {"散步": 7})
    CompactLexiconWriter().write(snapshot, tmp_path / "b.bin", {"散步": 7})
    assert (tmp_path / "a.bin").read_bytes() == (tmp_path / "b.bin").read_bytes()


def test_runtime_provenance_ids_recover_manifest_records(tmp_path: Path) -> None:
    from zaoseq_bopomofo.daily.compact import CompactLexicon, CompactLexiconWriter, LexiconSnapshot, ProvenanceTable
    from zaoseq_bopomofo.daily.lexicon import DerivedLexiconEntry

    derived = DerivedLexiconEntry("散步", (("ㄙㄢˋ", "ㄅㄨˋ"),), 5, 3, 5, 0, {"daily": 5}, 6.0, 1.0, 10.0, ("tatoeba_cmn_hant",), "recipe", "eligible")
    table = ProvenanceTable([derived])
    CompactLexiconWriter().write(LexiconSnapshot.of(small_lexicon()), tmp_path / "lex.bin", table.ids)
    table.write(tmp_path / "provenance.json")
    compact = CompactLexicon(tmp_path / "lex.bin")
    records = ProvenanceTable.read(tmp_path / "provenance.json")
    ids = dict(zip((e.text for e in compact.lookup(("ㄙㄢˋ", "ㄅㄨˋ"))), compact.provenance_ids(("ㄙㄢˋ", "ㄅㄨˋ"))))
    assert records[ids["散步"]]["source_ids"] == ["tatoeba_cmn_hant"]
    assert compact.provenance_ids(("ㄨㄛˇ",)) == (0,)


def test_compact_lexicon_gives_identical_decoder_output(tmp_path: Path) -> None:
    from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig
    from zaoseq_bopomofo.daily.compact import CompactLexicon, CompactLexiconWriter, LexiconSnapshot
    from zaoseq_bopomofo.decoding.scoring import LinearScorer

    lexicon = small_lexicon()
    CompactLexiconWriter().write(LexiconSnapshot.of(lexicon), tmp_path / "lex.bin")
    lm = small_lm(["我們散步", "我們在散步", "握手"])
    readings = ("ㄨㄛˇ", "ㄇㄣ˙", "ㄙㄢˋ", "ㄅㄨˋ")
    scorer = LinearScorer(corpus_weight=1.0, lexical_weight=1.0)
    compact = CompactLexicon(tmp_path / "lex.bin")
    a = CoverageLattice(lexicon, lm, scorer, GenerationConfig(beam=4, nbest=10)).generate(readings).candidates
    b = CoverageLattice(compact, lm, scorer, GenerationConfig(beam=4, nbest=10)).generate(readings).candidates  # type: ignore[arg-type]
    assert [(c.text, c.baseline_score) for c in a] == [(c.text, c.baseline_score) for c in b]


def test_cached_language_model_is_exactly_equivalent() -> None:
    from zaoseq_bopomofo.daily.mixture import CachedLanguageModel

    inner = MixtureLanguageModel([("a", small_lm(["我們今天去公園散步"]), 0.75), ("b", small_lm(["你好嗎這裡很安靜"]), 0.25)])
    cached = CachedLanguageModel(inner, max_entries=3)
    for history, char in [("^^", "我"), ("^我", "們"), ("^^", "我"), ("好嗎", "這"), ("^我", "們"), ("xx", "雨")] * 2:
        assert cached.extend(history, char) == inner.extend(history, char)
    assert cached.hits > 0
    assert cached.score("我們今天", "他說") == inner.score("我們今天", "他說")


class SingleReading:
    name = "fixture_reading"
    single_reading = True

    def readings(self, text: str) -> tuple[tuple[str, ...], ...]:
        return (tuple("ㄅ" for _ in text),)


def clean_fixture():  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.clean_lexicon import CandidateStatistics

    sentences: list[CorpusSentence] = []
    for i in range(40):
        sentences.append(CorpusSentence("legal", f"gov_{i % 4}", f"gov_{i % 4}:{i}", f"依第{i % 9 + 1}條第{'二三四五'[i % 4]}項規定辦理登記"))
        sentences.append(CorpusSentence("legal", f"gov_{i % 4}", f"gov_{i % 4}:{i}", "主管機關應公告登記事項"))
        sentences.append(CorpusSentence("daily", "daily_x", f"daily_x:{i}", ("我們今天去公園散步", "晚飯後出門散步")[i % 2]))
        sentences.append(CorpusSentence("daily", "daily_x", f"daily_x:b{i}", "辦理登記很麻煩"))
    CandidateStatistics.POOLED_MIN_PER_MILLION = 1.0
    try:
        return CandidateStatistics(build_tables(sentences, {"legal": 1.0}), sentences, known={"公園"})
    finally:
        CandidateStatistics.POOLED_MIN_PER_MILLION = 2.0


def test_generalizable_filters_use_statistics_not_word_lists() -> None:
    from zaoseq_bopomofo.daily.clean_lexicon import DailyOnlyFilter, DailySupportedFilter, DocumentFrequencyFilter, DomainRatioFilter, MixedFilter

    ctx = clean_fixture()
    stats = ctx.stats
    assert "公園" not in stats
    assert MixedFilter().reject(stats["登記"], ctx) is None
    assert DomainRatioFilter().reject(stats["條第"], ctx) in ("numeral_template", "government_domain_concentrated")
    assert MixedFilter().reject(stats["條第"], ctx) is None
    assert stats["條第"].numeral_share >= 0.5
    assert DomainRatioFilter().reject(stats["主管機關"], ctx) == "government_domain_concentrated"
    assert DailySupportedFilter().reject(stats["主管機關"], ctx) == "no_daily_support"
    assert DailySupportedFilter().reject(stats["登記"], ctx) is None
    assert DailyOnlyFilter().reject(stats["散步"], ctx) is None
    assert DailyOnlyFilter().reject(stats["主管機關"], ctx) == "below_daily_count"
    assert DocumentFrequencyFilter().reject(stats["散步"], ctx) == "too_few_sources"


def test_clean_lexicon_factory_is_deterministic_with_provenance() -> None:
    from zaoseq_bopomofo.daily.clean_lexicon import PRIORS, CleanLexiconFactory, LexiconRecipe, MixedFilter

    ctx = clean_fixture()
    for prior in PRIORS:
        recipe = LexiconRecipe(SingleReading(), MixedFilter(), prior())  # type: ignore[arg-type]
        first = CleanLexiconFactory(ctx, {"legal"}).build(recipe)
        second = CleanLexiconFactory(clean_fixture(), {"legal"}).build(recipe)
        assert [e.to_json() for e in first.entries] == [e.to_json() for e in second.entries]
        assert [e.text for e in first.entries] == sorted(e.text for e in first.entries)
        for entry in first.entries:
            assert len(entry.readings) == 1 and entry.provenance == recipe.name
            assert 3.0 <= entry.weight <= 200.0
            assert entry.daily_count + entry.government_count == entry.corpus_count
            assert set(entry.source_ids) <= {"gov_0", "gov_1", "gov_2", "gov_3", "daily_x"}


def test_priors_follow_their_fixed_mappings() -> None:
    from zaoseq_bopomofo.daily.clean_lexicon import FlatPrior, GramStats, LogPrior, RankBucketPrior, RawPrior

    stats = [GramStats(f"詞{i}", pooled_frequency=(i + 1) * 1e-6, pooled_pmi=1.0, fragment_share=0.0) for i in range(10)]
    assert FlatPrior().weights(stats) == [10.0] * 10
    raw = RawPrior().weights(stats)
    assert raw == sorted(raw) and all(3.0 <= w <= 200.0 for w in raw)
    log = LogPrior().weights(stats)
    assert log == sorted(log) and all(3.0 <= w <= 200.0 for w in log)
    buckets = RankBucketPrior().weights(stats)
    assert sorted(buckets, reverse=True) == [50.0, 20.0, 20.0, 10.0, 10.0, 10.0, 10.0, 3.0, 3.0, 3.0]
