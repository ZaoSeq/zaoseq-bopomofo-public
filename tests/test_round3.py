from __future__ import annotations

import json

import pytest

from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams
from zaoseq_bopomofo.daily.mixture import BoundedLanguageModelCache, MixtureLanguageModel
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

CALLS = [("^^", "我"), ("^我", "們"), ("^^", "你"), ("^我", "們"), ("好嗎", "這"), ("^^", "我"), ("xx", "雨"), ("^我", "們")] * 3


def mixture() -> MixtureLanguageModel:
    a = CorpusLanguageModel(count_ngrams(["我們今天去公園散步"], min_trigram_count=1), vocabulary_size=200)
    b = CorpusLanguageModel(count_ngrams(["你好嗎這裡很安靜"], min_trigram_count=1), vocabulary_size=200)
    return MixtureLanguageModel([("a", a, 0.5), ("b", b, 0.5)])


def test_round3_addendum_is_frozen_and_keeps_parent_plan() -> None:
    from zaoseq_bopomofo.evaluation.freeze import content_hash, verify

    assert verify(PROJECT_ROOT / "benchmarks" / "frozen" / "V0.2_ROUND3.json") == {"changed": [], "missing": []}
    addendum = json.loads((PROJECT_ROOT / "benchmarks" / "frozen" / "v0.2_round3_addendum.json").read_text(encoding="utf-8"))
    parent = addendum["parent_plan"]
    assert content_hash(PROJECT_ROOT / parent["file"]) == parent["sha256"]
    capacities = addendum["cache_policy"]["candidates"]
    assert capacities["disabled"] == 0 and capacities["unbounded_reference"] is None
    assert all(isinstance(capacities[k], int) and capacities[k] > 0 for k in ("bounded_8mb", "bounded_16mb", "bounded_32mb"))


@pytest.mark.parametrize("capacity", [0, 1, 3, 100, None])
def test_bounded_cache_is_exactly_equivalent(capacity: int | None) -> None:
    inner = mixture()
    cached = BoundedLanguageModelCache(inner, capacity)
    for history, char in CALLS:
        assert cached.extend(history, char) == inner.extend(history, char)
    assert cached.score("我們今天", "他說") == inner.score("我們今天", "他說")
    if capacity is not None:
        assert cached.entries <= capacity


def test_bounded_cache_eviction_is_deterministic_lru() -> None:
    first, second = BoundedLanguageModelCache(mixture(), 2), BoundedLanguageModelCache(mixture(), 2)
    for cache in (first, second):
        for history, char in CALLS:
            cache.extend(history, char)
    assert first.stats() == second.stats()
    assert list(first._cache) == list(second._cache)  # noqa: SLF001
    assert first.evictions > 0 and first.hits > 0
    lru = BoundedLanguageModelCache(mixture(), 2)
    lru.extend("^^", "我")
    lru.extend("^我", "們")
    lru.extend("^^", "我")
    lru.extend("xx", "雨")
    assert list(lru._cache) == [("^^", "我"), ("xx", "雨")]  # noqa: SLF001


def test_disabled_cache_never_stores_and_negative_capacity_is_rejected() -> None:
    cache = BoundedLanguageModelCache(mixture(), 0)
    for history, char in CALLS:
        cache.extend(history, char)
    assert cache.entries == 0 and cache.hits == 0 and cache.misses == len(CALLS)
    assert bool(cache)
    with pytest.raises(ValueError):
        BoundedLanguageModelCache(mixture(), -1)


@pytest.mark.parametrize("capacity", [0, 5, None])
def test_cached_lattice_output_matches_uncached_from_the_first_case(capacity: int | None) -> None:
    from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig
    from zaoseq_bopomofo.decoding.scoring import LinearScorer
    from zaoseq_bopomofo.lexicon.entry import EntrySource, LexiconEntry
    from zaoseq_bopomofo.lexicon.lexicon import Lexicon

    lexicon = Lexicon(
        LexiconEntry(t, r, f, s)
        for t, r, f, s in [
            ("我們", ("ㄨㄛˇ", "ㄇㄣ˙"), 200.0, EntrySource.BUILTIN),
            ("我", ("ㄨㄛˇ",), 1.0, EntrySource.CNS11643),
            ("握", ("ㄨㄛˇ",), 0.5, EntrySource.CNS11643),
            ("們", ("ㄇㄣ˙",), 1.0, EntrySource.CNS11643),
            ("門", ("ㄇㄣ˙",), 0.5, EntrySource.CNS11643),
        ]
    )
    scorer = LinearScorer(corpus_weight=1.0, lexical_weight=1.0)
    readings = ("ㄨㄛˇ", "ㄇㄣ˙")
    inner = mixture()
    plain = CoverageLattice(lexicon, inner, scorer, GenerationConfig()).generate(readings, "").candidates
    cached = CoverageLattice(lexicon, BoundedLanguageModelCache(inner, capacity), scorer, GenerationConfig()).generate(readings, "").candidates
    assert [(c.text, c.baseline_score) for c in plain] == [(c.text, c.baseline_score) for c in cached]


