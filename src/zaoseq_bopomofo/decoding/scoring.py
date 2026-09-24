"""候選分數拆解與組合。各成分分開保存，總分只是明確權重的線性組合，不是不可解釋的單一數字。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ScoreBreakdown:
    """都是 log10 尺度。

    - pronunciation：-讀音修正成本；照使用者輸入解讀時為 0。
    - lexical：builtin 詞庫 unigram（人工等級，只是 demo heuristic）。
    - corpus：CorpusLanguageModel 的字元 trigram 分數；沒有載入語料模型時為 None。
    contextual 訊號（Laya）不在這裡：它由 ranking 層另外提供，不混進 decoder 分數。
    """

    pronunciation: float
    lexical: float
    corpus: float | None


@runtime_checkable
class SequenceScorer(Protocol):
    def total(self, breakdown: ScoreBreakdown) -> float: ...


@dataclass(frozen=True)
class LinearScorer:
    """total = corpus_weight·corpus + lexical_weight·lexical + edit_lambda·pronunciation。

    權重是事前選定的設定，不依個別案例調整。corpus 為 None 時該項以 0 計，
    代表「沒有語料訊號」而不是「語料認為機率為 1」；此時應搭配 lexical_weight > 0 使用。
    """

    corpus_weight: float = 1.0
    lexical_weight: float = 0.0
    edit_lambda: float = 1.0

    def __post_init__(self) -> None:
        for name in ("corpus_weight", "lexical_weight", "edit_lambda"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} 必須是非負有限數：{value!r}")

    def total(self, breakdown: ScoreBreakdown) -> float:
        corpus = breakdown.corpus if breakdown.corpus is not None else 0.0
        return (
            self.corpus_weight * corpus
            + self.lexical_weight * breakdown.lexical
            + self.edit_lambda * breakdown.pronunciation
        )
