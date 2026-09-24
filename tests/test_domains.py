from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from zaoseq_bopomofo.corpus.domains import (
    GENERAL_WEIGHTS,
    DomainWeights,
    GeneralCorpusLanguageModel,
    InterpolatedLanguageModel,
    build_general,
    cap_by_domain,
)
from zaoseq_bopomofo.corpus.records import read_records
from zaoseq_bopomofo.corpus.source import Domain, SourceKind, load_registry
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, count_ngrams
from zaoseq_bopomofo.decoding.pipeline import DecoderSettings
from zaoseq_bopomofo.evaluation.domains import classify_errors, load_groups

VOCAB = set("我明天會再去在台北年法條例規定公告申請")


def _model(sentences: list[str]) -> CorpusLanguageModel:
    return CorpusLanguageModel(count_ngrams(sentences, min_trigram_count=1), vocabulary_size=len(VOCAB) + 3)


@pytest.fixture
def models() -> dict[Domain, CorpusLanguageModel]:
    return {
        Domain.GOVERNMENT_FAQ: _model(["請再去申請。", "我明天會再去。"]),
        Domain.PUBLIC_SERVICE: _model(["明天再去台北。"]),
        Domain.PRESS_RELEASE: _model(["會在去年公告。"] * 5),
        Domain.LEGAL: _model(["依法條例規定申請。"] * 50),
    }


def test_domain_weights_validation() -> None:
    with pytest.raises(ValueError):
        DomainWeights({Domain.LEGAL: 0.5})
    with pytest.raises(ValueError):
        DomainWeights({Domain.LEGAL: 1.5, Domain.PRESS_RELEASE: -0.5})
    with pytest.raises(ValueError):
        DomainWeights({})
    assert math.fsum(GENERAL_WEIGHTS.weights.values()) == pytest.approx(1.0)
    assert GENERAL_WEIGHTS.weights[Domain.LEGAL] < GENERAL_WEIGHTS.weights[Domain.GOVERNMENT_FAQ]


def test_interpolation_is_a_normalized_mixture(models: dict[Domain, CorpusLanguageModel]) -> None:
    general = build_general(models)
    assert isinstance(general, GeneralCorpusLanguageModel)
    vocabulary = sorted(VOCAB | {"。", "$", "^"})
    for history in ("^^", "會再", "未見"):
        expected = math.fsum(
            GENERAL_WEIGHTS.weights[d] * m.probability("去", history) for d, m in models.items()
        )
        assert general.probability("去", history) == pytest.approx(expected)
    assert math.isfinite(general.score("罕見字", "未見前文"))
    assert set(general.domain_probabilities("去", "會再")) == set(models)
    # 法律語料句數最多，但在 general 權重下不能主導：非法律的「再去」比純法律模型高。
    legal_only = build_general(models, DomainWeights({Domain.LEGAL: 1.0}))
    assert general.score("再去", "我明天會") > legal_only.score("再去", "我明天會")
    assert len(vocabulary) > 0


def test_missing_domain_model_is_an_error(models: dict[Domain, CorpusLanguageModel]) -> None:
    del models[Domain.PRESS_RELEASE]
    with pytest.raises(FileNotFoundError):
        build_general(models)


def test_interpolated_model_rejects_bad_weights(models: dict[Domain, CorpusLanguageModel]) -> None:
    with pytest.raises(ValueError):
        InterpolatedLanguageModel([(Domain.LEGAL, models[Domain.LEGAL], 0.5)])


def test_cap_is_deterministic_and_order_independent() -> None:
    pairs = [(Domain.LEGAL, f"法條{i}") for i in range(10)] + [(Domain.GOVERNMENT_FAQ, "請再去申請")]
    capped = cap_by_domain(pairs, cap=3)
    assert len(capped) == 4 and "請再去申請" in capped
    assert capped == cap_by_domain(list(reversed(pairs)), cap=3)


def test_records_reader_formats(tmp_path: Path) -> None:
    (tmp_path / "a.csv").write_text("問題,答案\n如何申請？,請線上申請。\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("標題\t內容\n公告\t明天開放\n", encoding="utf-8")
    (tmp_path / "c.json").write_text(json.dumps({"data": [{"問題": "q", "答覆": "a", "巢狀": {"x": 1}}]}), encoding="utf-8")
    (tmp_path / "d.xml").write_text(
        '<?xml version="1.0"?><root xmlns="https://x/"><item><問題>q1</問題><答案>a1</答案></item>'
        "<item><問題>q2</問題><答案>a2</答案></item></root>",
        encoding="utf-8",
    )
    (tmp_path / "e.csv").write_bytes("問題,答案\n如何,申請\n".encode("cp950"))
    assert list(read_records(tmp_path / "a.csv", "CSV")) == [{"問題": "如何申請？", "答案": "請線上申請。"}]
    assert list(read_records(tmp_path / "b.csv", "CSV")) == [{"標題": "公告", "內容": "明天開放"}]
    assert list(read_records(tmp_path / "c.json", "JSON")) == [{"問題": "q", "答覆": "a"}]
    assert [r["問題"] for r in read_records(tmp_path / "d.xml", "XML")] == ["q1", "q2"]
    assert list(read_records(tmp_path / "e.csv", "CSV")) == [{"問題": "如何", "答案": "申請"}]


def test_registry_domains_and_ai_training_basis() -> None:
    registry = load_registry()
    for record in registry.sources:
        assert record.ai_training_explicit is False
        assert record.ai_training_basis == "general unrestricted-purpose license grant"
    domains = {r.domain for r in registry.sources}
    assert {Domain.LEGAL, Domain.GOVERNMENT_FAQ, Domain.PUBLIC_SERVICE, Domain.PRESS_RELEASE, Domain.TERMINOLOGY} <= domains
    tabular = [r for r in registry.sources if r.kind is SourceKind.TABULAR]
    assert tabular and all(r.text_fields and r.file_format for r in tabular)
    record = tabular[0]
    assert not replace(record, ai_training_basis="").production_ready


def test_typo_correction_is_off_by_default() -> None:
    assert DecoderSettings().policy.enabled is False


def test_error_classification_uses_groups_without_changing_scores() -> None:
    groups = load_groups()
    assert groups["再"] == groups["在"]
    homophone = {("載", "ㄗㄞˋ"), ("再", "ㄗㄞˋ"), ("在", "ㄗㄞˋ"), ("剛", "ㄍㄤ")}
    labels = classify_errors(
        "再去剛", "在去綱", ("ㄗㄞˋ", "ㄑㄩˋ", "ㄍㄤ"), groups, lambda c, r: (c, r) in homophone
    )
    assert labels == ["在再", "non_homophone"]
    assert classify_errors("再去", "再", ("ㄗㄞˋ", "ㄑㄩˋ"), groups, lambda c, r: True) == ["length_mismatch"]