CV_ARCHIVE = "common-voice-scripted-speech-27-0-chines-aea50ebd.tar.gz"
CV_SENTENCES = "sentence_id\tsentence\tsentence_domain\tsource\tis_used\tclips_count\n" + "".join(
    f"{i}\t{t}\t\tsrc\t1\t3\n"
    for i, t in [("s1", "我們今天去公園散步。"), ("s2", "你好嗎這裡很安靜。"), ("s1", "我們今天去公園散步。"), ("s3", "你好嗎這裡很安靜。"), ("s4", "我们今天去公园散步。"), ("s5", "大家一起唱歌吃飯了沒有。")]
)
CV_CLIPS = "client_id\tpath\tsentence_id\tsentence\tsentence_domain\tup_votes\tdown_votes\tage\tgender\taccents\tvariant\tlocale\tsegment\n" + "".join(
    f"speaker{n}\tclip{n}.mp3\t{i}\t{t}\t\t2\t0\ttwenties\tmale\tTaipei\t\tzh-TW\t\n"
    for n, (i, t) in enumerate([("s1", "我們今天去公園散步。"), ("s1", "我們今天去公園散步。"), ("s2", "老師上課下雨帶傘。")])
)


def cv_archive(root, members: dict[str, str]):  # type: ignore[no-untyped-def]
    import io
    import tarfile

    path = root / "mdc_common_voice_zh_tw_27_0" / CV_ARCHIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as archive:
        for name, text in members.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return path


