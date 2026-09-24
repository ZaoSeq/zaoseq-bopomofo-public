"""依讀音索引的詞庫與 unigram 機率。"""

from __future__ import annotations

import math
from collections.abc import Iterable

from zaoseq_bopomofo.lexicon.entry import LexiconEntry


class DuplicateEntryError(ValueError):
    pass


class Lexicon:
    """不可變的詞庫。

    同一讀音下的詞條順序固定為 (-frequency, text 的 code point)，
    任何依賴詞庫順序的地方（候選 baseline、decoder tiebreak）因此都是 deterministic。
    """

    def __init__(self, entries: Iterable[LexiconEntry]) -> None:
        by_reading: dict[tuple[str, ...], list[LexiconEntry]] = {}
        seen: set[tuple[str, tuple[str, ...]]] = set()
        total = 0.0
        for entry in entries:
            key = (entry.text, entry.readings)
            if key in seen:
                raise DuplicateEntryError(f"重複詞條：{entry.text} {' '.join(entry.readings)}")
            seen.add(key)
            by_reading.setdefault(entry.readings, []).append(entry)
            total += entry.frequency
        self._by_reading = {
            reading: tuple(sorted(items, key=lambda e: (-e.frequency, e.text)))
            for reading, items in by_reading.items()
        }
        self._total_frequency = total
        self._syllables = frozenset(s for reading in self._by_reading for s in reading)
        self._max_length = max((len(r) for r in self._by_reading), default=0)
        self._size = len(seen)

    def __len__(self) -> int:
        return self._size

    @property
    def syllables(self) -> frozenset[str]:
        """詞庫出現過的所有音節，可直接當作 parser 的 inventory。"""
        return self._syllables

    @property
    def max_word_length(self) -> int:
        return self._max_length

    def words(self) -> frozenset[str]:
        return frozenset(e.text for entries in self._by_reading.values() for e in entries)

    def lookup(self, readings: tuple[str, ...]) -> tuple[LexiconEntry, ...]:
        """空 tuple 表示這個讀音確定沒有詞條。"""
        return self._by_reading.get(readings, ())

    def log10_probability(self, entry: LexiconEntry) -> float:
        # 以整份詞庫的權重總和正規化：單字與多字詞共用同一個分母，
        # 所以「一個詞」與「拆成數個字」的機率可以直接比較。
        return math.log10(entry.frequency / self._total_frequency)
