from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Iterable, Sequence
from pathlib import Path

from zaoseq_bopomofo.corpus.domains import LanguageModel
from zaoseq_bopomofo.corpus.statistics import CorpusLanguageModel, initial_history, load_counts, tokenize
from zaoseq_bopomofo.daily.corpus import LM_DIR


class MixtureLanguageModel:
    """P(c | h) = Σ w_i · P_i(c | h)。只有一個權重 > 0 的元件時直接委派，分數與該元件逐位元相同。"""

    def __init__(self, components: Sequence[tuple[str, LanguageModel, float]]) -> None:
        active = [(n, m, w) for n, m, w in components if w > 0]
        if not active:
            raise ValueError("至少需要一個權重 > 0 的元件")
        if any(not math.isfinite(w) for _, _, w in active) or abs(math.fsum(w for _, _, w in active) - 1.0) > 1e-9:
            raise ValueError("權重必須是有限數且總和為 1")
        self._components = tuple(active)
        self._single = active[0][1] if len(active) == 1 else None

    @property
    def weights(self) -> dict[str, float]:
        return {n: w for n, _, w in self._components}

    def probability(self, token: str, history: str) -> float:
        if self._single is not None:
            return self._single.probability(token, history)
        return math.fsum(w * m.probability(token, history) for _, m, w in self._components)

    def log10_probability(self, token: str, history: str) -> float:
        if self._single is not None:
            return self._single.log10_probability(token, history)
        return math.log10(self.probability(token, history))

    def score(self, text: str, left_context: str = "") -> float:
        history = initial_history(left_context)
        total = 0.0
        for token in tokenize(text):
            delta, history = self.extend(history, token)
            total += delta
        return total

    def extend(self, history: str, char: str) -> tuple[float, str]:
        if self._single is not None:
            return self._single.extend(history, char)
        return self.log10_probability(char, history), (history + char)[-2:]


class LanguageModelFactory:
    """政府模型沿用 frozen V0 的 GeneralCorpusLanguageModel（同一個 V）；日常模型的 V 為
    V0 的 V ∪ 日常語料字元，讓未見字元仍有有限機率。"""

    def __init__(self, candidate_characters: Iterable[str], lm_dir: Path = LM_DIR) -> None:
        from zaoseq_bopomofo.decoding.pipeline import DEFAULT_LM_DIR, LanguageModelConfig, load_language_model

        characters = set(candidate_characters)
        self._lm_dir = lm_dir
        self.gov = load_language_model(LanguageModelConfig.GENERAL, characters)
        raw, _, _ = load_counts(DEFAULT_LM_DIR / "raw")
        self._base_vocabulary = set(raw.unigrams) | characters
        self._daily: dict[str, CorpusLanguageModel] = {}

    def daily(self, name: str) -> CorpusLanguageModel:
        if name not in self._daily:
            counts, _, _ = load_counts(self._lm_dir / name)
            self._daily[name] = CorpusLanguageModel(counts, len(self._base_vocabulary | set(counts.unigrams)))
        return self._daily[name]

    def mixture(self, daily_name: str | None, daily_weight: float) -> LanguageModel:
        if daily_name is None or daily_weight == 0.0:
            return self.gov
        return MixtureLanguageModel([("gov", self.gov, 1.0 - daily_weight), (daily_name, self.daily(daily_name), daily_weight)])


class CachedLanguageModel:
    """以 (history, char) 快取 `extend` 的結果；回傳值與內層模型逐位元相同，只省去重複計算。
    超過 `max_entries` 時整個清空，行為仍是 deterministic。"""

    def __init__(self, inner: LanguageModel, max_entries: int = 1_000_000) -> None:
        self._inner = inner
        self._cache: dict[tuple[str, str], tuple[float, str]] = {}
        self._max = max_entries
        self.hits = 0
        self.misses = 0

    def probability(self, token: str, history: str) -> float:
        return self._inner.probability(token, history)

    def log10_probability(self, token: str, history: str) -> float:
        return self._inner.log10_probability(token, history)

    def score(self, text: str, left_context: str = "") -> float:
        return self._inner.score(text, left_context)

    def extend(self, history: str, char: str) -> tuple[float, str]:
        key = (history, char)
        found = self._cache.get(key)
        if found is not None:
            self.hits += 1
            return found
        self.misses += 1
        if len(self._cache) >= self._max:
            self._cache.clear()
        found = self._inner.extend(history, char)
        self._cache[key] = found
        return found


class BoundedLanguageModelCache:
    """有容量上限的 LRU 快取，包住 `extend`。capacity 0 = 不快取、None = 無上限（只作對照，不可用於 production）。
    回傳值與內層模型逐位元相同；淘汰順序只取決於呼叫順序，所以是 deterministic。"""

    def __init__(self, inner: LanguageModel, capacity: int | None) -> None:
        if capacity is not None and capacity < 0:
            raise ValueError("capacity 必須 >= 0 或 None")
        self._inner = inner
        self.capacity = capacity
        self._cache: OrderedDict[tuple[str, str], tuple[float, str]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def __bool__(self) -> bool:
        # decoder 以 `if lm` 判斷有沒有語言模型；空的快取也必須被視為有 LM。
        return True

    @property
    def entries(self) -> int:
        return len(self._cache)

    def probability(self, token: str, history: str) -> float:
        return self._inner.probability(token, history)

    def log10_probability(self, token: str, history: str) -> float:
        return self._inner.log10_probability(token, history)

    def score(self, text: str, left_context: str = "") -> float:
        return self._inner.score(text, left_context)

    def extend(self, history: str, char: str) -> tuple[float, str]:
        if self.capacity == 0:
            self.misses += 1
            return self._inner.extend(history, char)
        key = (history, char)
        found = self._cache.get(key)
        if found is not None:
            self.hits += 1
            self._cache.move_to_end(key)
            return found
        self.misses += 1
        found = self._inner.extend(history, char)
        self._cache[key] = found
        if self.capacity is not None and len(self._cache) > self.capacity:
            self._cache.popitem(last=False)
            self.evictions += 1
        return found

    def stats(self) -> dict[str, int | float | None]:
        calls = self.hits + self.misses
        return {
            "capacity": self.capacity,
            "entries": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": round(self.hits / calls, 4) if calls else 0.0,
        }
