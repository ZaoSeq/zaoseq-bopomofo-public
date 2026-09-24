"""文字 → 注音的規則式標注，只用於從合法語料產生 silver benchmark 與 ranking data。

多音字無法可靠判斷時直接拒絕該句，而不是猜一個讀音：標注錯誤會變成錯誤的 gold。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from zaoseq_bopomofo.corpus.normalize import is_han
from zaoseq_bopomofo.lexicon.builder import BuiltinRow
from zaoseq_bopomofo.lexicon.entry import CharReading


class RejectReason(Enum):
    NON_HAN = "non_han"
    NO_READING = "no_reading"
    AMBIGUOUS_POLYPHONE = "ambiguous_polyphone"


@dataclass(frozen=True)
class Annotation:
    text: str
    readings: tuple[str, ...]


@dataclass(frozen=True)
class Rejection:
    text: str
    reason: RejectReason
    char: str


class ReadingAnnotator:
    """規則依序為：
    1. builtin 詞表中有明確讀音的多字詞，以最長匹配套用；
    2. 在 CNS11643 只有一個讀音的字；
    3. builtin 詞表中只列一個讀音的單字（例如「的 ㄉㄜ˙」）；
    其餘多音字一律拒絕。
    """

    def __init__(self, char_readings: Iterable[CharReading], builtin: Sequence[BuiltinRow]) -> None:
        cns: dict[str, set[str]] = {}
        for row in char_readings:
            cns.setdefault(row.char, set()).add(row.reading)
        self._cns = cns
        words: dict[str, set[tuple[str, ...]]] = {}
        singles: dict[str, set[str]] = {}
        for row in builtin:
            if row.readings is None:
                continue
            if len(row.text) == 1:
                singles.setdefault(row.text, set()).add(row.readings[0])
            else:
                words.setdefault(row.text, set()).add(row.readings)
        self._words = {w: next(iter(r)) for w, r in words.items() if len(r) == 1}
        self._singles = {c: next(iter(r)) for c, r in singles.items() if len(r) == 1}
        self._max_word = max((len(w) for w in self._words), default=1)

    def annotate(self, text: str) -> Annotation | Rejection:
        readings: list[str] = []
        i = 0
        while i < len(text):
            char = text[i]
            if not is_han(char):
                return Rejection(text, RejectReason.NON_HAN, char)
            matched = False
            for length in range(min(self._max_word, len(text) - i), 1, -1):
                word = text[i : i + length]
                if word in self._words:
                    readings.extend(self._words[word])
                    i += length
                    matched = True
                    break
            if matched:
                continue
            options = self._cns.get(char)
            if not options:
                return Rejection(text, RejectReason.NO_READING, char)
            if len(options) == 1:
                readings.append(next(iter(options)))
            elif char in self._singles and self._singles[char] in options:
                readings.append(self._singles[char])
            else:
                return Rejection(text, RejectReason.AMBIGUOUS_POLYPHONE, char)
            i += 1
        return Annotation(text, tuple(readings))
