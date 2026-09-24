"""注音字串解析與逐鍵組字。

結構規則（聲母→介音→韻母→聲調、每格最多一個）在這裡檢查；
「哪些組合真的存在」由呼叫端提供的 inventory 決定，通常來自 CNS11643 讀音集合。
"""

from __future__ import annotations

from collections.abc import Container
from dataclasses import dataclass, replace
from enum import Enum

from zaoseq_bopomofo.phonetics.symbol import SymbolKind, Tone, symbol_kind, tone_of
from zaoseq_bopomofo.phonetics.syllable import BopomofoSyllable

_SEPARATORS = frozenset(" \t-")
_SLOT_ORDER = (SymbolKind.INITIAL, SymbolKind.MEDIAL, SymbolKind.FINAL)


class InvalidBopomofoError(ValueError):
    pass


def parse_syllable(text: str, inventory: Container[str] | None = None) -> BopomofoSyllable:
    """解析一個完整音節；未標調號視為一聲。

    輕聲同時接受前置（CNS11643 的 `˙ㄌㄜ`）與後置（`ㄌㄜ˙`）寫法。
    """
    raw = text.strip()
    if not raw:
        raise InvalidBopomofoError("空字串不是音節")
    tone: Tone | None = None
    if raw[0] == Tone.NEUTRAL.value:
        tone = Tone.NEUTRAL
        raw = raw[1:]
    if raw and tone_of(raw[-1]) is not None:
        if tone is not None:
            raise InvalidBopomofoError(f"{text!r} 有兩個聲調")
        tone = tone_of(raw[-1])
        raw = raw[:-1]

    slots: dict[SymbolKind, str] = {}
    last_index = -1
    for ch in raw:
        kind = symbol_kind(ch)
        if kind is None:
            raise InvalidBopomofoError(f"{text!r} 含有非注音字元 {ch!r}")
        index = _SLOT_ORDER.index(kind)
        if index <= last_index:
            raise InvalidBopomofoError(f"{text!r} 的符號順序或數量不合法")
        slots[kind] = ch
        last_index = index
    if not slots:
        raise InvalidBopomofoError(f"{text!r} 只有聲調沒有音")

    syllable = BopomofoSyllable(
        initial=slots.get(SymbolKind.INITIAL),
        medial=slots.get(SymbolKind.MEDIAL),
        final=slots.get(SymbolKind.FINAL),
        tone=tone if tone is not None else Tone.FIRST,
    )
    _check_inventory(syllable, inventory)
    return syllable


def parse_reading(text: str, inventory: Container[str] | None = None) -> tuple[BopomofoSyllable, ...]:
    """解析多音節字串。調號結束一個音節；空白或 `-` 以一聲結束尚未標調的音節。

    連續的一聲音節必須以分隔符隔開，因為沒有調號時無法從字串判斷邊界。
    """
    syllables: list[BopomofoSyllable] = []
    buffer = ""
    for ch in text:
        if ch in _SEPARATORS:
            if buffer:
                syllables.append(parse_syllable(buffer, inventory))
                buffer = ""
            continue
        buffer += ch
        if tone_of(ch) is not None:
            syllables.append(parse_syllable(buffer, inventory))
            buffer = ""
    if buffer:
        syllables.append(parse_syllable(buffer, inventory))
    return tuple(syllables)


def _check_inventory(syllable: BopomofoSyllable, inventory: Container[str] | None) -> None:
    if inventory is not None and syllable.text() not in inventory:
        raise InvalidBopomofoError(f"{syllable.text()!r} 不是已知的音節")


class ComposeStatus(Enum):
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ComposeResult:
    """`syllable` 在 COMPLETED 時是完成的音節，其餘狀態是目前的組字內容。"""

    status: ComposeStatus
    syllable: BopomofoSyllable
    reason: str | None = None


class SyllableComposer:
    """逐鍵組出一個音節。

    同一格再輸入會取代原本的符號（例如 ㄅ 之後按 ㄆ），這是注音使用者修正聲母的慣用方式。
    聲調鍵結束音節；inventory 不認得的組合會被拒絕，且保留原本的組字內容讓使用者修正。
    """

    def __init__(self, inventory: Container[str] | None = None) -> None:
        self._inventory = inventory
        self._current = BopomofoSyllable()

    @property
    def current(self) -> BopomofoSyllable:
        return self._current

    def push_symbol(self, symbol: str) -> ComposeResult:
        kind = symbol_kind(symbol)
        if kind is None:
            return ComposeResult(ComposeStatus.REJECTED, self._current, f"{symbol!r} 不是注音符號")
        field = kind.value
        self._current = replace(self._current, **{field: symbol})
        return ComposeResult(ComposeStatus.ACCEPTED, self._current)

    def push_tone(self, tone: Tone) -> ComposeResult:
        if not self._current.has_body:
            return ComposeResult(ComposeStatus.REJECTED, self._current, "尚未輸入聲母或韻母")
        completed = replace(self._current, tone=tone)
        if self._inventory is not None and completed.text() not in self._inventory:
            return ComposeResult(ComposeStatus.REJECTED, self._current, f"{completed.text()!r} 不是已知的音節")
        self._current = BopomofoSyllable()
        return ComposeResult(ComposeStatus.COMPLETED, completed)

    def backspace(self) -> bool:
        """由右而左刪一格；已經是空的回傳 False，讓上層改為刪除前一個音節。"""
        for field in ("final", "medial", "initial"):
            if getattr(self._current, field) is not None:
                self._current = replace(self._current, **{field: None})
                return True
        return False

    def clear(self) -> None:
        self._current = BopomofoSyllable()