def cv_registry(path, **changes: object):  # type: ignore[no-untyped-def]
    import hashlib
    from dataclasses import replace

    from zaoseq_bopomofo.daily.sources import ApprovalScope, DailySource, SourceFile, SourceRegistry, Status, TrainingBasis

    record = SourceFile(f"mdc_common_voice_zh_tw_27_0/{CV_ARCHIVE}", "https://mozilladatacollective.com/datasets/x", hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
    source = DailySource(
        "mdc_common_voice_zh_tw_27_0", "cv", "Mozilla", "https://mozilladatacollective.com", ("https://mozilladatacollective.com",), "27.0", "2026-09-25",
        "CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/", "yes", "yes", "no", "not required", "yes", TrainingBasis.INFERRED, "CC0",
        "sentences", "high", ("sentence_id", "sentence"), ("client_id",), "sentence id", (record,), Status.APPROVED, ApprovalScope.PRODUCTION, "fixture",
    )
    return SourceRegistry([replace(source, **changes)])


def cv_importer(tmp_path, members: dict[str, str], **changes: object):  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.importers import CommonVoiceImporter
    from zaoseq_bopomofo.daily.sources import Purpose, RawFiles

    path = cv_archive(tmp_path, members)
    return CommonVoiceImporter(cv_registry(path, **changes), raw=RawFiles(tmp_path), purpose=Purpose.PRODUCTION)


def test_common_voice_reads_only_zh_tw_sentence_ids_and_texts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    importer = cv_importer(
        tmp_path,
        {
            "cv-corpus-27.0/zh-CN/validated_sentences.tsv": "sentence_id\tsentence\nc1\t我们去公园。\n",
            "cv-corpus-27.0/zh-TW/validated.tsv": CV_CLIPS,
            "cv-corpus-27.0/zh-TW/validated_sentences.tsv": CV_SENTENCES,
        },
    )
    documents = list(importer.documents())
    assert importer.table == "validated_sentences.tsv"
    assert [(d.doc_id, d.text) for d in documents] == [("s1", "我們今天去公園散步。"), ("s2", "你好嗎這裡很安靜。"), ("s4", "我们今天去公园散步。"), ("s5", "大家一起唱歌吃飯了沒有。")]
    assert importer.duplicate_ids == 1 and importer.duplicate_texts == 1
    assert all(d.contributor == "" for d in documents)


def test_common_voice_fallback_counts_each_sentence_once_without_speaker_data(tmp_path) -> None:  # type: ignore[no-untyped-def]
    importer = cv_importer(tmp_path, {"cv-corpus-27.0/zh-TW/validated.tsv": CV_CLIPS, "cv-corpus-27.0/zh-TW/clips/clip0.mp3": "audio"})
    documents = list(importer.documents())
    assert importer.table == "validated.tsv"
    assert [(d.doc_id, d.text) for d in documents] == [("s1", "我們今天去公園散步。"), ("s2", "老師上課下雨帶傘。")]
    dumped = repr(documents)
    assert not any(word in dumped for word in ("speaker", "clip", "twenties", "male", "Taipei"))


def test_common_voice_is_gated_before_the_archive_is_read(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.sources import ApprovalScope, LicenseError, Status

    members = {"cv-corpus-27.0/zh-TW/validated_sentences.tsv": CV_SENTENCES}
    with pytest.raises(LicenseError, match="status HOLD"):
        next(cv_importer(tmp_path, members, status=Status.HOLD, approval_scope=ApprovalScope.NONE).documents())
    with pytest.raises(LicenseError, match="approval_scope"):
        next(cv_importer(tmp_path, members, approval_scope=ApprovalScope.DEV_EXPERIMENT).documents())
    with pytest.raises(LicenseError, match="沒有 zh-TW"):
        next(cv_importer(tmp_path, {"cv-corpus-27.0/zh-CN/validated_sentences.tsv": CV_SENTENCES}).documents())


def test_common_voice_goes_through_the_daily_builder_without_conversion(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.corpus import DailyCorpusBuilder
    from zaoseq_bopomofo.daily.guard import EvaluationGuard, ReferenceSet
    from zaoseq_bopomofo.daily.quality import Drop, SentenceInspector
    from zaoseq_bopomofo.daily.script import ScriptClassifier

    standard = set("我們今天去公園散步你好嗎這裡很安靜大家一起唱歌吃飯了沒有")
    guard = EvaluationGuard([ReferenceSet("coverage_dev", (("cv01", "大家一起唱歌吃飯了沒有"),))], threshold=0.6)
    importer = cv_importer(tmp_path, {"cv-corpus-27.0/zh-TW/validated_sentences.tsv": CV_SENTENCES})
    kept, stats = DailyCorpusBuilder([importer], SentenceInspector(ScriptClassifier(standard, simplified_characters=set("们园"))), guard).build()
    assert sorted(k.text for k in kept) == ["你好嗎這裡很安靜。", "我們今天去公園散步。"]
    quality = stats["mdc_common_voice_zh_tw_27_0"]
    assert quality.dropped[Drop.SIMPLIFIED.value] == 1 and quality.dropped[Drop.EVAL_OVERLAP.value] == 1
    assert not quality.contributors


def test_raw_common_voice_is_never_tracked() -> None:
    import subprocess

    from zaoseq_bopomofo.daily.importers import CommonVoiceImporter
    from zaoseq_bopomofo.daily.sources import SourceRegistry

    source = SourceRegistry.load()[CommonVoiceImporter.source_id]
    raw = [f"data/raw/daily/{f.path}" for f in source.files] + ["data/raw/daily/mdc_common_voice_zh_tw_27_0/clips/x.mp3", "data/raw/daily/mdc_common_voice_zh_tw_27_0/validated.tsv"]
    for path in (*raw, "data/daily/corpus/mdc_common_voice_zh_tw_27_0/sentences.jsonl"):
        assert subprocess.run(["git", "check-ignore", "-q", path], cwd=PROJECT_ROOT).returncode == 0, path
    tracked = subprocess.run(["git", "ls-files", "data/raw/daily"], cwd=PROJECT_ROOT, capture_output=True, text=True).stdout.split()
    assert not [p for p in tracked if "common_voice" in p]


def test_stage5_candidates_follow_approval_and_lm_sources() -> None:
    from zaoseq_bopomofo.daily.corpus_ablation import COMMON_VOICE, TATOEBA, available_candidates

    lms = {TATOEBA: {TATOEBA}, COMMON_VOICE: {COMMON_VOICE}, "daily_production": {TATOEBA, COMMON_VOICE}}
    assert [c.name for c in available_candidates({TATOEBA, COMMON_VOICE}, lambda n: lms.get(n, set()))] == ["S5_tatoeba", "S5_common_voice", "S5_tatoeba_common_voice"]
    assert [c.name for c in available_candidates({TATOEBA}, lambda n: lms.get(n, set()))] == ["S5_tatoeba"]
    stale = {**lms, "daily_production": {TATOEBA}}
    assert [c.name for c in available_candidates({TATOEBA, COMMON_VOICE}, lambda n: stale.get(n, set()))] == ["S5_tatoeba", "S5_common_voice"]


def test_common_voice_27_is_approved_only_as_the_exact_release() -> None:
    from zaoseq_bopomofo.daily.sources import ApprovalScope, LicenseGate, Purpose, SourceRegistry, Status

    registry = SourceRegistry.load()
    source = registry["mdc_common_voice_zh_tw_27_0"]
    assert source.status is Status.APPROVED and source.approval_scope is ApprovalScope.PRODUCTION
    assert LicenseGate().problems(source, Purpose.PRODUCTION) == []
    assert source.version.startswith("cv-corpus-27.0-2026-09-11")
    assert source.license_name.startswith("CC0 1.0") and source.training_use.startswith("yes") and source.commercial_use.startswith("yes")
    assert source.redistribution.startswith("no") and any("identify" in r for r in source.platform_restrictions)
    names = [f.path.rsplit("/", 1)[1] for f in source.files]
    assert names == ["1789493066987-cv-corpus-27.0-2026-09-11-zh-TW.tar.gz", "README.md", "validated_sentences.tsv"]
    assert source.files[0].sha256 == "96615945c476f795e03b666d1793b5e7fa8f080bfe92cb73c54fcf6254e2b094" and source.files[0].bytes == 3173160333
    assert source.fields_used == ("sentence_id", "sentence") and "client_id" in source.fields_excluded
    for other in ("cv_sentence_collector_zh_tw", "mdc_common_voice_zh_tw", "cv_zh_tw_chatlogs", "cv_zh_tw_taipei_city_gov"):
        assert registry[other].status is Status.HOLD


def test_common_voice_reads_the_verified_extracted_sentence_table(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import hashlib
    from dataclasses import replace

    from zaoseq_bopomofo.daily.importers import CommonVoiceImporter
    from zaoseq_bopomofo.daily.sources import Purpose, RawFiles, SourceFile, SourceRegistry

    directory = tmp_path / "mdc_common_voice_zh_tw_27_0"
    directory.mkdir()
    (directory / "validated_sentences.tsv").write_text(CV_SENTENCES, encoding="utf-8")
    (directory / "validated.tsv").write_text(CV_CLIPS, encoding="utf-8")
    path = directory / "validated_sentences.tsv"
    record = SourceFile("mdc_common_voice_zh_tw_27_0/validated_sentences.tsv", "https://mozilladatacollective.com", hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
    base = cv_registry(cv_archive(tmp_path, {}))
    registry = SourceRegistry([replace(base["mdc_common_voice_zh_tw_27_0"], files=(record,))])
    importer = CommonVoiceImporter(registry, raw=RawFiles(tmp_path), purpose=Purpose.PRODUCTION)
    documents = list(importer.documents())
    assert importer.table == "validated_sentences.tsv"
    assert [d.doc_id for d in documents] == ["s1", "s2", "s4", "s5"]
    assert "speaker" not in repr(documents)


def test_round3_systems_keep_the_round2_winner_on_the_tatoeba_lm() -> None:
    from zaoseq_bopomofo.daily.corpus_ablation import TATOEBA, lm_sources
    from zaoseq_bopomofo.daily.round3 import ROUND2_WINNER

    assert ROUND2_WINNER.daily_lm == TATOEBA and ROUND2_WINNER.daily_weight == 0.5
    assert lm_sources(TATOEBA) in (set(), {TATOEBA})


def test_round3_winner_config_is_the_stage5_selection() -> None:
    from zaoseq_bopomofo.daily.corpus_ablation import CANDIDATES, lm_sources
    from zaoseq_bopomofo.daily.round3 import CACHE_CANDIDATES, ROUND2_LEXICON, ROUND3_WINNER, PROVISIONAL_CAPACITY

    pooled = next(c for c in CANDIDATES if c.name == "S5_tatoeba_common_voice")
    assert ROUND3_WINNER.daily_lm == pooled.daily_lm and ROUND3_WINNER.daily_weight == 0.5
    assert ROUND3_WINNER.lexicon_path is not None and ROUND3_WINNER.lexicon_path.parent.name == pooled.name
    assert ROUND3_WINNER.lexicon_path.name == ROUND2_LEXICON.name
    assert lm_sources(pooled.daily_lm) in (set(), set(pooled.sources))
    assert CACHE_CANDIDATES[PROVISIONAL_CAPACITY] == 22000
