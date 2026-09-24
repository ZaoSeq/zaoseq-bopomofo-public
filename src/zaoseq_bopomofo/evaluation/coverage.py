"""詞庫與 decoder 的 coverage 指標，與 ranking benchmark 分開計算。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache

from zaoseq_bopomofo.decoding.generator import CandidateGenerator
from zaoseq_bopomofo.evaluation.dataset import Scenario
from zaoseq_bopomofo.lexicon.lexicon import Lexicon


@dataclass(frozen=True)
class CoverageSummary:
    """
    - recall_at_k：完整句子（target + suffix）出現在 baseline 前 k 名候選的比例；k=0 代表不限名次。
    - oov_rate：(字, 讀音) 配對不在詞庫中的比例，以字為單位。
    - segmentation_coverage：完整句子能被切成詞庫詞條、且每段讀音吻合的比例；
      可切分但不在候選中，代表 decoder 的 N-best 截斷，而不是詞庫缺詞。
    """

    scenarios: int
    recall_at_k: dict[int, float]
    oov_rate: float | None
    segmentation_coverage: float | None


def measure_coverage(
    scenarios: Sequence[Scenario],
    lexicon: Lexicon,
    generator: CandidateGenerator,
    ks: Sequence[int] = (1, 3, 5, 0),
) -> CoverageSummary:
    hits = {k: 0 for k in ks}
    oov = total_chars = segmentable = 0
    for s in scenarios:
        text = s.target + s.suffix
        readings = s.target_readings + s.suffix_readings
        texts = [c.text for c in generator.candidates_for(readings)]
        for k in ks:
            window = texts if k == 0 else texts[:k]
            hits[k] += text in window
        for char, reading in zip(text, readings):
            total_chars += 1
            oov += not any(e.text == char for e in lexicon.lookup((reading,)))
        segmentable += _segmentable(lexicon, text, readings)
    n = len(scenarios)
    return CoverageSummary(
        scenarios=n,
        recall_at_k={k: hits[k] / n for k in ks} if n else {},
        oov_rate=oov / total_chars if total_chars else None,
        segmentation_coverage=segmentable / n if n else None,
    )


def _segmentable(lexicon: Lexicon, text: str, readings: tuple[str, ...]) -> bool:
    @lru_cache(maxsize=None)
    def reachable(start: int) -> bool:
        if start == len(text):
            return True
        for end in range(start + 1, min(len(text), start + lexicon.max_word_length) + 1):
            words = {e.text for e in lexicon.lookup(readings[start:end])}
            if text[start:end] in words and reachable(end):
                return True
        return False

    return reachable(0)
