"""contextual 訊號的附帶診斷資料。只有資料，沒有邏輯，避免 base / contextual / confidence 互相 import。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextSignal:
    """backend 回報的推論成本與穩定度。

    - `disagreement`：pairwise 中 A-vs-B 與 B-vs-A 對同一對候選的判斷差距平均，0 表示完全一致，
      1 表示結論完全由呈現位置決定。
    - `order_instability`：multi-choice 中各呈現順序的第一名與平均後第一名不同的比例。
    沒有量測的項目為 None，不是 0。
    """

    forward_passes: int
    questions: int
    disagreement: float | None = None
    order_instability: float | None = None


@dataclass(frozen=True)
class ContextConfidence:
    """contextual 分佈的可靠程度與據此決定的 hybrid 權重。

    這是「模型不確定時少干預」的 gating，不代表 confident 時一定正確；
    benchmark 另外統計 high-confidence wrong 與 low-confidence correct。
    """

    margin: float
    entropy: float
    disagreement: float | None
    order_instability: float | None
    gate: float
    effective_weight: float
    confident: bool
