"""實體按鍵到注音符號的對照。"""

from __future__ import annotations

from collections.abc import Container
from dataclasses import dataclass

from zaoseq_bopomofo.phonetics.parser import ComposeStatus, InvalidBopomofoError, SyllableComposer
from zaoseq_bopomofo.phonetics.symbol import Tone
from zaoseq_bopomofo.phonetics.syllable import BopomofoSyllable


@dataclass(frozen=True)
class SymbolKey:
    symbol: str


@dataclass(frozen=True)
class ToneKey:
    tone: Tone


KeyAction = SymbolKey | ToneKey

# 標準（大千）排列，即台灣實體鍵盤上印的注音位置。
_STANDARD_SYMBOLS = {
    "1": "ㄅ", "q": "ㄆ", "a": "ㄇ", "z": "ㄈ",
    "2": "ㄉ", "w": "ㄊ", "s": "ㄋ", "x": "ㄌ",
    "e": "ㄍ", "d": "ㄎ", "c": "ㄏ",
    "r": "ㄐ", "f": "ㄑ", "v": "ㄒ",
    "5": "ㄓ", "t": "ㄔ", "g": "ㄕ", "b": "ㄖ",
    "y": "ㄗ", "h": "ㄘ", "n": "ㄙ",
    "u": "ㄧ", "j": "ㄨ", "m": "ㄩ",
    "8": "ㄚ", "i": "ㄛ", "k": "ㄜ", ",": "ㄝ",
    "9": "ㄞ", "o": "ㄟ", "l": "ㄠ", ".": "ㄡ",
    "0": "ㄢ", "p": "ㄣ", ";": "ㄤ", "/": "ㄥ", "-": "ㄦ",
}
_STANDARD_TONES = {" ": Tone.FIRST, "6": Tone.SECOND, "3": Tone.THIRD, "4": Tone.FOURTH, "7": Tone.NEUTRAL}


# 實體鍵盤列（QWERTY 錯位排列）。相鄰定義：同列左右，以及上一列的 (c, c+1)、下一列的 (c-1, c)。
_ROWS = ("1234567890-", "qwertyuiop", "asdfghjkl;", "zxcvbnm,./")


def _key_positions() -> dict[str, tuple[int, int]]:
    return {key: (r, c) for r, row in enumerate(_ROWS) for c, key in enumerate(row)}


_POSITIONS = _key_positions()


def adjacent_keys(key: str) -> tuple[str, ...]:
    position = _POSITIONS.get(key.lower())
    if position is None:
        return ()
    r, c = position
    neighbours = [(r, c - 1), (r, c + 1), (r - 1, c), (r - 1, c + 1), (r + 1, c - 1), (r + 1, c)]
    return tuple(
        _ROWS[nr][nc] for nr, nc in neighbours if 0 <= nr < len(_ROWS) and 0 <= nc < len(_ROWS[nr])
    )


class StandardKeyboardLayout:
    name = "standard"

    def key_for_symbol(self, symbol: str) -> str | None:
        for key, value in _STANDARD_SYMBOLS.items():
            if value == symbol:
                return key
        return None

    def adjacent_symbols(self, symbol: str) -> tuple[str, ...]:
        """實體位置相鄰、且對應到注音符號（不是聲調鍵）的符號。"""
        key = self.key_for_symbol(symbol)
        if key is None:
            return ()
        return tuple(_STANDARD_SYMBOLS[k] for k in adjacent_keys(key) if k in _STANDARD_SYMBOLS)

    def map_key(self, key: str) -> KeyAction | None:
        """不屬於注音排列的鍵回傳 None，由 IME engine 決定是否當作控制鍵。"""
        lowered = key.lower()
        if lowered in _STANDARD_SYMBOLS:
            return SymbolKey(_STANDARD_SYMBOLS[lowered])
        if key in _STANDARD_TONES:
            return ToneKey(_STANDARD_TONES[key])
        return None


def parse_key_sequence(
    keys: str,
    layout: StandardKeyboardLayout,
    inventory: Container[str] | None = None,
) -> tuple[BopomofoSyllable, ...]:
    """把一串按鍵（如 `su3cl3`）轉成音節；空白是一聲鍵。結尾未標調的音節視為輸入錯誤。"""
    composer = SyllableComposer(inventory)
    syllables: list[BopomofoSyllable] = []
    for key in keys:
        action = layout.map_key(key)
        if action is None:
            raise InvalidBopomofoError(f"按鍵 {key!r} 不在 {layout.name} 排列中")
        if isinstance(action, SymbolKey):
            result = composer.push_symbol(action.symbol)
        elif key == " " and not composer.current.has_body:
            # 音節之間多按的空白不算錯誤；其他聲調鍵出現在空音節上仍交給 composer 拒絕。
            continue
        else:
            result = composer.push_tone(action.tone)
        if result.status is ComposeStatus.REJECTED:
            raise InvalidBopomofoError(result.reason or "無效輸入")
        if result.status is ComposeStatus.COMPLETED:
            syllables.append(result.syllable)
    if composer.current.has_body:
        raise InvalidBopomofoError(f"最後一個音節 {composer.current.body!r} 尚未輸入聲調")
    return tuple(syllables)
