from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from zaoseq_bopomofo.corpus.statistics import BOS, EOS, tokenize

MIN_COUNT = 2
KN_DISCOUNT = 0.75


def padded(text: str, order: int) -> list[str]:
    return [BOS] * (order - 1) + tokenize(text) + [EOS]


def history_of(left_context: str, order: int) -> str:
    """前文最後 order-1 個 token（不足時以句首標記補齊）。"""
    return "".join(([BOS] * (order - 1) + tokenize(left_context))[-(order - 1) :])


@dataclass
class NgramTables:
    """`counts[m]`：m-gram 原始次數（m ≥ 3 只保留次數 ≥ MIN_COUNT）。
    `followers[h]`：剪枝前 h 之後的 (總次數, 相異 token 數)；長度 ≥ 3 的 history 只保留總次數 ≥ MIN_COUNT 者。
    `continuation[m]`／`cont_followers[h]`：Kneser–Ney 低階用的相異左延伸數與其 (總和, 相異數)。"""

    order: int
    counts: list[dict[str, int]]
    followers: dict[str, tuple[int, int]]
    continuation: list[dict[str, int]]
    cont_followers: dict[str, tuple[int, int]]
    total_tokens: int


class NgramBuilder:
    """由高階往低階逐階計數，每一階用完即剪枝，避免同時保留所有未剪枝的表。"""

    def __init__(self, order: int, min_count: int = MIN_COUNT, continuation: bool = True) -> None:
        if order < 2:
            raise ValueError("order 至少為 2")
        self._order = order
        self._min = min_count
        self._continuation = continuation

    def build(self, texts: Sequence[str]) -> NgramTables:
        n = self._order
        tokens = [padded(t, n) for t in texts]
        counts: list[dict[str, int]] = [{} for _ in range(n + 1)]
        continuation: list[dict[str, int]] = [{} for _ in range(n + 1)]
        followers: dict[str, tuple[int, int]] = {}
        cont_followers: dict[str, tuple[int, int]] = {}
        for m in range(n, 0, -1):
            table: Counter[str] = Counter()
            for seq in tokens:
                for i in range(n - 1, len(seq)):
                    if i - m + 1 >= 0:
                        table["".join(seq[i - m + 1 : i + 1])] += 1
            if m >= 2:
                self._followers(table, followers, long_history=m >= 4)
            if self._continuation and m >= 2:
                left: Counter[str] = Counter(g[1:] for g in table)
                continuation[m - 1] = dict(left)
                if m - 1 >= 2:
                    self._followers(left, cont_followers, long_history=m >= 5)
            counts[m] = {g: c for g, c in table.items() if m < 3 or c >= self._min}
        for m in range(3, n):
            continuation[m] = {g: c for g, c in continuation[m].items() if c >= self._min}
        total = sum(counts[1].values())
        return NgramTables(n, counts, followers, continuation, cont_followers, total)

    def _followers(self, table: Counter[str], out: dict[str, tuple[int, int]], long_history: bool) -> None:
        stats: dict[str, list[int]] = {}
        for gram, count in table.items():
            entry = stats.setdefault(gram[:-1], [0, 0])
            entry[0] += count
            entry[1] += 1
        for history, (total, types) in stats.items():
            if not long_history or total >= self._min:
                out[history] = (total, types)


class NgramModel:
    """字元 n-gram 的共同介面：decoder 用 extend() 逐字計分，history 為最後 order-1 個 token。"""

    def __init__(self, tables: NgramTables, vocabulary_size: int) -> None:
        if vocabulary_size < len(tables.counts[1]):
            raise ValueError("vocabulary_size 不可小於實際出現的字元數")
        self.tables = tables
        self.order = tables.order
        self._v = vocabulary_size

    def probability(self, token: str, history: str) -> float:
        raise NotImplementedError

    def log10_probability(self, token: str, history: str) -> float:
        return math.log10(self.probability(token, history))

    def extend(self, history: str, char: str) -> tuple[float, str]:
        return self.log10_probability(char, history), (history + char)[-(self.order - 1) :]

    def initial_history(self, left_context: str) -> str:
        return history_of(left_context, self.order)

    def score(self, text: str, left_context: str = "") -> float:
        history = self.initial_history(left_context)
        total = 0.0
        for token in tokenize(text):
            delta, history = self.extend(history, token)
            total += delta
        return total


class WittenBellModel(NgramModel):
    """P_m(c | h) = (C(hc) + T(h)·P_{m-1}(c | h')) / (N(h) + T(h))；P_1(c) = (C(c) + 1) / (N + V)。
    order 3 時與 v0.2 的 CorpusLanguageModel 相同。"""

    def probability(self, token: str, history: str) -> float:
        t = self.tables
        p = (t.counts[1].get(token, 0) + 1) / (t.total_tokens + self._v)
        for m in range(2, self.order + 1):
            h = history[len(history) - (m - 1) :] if len(history) >= m - 1 else None
            if h is None:
                break
            stats = t.followers.get(h)
            if stats is None:
                continue
            total, types = stats
            p = (t.counts[m].get(h + token, 0) + types * p) / (total + types)
        return p


class KneserNeyModel(NgramModel):
    """interpolated Kneser–Ney（單一 discount）：最高階用原始次數，低階用相異左延伸數。"""

    def __init__(self, tables: NgramTables, vocabulary_size: int, discount: float = KN_DISCOUNT) -> None:
        super().__init__(tables, vocabulary_size)
        self._d = discount
        unigram = tables.continuation[1]
        self._unigram_total = sum(unigram.values())
        self._unigram_types = len(unigram)

    def probability(self, token: str, history: str) -> float:
        t, d = self.tables, self._d
        p = (max(t.continuation[1].get(token, 0) - d, 0.0) + d * self._unigram_types / self._v) / self._unigram_total
        for m in range(2, self.order + 1):
            if len(history) < m - 1:
                break
            h = history[len(history) - (m - 1) :]
            highest = m == self.order
            stats = (t.followers if highest else t.cont_followers).get(h)
            if stats is None:
                continue
            total, types = stats
            numerator = (t.counts[m] if highest else t.continuation[m]).get(h + token, 0)
            p = (max(numerator - d, 0.0) + d * types * p) / total
        return p


class NgramMixture:
    """P(c | h) = Σ w_i · P_i(c | h)；元件可以是不同階數，history 保留最長元件需要的長度。"""

    def __init__(self, components: Sequence[tuple[str, NgramModel, float]]) -> None:
        active = [(n, m, w) for n, m, w in components if w > 0]
        if not active or abs(math.fsum(w for _, _, w in active) - 1.0) > 1e-9:
            raise ValueError("權重必須為正且總和為 1")
        self._components = tuple(active)
        self.order = max(m.order for _, m, _ in active)

    def probability(self, token: str, history: str) -> float:
        return math.fsum(w * m.probability(token, history) for _, m, w in self._components)

    def log10_probability(self, token: str, history: str) -> float:
        return math.log10(self.probability(token, history))

    def extend(self, history: str, char: str) -> tuple[float, str]:
        return self.log10_probability(char, history), (history + char)[-(self.order - 1) :]

    def initial_history(self, left_context: str) -> str:
        return history_of(left_context, self.order)

    def score(self, text: str, left_context: str = "") -> float:
        history = self.initial_history(left_context)
        total = 0.0
        for token in tokenize(text):
            delta, history = self.extend(history, token)
            total += delta
        return total


def vocabulary(texts: Iterable[str]) -> set[str]:
    return {token for text in texts for token in tokenize(text)}
