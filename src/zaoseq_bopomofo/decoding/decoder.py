"""以 unigram 詞庫對讀音序列做 k-best 分詞。"""

from __future__ import annotations

from dataclasses import dataclass

from zaoseq_bopomofo.lexicon.entry import LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon


@dataclass(frozen=True)
class Composition:
    segments: tuple[LexiconEntry, ...]
    log10_probability: float

    @property
    def text(self) -> str:
        return "".join(e.text for e in self.segments)


class Decoder:
    """讀音序列 → 最可能的 k 種分詞組合。

    DP 狀態是「讀音前綴 i 的前 k 名組合」。每個 span 只展開詞庫排序最前面的
    `entries_per_span` 個詞條：單音節常有上百個同音字，全部展開會讓 k-best 被
    大量低頻組合塞滿，卻幾乎不可能勝出。
    同文字但不同分段的組合只保留分數最高者，避免候選清單出現重複文字。
    """

    def __init__(self, lexicon: Lexicon, beam: int = 10, entries_per_span: int = 5) -> None:
        if beam < 1 or entries_per_span < 1:
            raise ValueError("beam 與 entries_per_span 必須 >= 1")
        self._lexicon = lexicon
        self._beam = beam
        self._entries_per_span = entries_per_span

    def decode(self, readings: tuple[str, ...]) -> tuple[Composition, ...]:
        """無法完整覆蓋讀音時回傳空 tuple（例如中間有詞庫沒有的音節）。"""
        n = len(readings)
        if n == 0:
            return ()
        best: list[list[Composition]] = [[] for _ in range(n + 1)]
        best[0] = [Composition(segments=(), log10_probability=0.0)]
        max_len = max(1, self._lexicon.max_word_length)
        for end in range(1, n + 1):
            pool: dict[str, Composition] = {}
            for length in range(1, min(max_len, end) + 1):
                start = end - length
                if not best[start]:
                    continue
                entries = self._lexicon.lookup(readings[start:end])[: self._entries_per_span]
                for prefix in best[start]:
                    for entry in entries:
                        candidate = Composition(
                            segments=prefix.segments + (entry,),
                            log10_probability=prefix.log10_probability + self._lexicon.log10_probability(entry),
                        )
                        existing = pool.get(candidate.text)
                        if existing is None or _sort_key(candidate) < _sort_key(existing):
                            pool[candidate.text] = candidate
            best[end] = sorted(pool.values(), key=_sort_key)[: self._beam]
        return tuple(best[n])


def _sort_key(composition: Composition) -> tuple[float, int, str]:
    # 同分時偏好段數少的組合（整詞優於拆字），再以文字 code point 固定順序。
    return (-composition.log10_probability, len(composition.segments), composition.text)
