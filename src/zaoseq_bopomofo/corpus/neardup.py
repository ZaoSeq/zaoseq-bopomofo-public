"""近重複句偵測：只保留漢字後取字元 n-gram，MinHash LSH 找候選，再以精確 Jaccard 確認。

用於 TRAIN / DEV / TEST 的洩漏控制；精確重複已由語料 build 的全域去重處理，這裡處理的是
「換了幾個字的同一句」（例如同一段 FAQ 模板只改機關名稱）。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from zaoseq_bopomofo.corpus.sentences import dedupe_key

_PRIME = (1 << 61) - 1


def normalize(text: str) -> str:
    return dedupe_key(text)


def shingles(text: str, n: int = 4) -> np.ndarray:
    key = normalize(text)
    if not key:
        return np.empty(0, dtype=np.uint64)
    grams = {key[i : i + n] for i in range(max(1, len(key) - n + 1))}
    values = [int.from_bytes(hashlib.blake2b(g.encode("utf-8"), digest_size=8).digest(), "little") for g in grams]
    return np.unique(np.array(values, dtype=np.uint64))


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    inter = np.intersect1d(a, b, assume_unique=True).size
    return inter / (a.size + b.size - inter)


@dataclass(frozen=True)
class Match:
    key: str
    similarity: float


class NearDuplicateIndex:
    """`threshold` 是 Jaccard 門檻；bands × rows 決定 LSH 的召回，預設在 J≈0.5 時約 50% 命中，
    J≥0.7 時幾乎必中，所以門檻 0.7 以上的近重複不會漏掉。"""

    def __init__(self, threshold: float = 0.7, n: int = 4, bands: int = 16, rows: int = 4, seed: int = 20260923) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold 必須介於 (0, 1]")
        self.threshold = threshold
        self.n = n
        self._bands = bands
        self._rows = rows
        rng = np.random.default_rng(seed)
        size = bands * rows
        self._a = rng.integers(1, _PRIME, size=size, dtype=np.uint64)
        self._b = rng.integers(0, _PRIME, size=size, dtype=np.uint64)
        self._buckets: list[dict[bytes, list[int]]] = [dict() for _ in range(bands)]
        self._keys: list[str] = []
        self._shingles: list[np.ndarray] = []

    def __len__(self) -> int:
        return len(self._keys)

    def _signature(self, values: np.ndarray) -> np.ndarray:
        # (a·x + b) mod p 以 uint64 溢位近似；只需要是固定的雜湊族，不需要精確的模運算。
        with np.errstate(over="ignore"):
            hashed = values[None, :] * self._a[:, None] + self._b[:, None]
        return hashed.min(axis=1)

    def _band_keys(self, signature: np.ndarray) -> list[bytes]:
        return [signature[i * self._rows : (i + 1) * self._rows].tobytes() for i in range(self._bands)]

    def add(self, key: str, text: str) -> None:
        values = shingles(text, self.n)
        if values.size == 0:
            return
        index = len(self._keys)
        self._keys.append(key)
        self._shingles.append(values)
        for band, bucket_key in enumerate(self._band_keys(self._signature(values))):
            self._buckets[band].setdefault(bucket_key, []).append(index)

    def add_all(self, rows: Iterable[tuple[str, str]]) -> None:
        for key, text in rows:
            self.add(key, text)

    def query(self, text: str) -> list[Match]:
        values = shingles(text, self.n)
        if values.size == 0:
            return []
        candidates: set[int] = set()
        for band, bucket_key in enumerate(self._band_keys(self._signature(values))):
            candidates.update(self._buckets[band].get(bucket_key, ()))
        matches = [Match(self._keys[i], jaccard(values, self._shingles[i])) for i in candidates]
        return sorted((m for m in matches if m.similarity >= self.threshold), key=lambda m: (-m.similarity, m.key))

    def is_duplicate(self, text: str) -> bool:
        return bool(self.query(text))
