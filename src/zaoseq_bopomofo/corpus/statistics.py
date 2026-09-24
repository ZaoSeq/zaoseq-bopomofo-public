"""從語料重建 n-gram 統計與 CorpusLanguageModel。所有數字都由 train split 計算，沒有手動調整。"""

from __future__ import annotations

import gzip
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.corpus.normalize import is_han

BOS = "^"
EOS = "$"
DIGIT = "0"
LATIN = "A"
_DIGITS = re.compile(r"[0-9]+(?:[.,][0-9]+)*")
_LATIN = re.compile(r"[A-Za-z]+")


def tokenize(text: str) -> list[str]:
    """字元 token：漢字與標點各自一個 token；連續數字與英文字母各壓成一個類別 token，
    因為注音輸入只會產生漢字，數字的具體值對選字沒有資訊量，卻會讓 n-gram 稀疏。"""
    text = _DIGITS.sub(DIGIT, text)
    text = _LATIN.sub(LATIN, text)
    # 句首／句尾標記保留給模型使用；原文中的 ^、$ 直接捨棄，避免與標記混淆。
    return [ch for ch in text if not ch.isspace() and ch not in (BOS, EOS)]


@dataclass(frozen=True)
class NgramCounts:
    """`followers[h]` = (h 之後出現的總次數, 相異後續 token 數)，Witten–Bell 需要的是這兩個值，
    所以在剪枝低頻 trigram 之前先計算好，剪枝不影響 back-off 權重。"""

    unigrams: Mapping[str, int]
    bigrams: Mapping[str, int]
    trigrams: Mapping[str, int]
    followers: Mapping[str, tuple[int, int]]
    total_tokens: int


def count_ngrams(sentences: Iterable[str], min_trigram_count: int = 2) -> NgramCounts:
    unigrams: Counter[str] = Counter()
    bigrams: Counter[str] = Counter()
    trigrams: Counter[str] = Counter()
    for sentence in sentences:
        tokens = [BOS, BOS, *tokenize(sentence), EOS]
        for i in range(2, len(tokens)):
            unigrams[tokens[i]] += 1
            bigrams[tokens[i - 1] + tokens[i]] += 1
            trigrams[tokens[i - 2] + tokens[i - 1] + tokens[i]] += 1
    followers: dict[str, list[int]] = {}
    for gram, count in bigrams.items():
        entry = followers.setdefault(gram[:-1], [0, 0])
        entry[0] += count
        entry[1] += 1
    for gram, count in trigrams.items():
        entry = followers.setdefault(gram[:-1], [0, 0])
        entry[0] += count
        entry[1] += 1
    kept = {g: c for g, c in trigrams.items() if c >= min_trigram_count}
    return NgramCounts(
        unigrams=dict(unigrams),
        bigrams=dict(bigrams),
        trigrams=kept,
        followers={h: (v[0], v[1]) for h, v in followers.items()},
        total_tokens=sum(unigrams.values()),
    )


def count_words(sentences: Iterable[str], vocabulary: frozenset[str], max_length: int) -> Counter[str]:
    """以詞表做最長匹配分詞後統計 word unigram；詞表外的字以單字計。
    這個分詞沒有經過驗證，所以只提供 word unigram，不建立 word bigram。"""
    counts: Counter[str] = Counter()
    for sentence in sentences:
        chars = [ch for ch in sentence if is_han(ch)]
        i = 0
        while i < len(chars):
            for length in range(min(max_length, len(chars) - i), 0, -1):
                word = "".join(chars[i : i + length])
                if length == 1 or word in vocabulary:
                    counts[word] += 1
                    i += length
                    break
    return counts


class CorpusLanguageModel:
    """字元 trigram，Witten–Bell interpolated smoothing。

    P3(c | ab) = (C(abc) + T(ab)·P2(c | b)) / (C(ab·) + T(ab))，P2 同理 back-off 到 P1，
    P1(c) = (C(c) + 1) / (N + V)。V 是可能出現的字元數上限（至少含 CNS 常用字），
    所以沒見過的字也有有限的機率，任何序列的分數都不會是 -inf。
    """

    def __init__(self, counts: NgramCounts, vocabulary_size: int) -> None:
        if vocabulary_size < len(counts.unigrams):
            raise ValueError("vocabulary_size 不可小於實際出現的字元數")
        self._c = counts
        self._vocabulary_size = vocabulary_size
        self._unigram_denominator = counts.total_tokens + vocabulary_size

    @property
    def counts(self) -> NgramCounts:
        return self._c

    def probability(self, token: str, history: str) -> float:
        p1 = (self._c.unigrams.get(token, 0) + 1) / self._unigram_denominator
        p2 = self._interpolate(history[-1:], token, p1, self._c.bigrams)
        return self._interpolate(history[-2:], token, p2, self._c.trigrams) if len(history) >= 2 else p2

    def _interpolate(self, history: str, token: str, lower: float, table: Mapping[str, int]) -> float:
        stats = self._c.followers.get(history)
        if not history or stats is None:
            return lower
        total, types = stats
        return (table.get(history + token, 0) + types * lower) / (total + types)

    def log10_probability(self, token: str, history: str) -> float:
        return math.log10(self.probability(token, history))

    def score(self, text: str, left_context: str = "") -> float:
        """text 在 left_context 之後出現的 log10 機率；前文為空時以句首開始。"""
        history = [BOS, BOS, *tokenize(left_context)][-2:]
        total = 0.0
        for token in tokenize(text):
            total += self.log10_probability(token, "".join(history))
            history = [history[-1], token]
        return total

    def extend(self, history: str, char: str) -> tuple[float, str]:
        """decoder 用的增量介面：回傳 (log10 P(char | history), 新的兩字元 history)。"""
        return self.log10_probability(char, history), (history + char)[-2:]

    @staticmethod
    def initial_history(left_context: str) -> str:
        return initial_history(left_context)


def initial_history(left_context: str) -> str:
    """前文最後兩個 token；前文為空時是兩個句首標記。"""
    return "".join([BOS, BOS, *tokenize(left_context)][-2:])


def save_counts(counts: NgramCounts, words: Mapping[str, int], directory: Path, manifest: dict[str, object]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    tables: dict[str, Mapping[str, int]] = {
        "unigrams": counts.unigrams,
        "bigrams": counts.bigrams,
        "trigrams": counts.trigrams,
        "words": words,
    }
    for name, table in tables.items():
        with gzip.open(directory / f"{name}.tsv.gz", "wt", encoding="utf-8", newline="\n") as handle:
            for gram in sorted(table):
                handle.write(f"{gram}\t{table[gram]}\n")
    with gzip.open(directory / "followers.tsv.gz", "wt", encoding="utf-8", newline="\n") as handle:
        for history in sorted(counts.followers):
            total, types = counts.followers[history]
            handle.write(f"{history}\t{total}\t{types}\n")
    (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_counts(directory: Path) -> tuple[NgramCounts, dict[str, int], dict[str, object]]:
    def read(name: str) -> dict[str, int]:
        table: dict[str, int] = {}
        with gzip.open(directory / f"{name}.tsv.gz", "rt", encoding="utf-8") as handle:
            for line in handle:
                gram, count = line.rstrip("\n").split("\t")
                table[gram] = int(count)
        return table

    followers: dict[str, tuple[int, int]] = {}
    with gzip.open(directory / "followers.tsv.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            history, total, types = line.rstrip("\n").split("\t")
            followers[history] = (int(total), int(types))
    unigrams = read("unigrams")
    counts = NgramCounts(unigrams, read("bigrams"), read("trigrams"), followers, sum(unigrams.values()))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return counts, read("words"), manifest
