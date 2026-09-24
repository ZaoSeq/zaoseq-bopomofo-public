"""注音符號與聲調的分類。"""

from __future__ import annotations

from enum import Enum

INITIALS = "ㄅㄆㄇㄈㄉㄊㄋㄌㄍㄎㄏㄐㄑㄒㄓㄔㄕㄖㄗㄘㄙ"
MEDIALS = "ㄧㄨㄩ"
FINALS = "ㄚㄛㄜㄝㄞㄟㄠㄡㄢㄣㄤㄥㄦ"


class SymbolKind(Enum):
    INITIAL = "initial"
    MEDIAL = "medial"
    FINAL = "final"


class Tone(Enum):
    # 值為規範寫法中的調號；一聲不標調號，所以是空字串。
    FIRST = ""
    SECOND = "ˊ"
    THIRD = "ˇ"
    FOURTH = "ˋ"
    NEUTRAL = "˙"

    @property
    def number(self) -> int:
        return _TONE_NUMBERS[self]


_TONE_NUMBERS = {Tone.FIRST: 1, Tone.SECOND: 2, Tone.THIRD: 3, Tone.FOURTH: 4, Tone.NEUTRAL: 5}

# ˉ (U+02C9) 是部分資料明確標示一聲的寫法，解析時接受，輸出時一律省略。
TONE_MARKS: dict[str, Tone] = {
    "ˉ": Tone.FIRST,
    "ˊ": Tone.SECOND,
    "ˇ": Tone.THIRD,
    "ˋ": Tone.FOURTH,
    "˙": Tone.NEUTRAL,
}

_KIND_BY_SYMBOL: dict[str, SymbolKind] = {
    **{s: SymbolKind.INITIAL for s in INITIALS},
    **{s: SymbolKind.MEDIAL for s in MEDIALS},
    **{s: SymbolKind.FINAL for s in FINALS},
}


def symbol_kind(symbol: str) -> SymbolKind | None:
    """非注音符號回傳 None。"""
    return _KIND_BY_SYMBOL.get(symbol)


def tone_of(mark: str) -> Tone | None:
    return TONE_MARKS.get(mark)
