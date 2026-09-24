"""組裝預設的 corpus decoder。沒有語料統計檔時明確回報，不會默默退回別的模型。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from zaoseq_bopomofo.corpus.domains import (
    GENERAL_WEIGHTS,
    LEGAL_WEIGHTS,
    DomainWeights,
    LanguageModel,
    build_general,
    load_domain_models,
)
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, load_counts
from zaoseq_bopomofo.decoding.errors import ErrorCosts, ReadingErrorModel
from zaoseq_bopomofo.decoding.lattice import LatticeConfig, LatticeDecoder
from zaoseq_bopomofo.decoding.scoring import LinearScorer
from zaoseq_bopomofo.decoding.tolerant import TolerancePolicy, TolerantDecoder
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT, LoadedLexicon

DEFAULT_LM_DIR = PROJECT_ROOT / "data" / "corpus" / "lm"


class LanguageModelMissingError(RuntimeError):
    pass


class LanguageModelConfig(Enum):
    """GENERAL 是日常注音的預設；RAW 依原始句數混合（法律語料主導），只作對照；
    CAPPED 每個領域最多 20k 句；LEGAL 只用法律語料，留作未來 domain adaptation。"""

    GENERAL = "general"
    RAW = "raw"
    CAPPED = "capped"
    LEGAL = "legal"


def load_language_model(
    config: LanguageModelConfig = LanguageModelConfig.GENERAL,
    candidate_characters: Iterable[str] = (),
    directory: Path = DEFAULT_LM_DIR,
    weights: DomainWeights = GENERAL_WEIGHTS,
) -> LanguageModel:
    """所有設定共用同一個字元詞彙量 V（raw 語料字元 ∪ decoder 可能產生的字），
    讓不同設定的分數可以比較，未見字元也有有限的 add-one 機率。"""
    if not (directory / "raw" / "manifest.json").exists():
        raise LanguageModelMissingError(f"找不到 {directory}；請先執行 `python -m zaoseq_bopomofo.corpus build`")
    raw_counts, _, _ = load_counts(directory / "raw")
    vocabulary_size = len(set(raw_counts.unigrams) | set(candidate_characters))
    if config is LanguageModelConfig.RAW:
        return CorpusLanguageModel(raw_counts, vocabulary_size)
    if config is LanguageModelConfig.CAPPED:
        counts, _, _ = load_counts(directory / "capped")
        return CorpusLanguageModel(counts, vocabulary_size)
    models = load_domain_models(directory, vocabulary_size)
    if config is LanguageModelConfig.LEGAL:
        return build_general(models, LEGAL_WEIGHTS)
    return build_general(models, weights)


def lexicon_characters(loaded: LoadedLexicon) -> set[str]:
    return {ch for word in loaded.lexicon.words() for ch in word}


@dataclass(frozen=True)
class DecoderSettings:
    scorer: LinearScorer = LinearScorer(corpus_weight=1.0, lexical_weight=0.0, edit_lambda=1.0)
    lattice: LatticeConfig = LatticeConfig()
    costs: ErrorCosts = ErrorCosts()
    # typo correction 預設關閉：目前 recovery 低且會在 2–3% 的正確輸入上改錯，只保留實驗開關。
    policy: TolerancePolicy = TolerancePolicy(enabled=False)


def build_tolerant_decoder(
    loaded: LoadedLexicon,
    language_model: LanguageModel | None,
    settings: DecoderSettings | None = None,
) -> TolerantDecoder:
    cfg = settings or DecoderSettings()
    errors = ReadingErrorModel(loaded.lexicon.syllables, cfg.costs)
    lattice = LatticeDecoder(loaded.lexicon, language_model, cfg.scorer, errors, cfg.lattice)
    return TolerantDecoder(lattice, errors, cfg.policy, has_language_model=language_model is not None)


# Frozen V0 baseline（benchmarks/frozen/V0.json）：general corpus LM + builtin lexicon、exact decoding。
# 之後的 TEST 結果不得回頭修改這組設定；要改就是新的 baseline 版本。
V0_SETTINGS = DecoderSettings(
    scorer=LinearScorer(corpus_weight=1.0, lexical_weight=1.0),
    policy=TolerancePolicy(enabled=False),
)


def build_v0_decoder(loaded: LoadedLexicon, directory: Path = DEFAULT_LM_DIR) -> TolerantDecoder:
    language_model = load_language_model(LanguageModelConfig.GENERAL, lexicon_characters(loaded), directory)
    return build_tolerant_decoder(loaded, language_model, V0_SETTINGS)
