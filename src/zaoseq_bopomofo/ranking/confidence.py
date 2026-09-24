"""由 contextual 分佈與診斷資料計算 ContextConfidence。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from zaoseq_bopomofo.ranking.signal import ContextConfidence, ContextSignal


@dataclass(frozen=True)
class ConfidenceConfig:
    """所有 gating 門檻集中在這裡；數值是事前選定，未依 DEV 結果調整。

    每個 gate 在 [0, 1] 之間線性變化，effective_weight = max_weight × 各 gate 的乘積：
    - margin：第一名與第二名機率差，低於 margin_low 視為沒有偏好，高於 margin_high 視為明確。
    - entropy：以 log(k) 正規化的熵，高於 entropy_high 視為幾乎平坦（例如 0.279/0.264/0.256/0.2）。
    - disagreement / order_instability：高於對應上限時 gate 為 0，代表結論主要由呈現位置決定。
    `confident` 是 gate >= confident_gate，只用於統計，不影響排序。
    """

    max_weight: float = 0.6
    margin_low: float = 0.05
    margin_high: float = 0.30
    entropy_low: float = 0.70
    entropy_high: float = 0.95
    disagreement_high: float = 0.50
    instability_high: float = 0.50
    confident_gate: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_weight <= 1.0:
            raise ValueError("max_weight 必須介於 [0, 1]")
        if not (self.margin_low < self.margin_high and self.entropy_low < self.entropy_high):
            raise ValueError("low 門檻必須小於 high 門檻")
        if self.disagreement_high <= 0 or self.instability_high <= 0:
            raise ValueError("disagreement / instability 上限必須 > 0")


def assess_confidence(
    probabilities: Mapping[str, float],
    signal: ContextSignal | None,
    config: ConfidenceConfig,
) -> ContextConfidence:
    """`probabilities` 至少兩個候選且總和約為 1；少於兩個時沒有決策空間，gate 為 0。"""
    values = sorted(probabilities.values(), reverse=True)
    if len(values) < 2:
        return ContextConfidence(0.0, 0.0, None, None, 0.0, 0.0, False)
    margin = values[0] - values[1]
    entropy = -math.fsum(p * math.log(p) for p in values if p > 0) / math.log(len(values))
    disagreement = signal.disagreement if signal else None
    instability = signal.order_instability if signal else None

    gate = _rising(margin, config.margin_low, config.margin_high)
    gate *= _falling(entropy, config.entropy_low, config.entropy_high)
    if disagreement is not None:
        gate *= _falling(disagreement, 0.0, config.disagreement_high)
    if instability is not None:
        gate *= _falling(instability, 0.0, config.instability_high)
    return ContextConfidence(
        margin=margin,
        entropy=entropy,
        disagreement=disagreement,
        order_instability=instability,
        gate=gate,
        effective_weight=config.max_weight * gate,
        confident=gate >= config.confident_gate,
    )


def _rising(value: float, low: float, high: float) -> float:
    return min(1.0, max(0.0, (value - low) / (high - low)))


def _falling(value: float, low: float, high: float) -> float:
    return 1.0 - _rising(value, low, high)
