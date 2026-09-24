"""領域平衡的語言模型：raw、capped、weighted interpolation 三種組法。"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from zaoseq_bopomofo.corpus.source import Domain
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, initial_history, load_counts, tokenize

# 參與字元語言模型的領域；terminology 是詞條清單不是句子，只用於詞彙統計。
LM_DOMAINS = (Domain.GOVERNMENT_FAQ, Domain.PUBLIC_SERVICE, Domain.PRESS_RELEASE, Domain.OTHER_FORMAL, Domain.LEGAL)


@runtime_checkable
class LanguageModel(Protocol):
    """decoder 與 ranker 只依賴這個介面；單一 n-gram 模型與插值模型都實作它。"""

    def probability(self, token: str, history: str) -> float: ...

    def log10_probability(self, token: str, history: str) -> float: ...

    def score(self, text: str, left_context: str = "") -> float: ...

    def extend(self, history: str, char: str) -> tuple[float, str]: ...


@dataclass(frozen=True)
class DomainWeights:
    """各領域在插值模型中的權重，總和必須為 1。沒有列出的領域權重為 0。

    GENERAL 是事前選定的日常輸入設定：三個非法律正式文體各 0.3，法律 0.1；
    法律語料仍保留，但不會因為句數最多而主導一般注音。
    """

    weights: Mapping[Domain, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("DomainWeights 至少需要一個領域")
        if any(not math.isfinite(w) or w < 0 for w in self.weights.values()):
            raise ValueError("領域權重必須是非負有限數")
        if abs(math.fsum(self.weights.values()) - 1.0) > 1e-9:
            raise ValueError(f"領域權重總和必須為 1：{dict(self.weights)}")


GENERAL_WEIGHTS = DomainWeights(
    {
        Domain.GOVERNMENT_FAQ: 0.3,
        Domain.PUBLIC_SERVICE: 0.3,
        Domain.PRESS_RELEASE: 0.3,
        Domain.LEGAL: 0.1,
    }
)
LEGAL_WEIGHTS = DomainWeights({Domain.LEGAL: 1.0})


class InterpolatedLanguageModel:
    """P(c | h) = Σ_d w_d · P_d(c | h)，每個 P_d 都是已平滑的領域模型，所以混合後仍是合法分佈，
    而且任何序列都不會是 -inf。log10 版本就是對混合機率取 log，不是對 log 做加權。"""

    def __init__(self, components: Sequence[tuple[Domain, CorpusLanguageModel, float]]) -> None:
        active = [(d, m, w) for d, m, w in components if w > 0]
        if not active:
            raise ValueError("至少需要一個權重 > 0 的領域模型")
        total = math.fsum(w for _, _, w in active)
        if abs(total - 1.0) > 1e-9:
            raise ValueError("插值權重總和必須為 1")
        self._components = tuple(active)

    @property
    def domains(self) -> tuple[Domain, ...]:
        return tuple(d for d, _, _ in self._components)

    def domain_probabilities(self, token: str, history: str) -> dict[Domain, float]:
        """各領域模型各自給的機率，用於分數拆解與分析。"""
        return {d: m.probability(token, history) for d, m, _ in self._components}

    def probability(self, token: str, history: str) -> float:
        return math.fsum(w * m.probability(token, history) for _, m, w in self._components)

    def log10_probability(self, token: str, history: str) -> float:
        return math.log10(self.probability(token, history))

    def score(self, text: str, left_context: str = "") -> float:
        history = initial_history(left_context)
        total = 0.0
        for token in tokenize(text):
            delta, history = self.extend(history, token)
            total += delta
        return total

    def extend(self, history: str, char: str) -> tuple[float, str]:
        return self.log10_probability(char, history), (history + char)[-2:]


class GeneralCorpusLanguageModel(InterpolatedLanguageModel):
    """日常注音預設使用的語言模型：以 GENERAL_WEIGHTS 插值各領域模型。"""


def cap_by_domain(sentences: Sequence[tuple[Domain, str]], cap: int) -> list[str]:
    """每個領域最多保留 `cap` 句，依句子的 sha256 排序抽樣，結果 deterministic 且與輸入順序無關。"""
    by_domain: dict[Domain, list[str]] = {}
    for domain, text in sentences:
        by_domain.setdefault(domain, []).append(text)
    kept: list[str] = []
    for domain in sorted(by_domain, key=lambda d: d.value):
        ranked = sorted(by_domain[domain], key=lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest())
        kept.extend(ranked[:cap])
    return kept


def load_domain_models(directory: Path, vocabulary_size: int) -> dict[Domain, CorpusLanguageModel]:
    models: dict[Domain, CorpusLanguageModel] = {}
    for domain in LM_DOMAINS:
        path = directory / "domain" / domain.value
        if (path / "manifest.json").exists():
            counts, _, _ = load_counts(path)
            models[domain] = CorpusLanguageModel(counts, vocabulary_size=vocabulary_size)
    return models


def interpolate(models: Mapping[Domain, CorpusLanguageModel], weights: DomainWeights) -> InterpolatedLanguageModel:
    missing = [d.value for d, w in weights.weights.items() if w > 0 and d not in models]
    if missing:
        raise FileNotFoundError(f"缺少領域模型：{missing}；請重新執行 corpus build")
    components = [(d, models[d], w) for d, w in weights.weights.items()]
    return InterpolatedLanguageModel(components)


def build_general(models: Mapping[Domain, CorpusLanguageModel], weights: DomainWeights = GENERAL_WEIGHTS) -> GeneralCorpusLanguageModel:
    missing = [d.value for d, w in weights.weights.items() if w > 0 and d not in models]
    if missing:
        raise FileNotFoundError(f"缺少領域模型：{missing}；請重新執行 corpus build")
    return GeneralCorpusLanguageModel([(d, models[d], w) for d, w in weights.weights.items()])
