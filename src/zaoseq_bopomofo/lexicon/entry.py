"""詞庫資料型別。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class EntrySource(Enum):
    CNS11643 = "cns11643"
    BUILTIN = "builtin"


@dataclass(frozen=True)
class CharReading:
    """CNS11643 的一筆「字 → 讀音」。`reading` 已轉為規範寫法（輕聲調號後置）。"""

    char: str
    reading: str
    cns_code: str

    @property
    def plane(self) -> int:
        return int(self.cns_code.split("-", 1)[0])


@dataclass(frozen=True)
class LexiconEntry:
    """`frequency` 是相對權重（> 0），只在同一份詞庫內有比較意義，不是語料統計次數。"""

    text: str
    readings: tuple[str, ...]
    frequency: float
    source: EntrySource

    def __post_init__(self) -> None:
        # 目前只收一字一音節的詞；兒化等例外需要另外設計 reading 對齊方式。
        if len(self.text) != len(self.readings):
            raise ValueError(f"{self.text!r} 的字數與音節數 {len(self.readings)} 不一致")
        if not math.isfinite(self.frequency) or self.frequency <= 0:
            raise ValueError(f"{self.text!r} 的 frequency 必須是正數：{self.frequency!r}")
