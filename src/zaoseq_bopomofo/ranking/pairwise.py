"""雙向 pairwise 比較：把 closed choice 拆成兩兩比較，以 candidate identity 對齊後聚合。與具體模型無關。"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from zaoseq_bopomofo.ranking.contextual import (
    ChoiceDistribution,
    ChoiceOption,
    ChoiceRequest,
    InvalidBackendResponseError,
)
from zaoseq_bopomofo.ranking.signal import ContextSignal

OrderedPair = tuple[ChoiceOption, ChoiceOption]


@dataclass(frozen=True)
class JudgeOutput:
    """`first_wins[i]` 是第 i 個 ordered pair 中「先出現者」被選中的機率。"""

    first_wins: tuple[float, ...]
    forward_passes: int


@runtime_checkable
class PairwiseJudge(Protocol):
    @property
    def model_name(self) -> str: ...

    def judge(self, left_context: str, readings: tuple[str, ...], pairs: Sequence[OrderedPair]) -> JudgeOutput:
        """所有 pair 應在同一次批次推論中完成。"""
        ...


@runtime_checkable
class PairwiseAggregator(Protocol):
    def aggregate(self, preference: Mapping[tuple[str, str], float], ids: Sequence[str]) -> dict[str, float]:
        """`preference[(a, b)]` 是 a 勝過 b 的機率，且 preference[(a, b)] + preference[(b, a)] = 1。
        回傳總和為 1 的分佈；結果不得依賴 `ids` 的順序。"""
        ...


class MeanWinAggregator:
    """每個候選對其他候選的平均勝率，再正規化。簡單可解釋，但分佈偏平。"""

    def aggregate(self, preference: Mapping[tuple[str, str], float], ids: Sequence[str]) -> dict[str, float]:
        ordered = sorted(ids)
        wins = {a: math.fsum(preference[(a, b)] for b in ordered if b != a) / (len(ordered) - 1) for a in ordered}
        total = math.fsum(wins.values())
        return {a: wins[a] / total for a in ordered}


class BradleyTerryAggregator:
    """Bradley–Terry 強度，以 MM 演算法固定迭代次數求解。

    `prior` 是每對候選雙方各加的虛擬勝場：某候選贏下所有比較時，最大概似估計會發散到無窮大，
    prior 讓強度保持有限且可比較。迭代順序固定為 id 排序，結果與輸入順序無關。
    """

    def __init__(self, prior: float = 0.1, iterations: int = 200) -> None:
        if prior <= 0 or iterations < 1:
            raise ValueError("prior 必須 > 0，iterations 必須 >= 1")
        self._prior = prior
        self._iterations = iterations

    def aggregate(self, preference: Mapping[tuple[str, str], float], ids: Sequence[str]) -> dict[str, float]:
        ordered = sorted(ids)
        n = len(ordered)
        wins = {a: math.fsum(preference[(a, b)] + self._prior for b in ordered if b != a) for a in ordered}
        games = 1.0 + 2.0 * self._prior
        strength = {a: 1.0 / n for a in ordered}
        for _ in range(self._iterations):
            updated = {
                a: wins[a] / math.fsum(games / (strength[a] + strength[b]) for b in ordered if b != a)
                for a in ordered
            }
            total = math.fsum(updated.values())
            strength = {a: v / total for a, v in updated.items()}
        return strength


@dataclass(frozen=True)
class PairwiseDetail:
    """一次 pairwise 評估的完整中間結果，供 debug 與 explain 使用。"""

    forward: Mapping[tuple[str, str], float]
    preference: Mapping[tuple[str, str], float]
    probabilities: Mapping[str, float]
    disagreement: float
    forward_passes: int
    questions: int


class PairwiseBackend:
    """ContextualBackend 實作：k 個候選產生 k(k-1) 個 ordered pair，一次交給 judge。

    `forward[(a, b)]` 是 a 放在前面時 a 勝出的機率；對稱化後
    preference(a, b) = (forward[(a, b)] + 1 - forward[(b, a)]) / 2，
    所以位置偏好在兩個方向上互相抵銷，聚合完全依 candidate identity，不依 option index。
    """

    def __init__(self, judge: PairwiseJudge, aggregator: PairwiseAggregator | None = None) -> None:
        self._judge = judge
        self._aggregator = aggregator or BradleyTerryAggregator()

    @property
    def model_name(self) -> str:
        return f"{self._judge.model_name}#pairwise"

    def compare(self, request: ChoiceRequest) -> PairwiseDetail:
        by_id = {o.candidate_id: o for o in request.options}
        ids = sorted(by_id)
        pairs = [(by_id[a], by_id[b]) for a, b in itertools.permutations(ids, 2)]
        output = self._judge.judge(request.left_context, request.readings, pairs)
        if len(output.first_wins) != len(pairs):
            raise InvalidBackendResponseError(f"judge 回傳 {len(output.first_wins)} 個結果，預期 {len(pairs)}")
        forward: dict[tuple[str, str], float] = {}
        for (a, b), value in zip(pairs, output.first_wins):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise InvalidBackendResponseError(f"{a.candidate_id} vs {b.candidate_id} 的機率不合法：{value!r}")
            if not 0.0 <= value <= 1.0:
                raise InvalidBackendResponseError(f"{a.candidate_id} vs {b.candidate_id} 的機率超出 [0, 1]：{value!r}")
            forward[(a.candidate_id, b.candidate_id)] = float(value)

        preference: dict[tuple[str, str], float] = {}
        gaps: list[float] = []
        for a, b in itertools.combinations(ids, 2):
            a_first, b_first = forward[(a, b)], forward[(b, a)]
            preference[(a, b)] = (a_first + 1.0 - b_first) / 2.0
            preference[(b, a)] = 1.0 - preference[(a, b)]
            # 位置無關的模型應滿足 a_first == 1 - b_first；差距就是位置造成的不一致。
            gaps.append(abs(a_first - (1.0 - b_first)))

        aggregated = self._aggregator.aggregate(preference, ids)
        # 取 6 位小數消除浮點雜訊，讓本應同分的候選能走 baseline tiebreak。
        probabilities = {cid: round(p, 6) for cid, p in aggregated.items()}
        return PairwiseDetail(
            forward=forward,
            preference=preference,
            probabilities=probabilities,
            disagreement=math.fsum(gaps) / len(gaps),
            forward_passes=output.forward_passes,
            questions=len(pairs),
        )

    def decide(self, request: ChoiceRequest) -> ChoiceDistribution:
        detail = self.compare(request)
        signal = ContextSignal(
            forward_passes=detail.forward_passes,
            questions=detail.questions,
            disagreement=detail.disagreement,
        )
        return ChoiceDistribution(self.model_name, detail.probabilities, None, signal)
