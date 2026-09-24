"""量測 contextual backend 對選項呈現順序的敏感度；結果是觀察紀錄，不參與排序。"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from zaoseq_bopomofo.evaluation.dataset import RankingCase
from zaoseq_bopomofo.ranking.contextual import ChoiceDistribution, ChoiceOption, ChoiceRequest

Decide = Callable[[ChoiceRequest], ChoiceDistribution]


@dataclass(frozen=True)
class OrderBiasSummary:
    """
    - top1_flip_rate：同一組候選只因順序不同，第一名就改變的 case 比例。
    - first_position_win_rate：放在第一個位置的選項剛好勝出的比例；沒有位置偏好時期望值為 chance_rate。
    - mean_probability_spread：同一候選在不同順序下機率的 (max - min)，對所有候選與 case 取平均。
    - single_order_agreement：原始順序（baseline 順序）的第一名，與全排列平均後第一名相同的比例。
    """

    cases: int
    orders_per_case: int
    top1_flip_rate: float | None
    first_position_win_rate: float | None
    chance_rate: float | None
    mean_probability_spread: float | None
    single_order_agreement: float | None


def measure_order_bias(cases: Sequence[RankingCase], decide: Decide, window: int = 4) -> OrderBiasSummary:
    """`decide` 必須是單一順序的 backend（例如 OrderMode.SINGLE），否則量到的是已去偏的結果。"""
    flips = first_wins = decisions = agreements = 0
    spreads: list[float] = []
    chance: list[float] = []
    evaluated = 0
    orders_per_case = 0
    for case in cases:
        options = tuple(
            ChoiceOption(f"c{i}", text) for i, text in enumerate(case.candidates[:window])
        )
        if len(options) < 2:
            continue
        evaluated += 1
        per_candidate: dict[str, list[float]] = {o.candidate_id: [] for o in options}
        winners: set[str] = set()
        original_winner = ""
        permutations = list(itertools.permutations(options))
        orders_per_case = max(orders_per_case, len(permutations))
        for index, order in enumerate(permutations):
            result = decide(ChoiceRequest(case.left_context, case.readings, tuple(order)))
            probabilities = dict(result.probabilities)
            winner = max(order, key=lambda o: (probabilities[o.candidate_id], -int(o.candidate_id[1:]))).candidate_id
            winners.add(winner)
            if index == 0:
                original_winner = winner
            first_wins += winner == order[0].candidate_id
            decisions += 1
            for cid, value in probabilities.items():
                per_candidate[cid].append(float(value))
        chance.append(1.0 / len(options))
        flips += len(winners) > 1
        spreads.extend(max(v) - min(v) for v in per_candidate.values())
        averaged = {cid: math.fsum(v) / len(v) for cid, v in per_candidate.items()}
        best = max(averaged, key=lambda cid: (averaged[cid], -int(cid[1:])))
        agreements += best == original_winner
    return OrderBiasSummary(
        cases=evaluated,
        orders_per_case=orders_per_case,
        top1_flip_rate=flips / evaluated if evaluated else None,
        first_position_win_rate=first_wins / decisions if decisions else None,
        chance_rate=math.fsum(chance) / len(chance) if chance else None,
        mean_probability_spread=math.fsum(spreads) / len(spreads) if spreads else None,
        single_order_agreement=agreements / evaluated if evaluated else None,
    )
