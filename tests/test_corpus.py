from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from zaoseq_bopomofo.corpus.annotate import Annotation, ReadingAnnotator, Rejection, RejectReason
from zaoseq_bopomofo.corpus.importer import RawDocument, SourceIntegrityError, verify
from zaoseq_bopomofo.corpus.normalize import normalize_text
from zaoseq_bopomofo.corpus.sentences import Split, assign_split, build_sentences, dedupe_key, split_sentences
from zaoseq_bopomofo.corpus.source import SourceKind, SourceStatus, load_registry
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams, load_counts, save_counts, tokenize
from zaoseq_bopomofo.lexicon.builder import BuiltinRow
from zaoseq_bopomofo.lexicon.entry import CharReading

ROOT = Path(__file__).resolve().parents[1]


def test_registry_sources_are_all_production_ready_or_explicitly_blocked() -> None:
    registry = load_registry()
    assert {s.id for s in registry.sources} >= {"cns11643", "moj_law_zh", "mofa_press_zh"}
    for record in registry.sources:
        if record.status is SourceStatus.APPROVED:
            assert record.production_ready, (record.id, record.production_issues())
        assert record.license and record.official_dataset_url.startswith("https://data.gov.tw/dataset/")
    assert any(r["id"] == "wikipedia" for r in registry.rejected_sources)


def test_unknown_license_field_blocks_production() -> None:
    record = load_registry().get("gsn_qa")
    assert not replace(record, ai_training="unknown").production_ready
    assert not replace(record, commercial_use="").production_ready
    assert not replace(record, status=SourceStatus.PENDING).production_ready
    assert not replace(record, sha256="").production_ready
    assert replace(record, kind=SourceKind.FAQ_CSV).production_ready


def test_sha256_mismatch_is_rejected(tmp_path: Path) -> None:
    record = replace(load_registry().get("gsn_qa"), raw_file="x.csv")
    (tmp_path / record.id).mkdir()
    (tmp_path / record.id / "x.csv").write_text("faq_question,faq_answer\n", encoding="utf-8")
    with pytest.raises(SourceIntegrityError):
        verify(record, tmp_path)


def test_normalize_text() -> None:
    raw = "<p>第458號新聞稿&nbsp;</p>\r\n<p>外交部長說明,詳見 https://x.gov.tw 。ＡＢＣ１２３</p>"
    text = normalize_text(raw)
    assert "<" not in text and "&nbsp;" not in text and "https" not in text
    assert "\r" not in text
    assert "外交部長說明，詳見" in text
    assert "ABC123" in text
    # 不做簡轉繁、不改字形。
    assert normalize_text("臺灣与台灣") == "臺灣与台灣"


def test_sentence_split_removes_markers_and_short_pieces() -> None:
    pieces = split_sentences("一、申請人應檢附文件。二、好。第 3 條 本法自公布日施行！")
    assert pieces == ["申請人應檢附文件。", "本法自公布日施行！"]


def test_long_sentence_is_split_at_commas() -> None:
    long = "，".join(["這是一個很長的子句內容"] * 20) + "。"
    assert all(len(p) <= 120 for p in split_sentences(long))


def test_dedupe_is_global_and_split_is_per_document() -> None:
    documents = [
        RawDocument("a", "d1", "f", "本法自公布日施行。"),
        RawDocument("b", "d9", "f", "本法自公布日施行！"),
    ]
    seen: set[str] = set()
    sentences = list(build_sentences(documents, seen))
    assert len(sentences) == 1 and sentences[0].source_id == "a"
    assert dedupe_key("第3條，本法。") == "第條本法"
    assert assign_split("a", "d1") == assign_split("a", "d1")
    splits = {assign_split("s", f"doc{i}") for i in range(200)}
    assert splits == {Split.TRAIN, Split.DEV, Split.TEST}


def test_tokenize_collapses_digits_and_latin_and_drops_markers() -> None:
    assert tokenize("第12.5條 GSN 使用$^") == ["第", "0", "條", "A", "使", "用"]


SENTENCES = ["我明天會再去台北。", "我明天會去台北。", "他在台北工作。", "請你再說一次。"]


def test_language_model_is_finite_and_normalized() -> None:
    counts = count_ngrams(SENTENCES, min_trigram_count=1)
    vocabulary = sorted(set(counts.unigrams) | {"宰", "罕"})
    lm = CorpusLanguageModel(counts, vocabulary_size=len(vocabulary))
    for history in ("^^", "明天", "會再", "未知"):
        total = math.fsum(lm.probability(token, history) for token in vocabulary)
        assert total == pytest.approx(1.0, abs=1e-9)
    assert math.isfinite(lm.score("宰罕宰", "從未見過"))
    assert lm.score("再去台北", "我明天會") > lm.score("宰去台北", "我明天會")


def test_counts_roundtrip(tmp_path: Path) -> None:
    counts = count_ngrams(SENTENCES, min_trigram_count=1)
    save_counts(counts, {"台北": 3}, tmp_path, {"schema": "test"})
    loaded, words, manifest = load_counts(tmp_path)
    assert loaded.trigrams == counts.trigrams and loaded.followers == counts.followers
    assert words == {"台北": 3} and manifest == {"schema": "test"}


def test_pruning_keeps_backoff_statistics() -> None:
    full = count_ngrams(SENTENCES, min_trigram_count=1)
    pruned = count_ngrams(SENTENCES, min_trigram_count=2)
    assert pruned.followers == full.followers
    assert len(pruned.trigrams) < len(full.trigrams)


def _annotator() -> ReadingAnnotator:
    chars = [
        CharReading("再", "ㄗㄞˋ", "1-0001"),
        CharReading("去", "ㄑㄩˋ", "1-0002"),
        CharReading("行", "ㄒㄧㄥˊ", "1-0003"),
        CharReading("行", "ㄏㄤˊ", "1-0003"),
        CharReading("的", "ㄉㄜ˙", "1-0004"),
        CharReading("的", "ㄉㄧˊ", "1-0004"),
        CharReading("銀", "ㄧㄣˊ", "1-0005"),
    ]
    builtin = [
        BuiltinRow("的", 5, ("ㄉㄜ˙",), 1),
        BuiltinRow("銀行", 4, ("ㄧㄣˊ", "ㄏㄤˊ"), 2),
    ]
    return ReadingAnnotator(chars, builtin)


def test_annotator_rules() -> None:
    annotator = _annotator()
    assert annotator.annotate("再去") == Annotation("再去", ("ㄗㄞˋ", "ㄑㄩˋ"))
    assert annotator.annotate("銀行的") == Annotation("銀行的", ("ㄧㄣˊ", "ㄏㄤˊ", "ㄉㄜ˙"))
    rejected = annotator.annotate("再行")
    assert isinstance(rejected, Rejection) and rejected.reason is RejectReason.AMBIGUOUS_POLYPHONE
    assert annotator.annotate("再A").reason is RejectReason.NON_HAN  # type: ignore[union-attr]
    assert annotator.annotate("再宰").reason is RejectReason.NO_READING  # type: ignore[union-attr]


def test_sources_json_is_valid_json_with_schema() -> None:
    data = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    assert data["schema"] == "zaoseq-bopomofo/sources/v1"
    required = {
        "id", "dataset_name", "provider", "official_dataset_url", "download_url", "license", "license_url",
        "commercial_use", "modification", "redistribution", "ai_training", "attribution", "downloaded_at",
        "upstream_version_or_updated_at", "sha256", "allowed_uses", "notes",
    }
    for source in data["sources"]:
        assert required <= set(source), source["id"]
