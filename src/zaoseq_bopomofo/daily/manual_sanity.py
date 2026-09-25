from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig
from zaoseq_bopomofo.daily.round3 import RESULTS, V0, SystemConfig, SystemFactory

TOP_N = 5


@dataclass(frozen=True)
class SanityInput:
    """只觀察的固定輸入：不影響選擇、不調參、不當作準確率。"""

    label: str
    expected: str
    readings: tuple[str, ...]


INPUTS = (
    SanityInput("再去台北玩", "我想要再去台北玩", ("ㄨㄛˇ", "ㄒㄧㄤˇ", "ㄧㄠˋ", "ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ", "ㄨㄢˊ")),
    SanityInput("西門町嗎（輕聲）", "你要去西門町嗎", ("ㄋㄧˇ", "ㄧㄠˋ", "ㄑㄩˋ", "ㄒㄧ", "ㄇㄣˊ", "ㄉㄧㄥ", "ㄇㄚ˙")),
    SanityInput("西門町嗎（一聲）", "你要去西門町嗎", ("ㄋㄧˇ", "ㄧㄠˋ", "ㄑㄩˋ", "ㄒㄧ", "ㄇㄣˊ", "ㄉㄧㄥ", "ㄇㄚ")),
    SanityInput("今天要幹嘛", "你今天要幹嘛", ("ㄋㄧˇ", "ㄐㄧㄣ", "ㄊㄧㄢ", "ㄧㄠˋ", "ㄍㄢˋ", "ㄇㄚˊ")),
    SanityInput("等等再回你", "我等等再回你", ("ㄨㄛˇ", "ㄉㄥˇ", "ㄉㄥˇ", "ㄗㄞˋ", "ㄏㄨㄟˊ", "ㄋㄧˇ")),
    SanityInput("吃飯嗎（輕聲）", "你有吃飯嗎", ("ㄋㄧˇ", "ㄧㄡˇ", "ㄔ", "ㄈㄢˋ", "ㄇㄚ˙")),
    SanityInput("吃飯嗎（一聲）", "你有吃飯嗎", ("ㄋㄧˇ", "ㄧㄡˇ", "ㄔ", "ㄈㄢˋ", "ㄇㄚ")),
)


class ManualSanity:
    """每個系統對固定輸入的 decoder 前幾名與 frozen teacher（K=4）的選擇。"""

    def __init__(self, systems: Sequence[tuple[SystemConfig, int | None | str]]) -> None:
        self._systems = systems

    def observe(self) -> dict[str, object]:
        from zaoseq_bopomofo.daily.experiments import TeacherObserver
        from zaoseq_bopomofo.ranking.base import RankingContext

        factory = SystemFactory()
        ranker = TeacherObserver().ranker(4)
        out: dict[str, object] = {}
        for system, capacity in self._systems:
            ctx = factory.context(system, capacity)
            lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
            rows = []
            for item in INPUTS:
                candidates = lattice.generate(item.readings, "").candidates
                texts = [c.text for c in candidates]
                keys = [ctx.key(t) for t in texts]
                expected = ctx.key(item.expected)
                pick = ranker.rank(RankingContext("", item.readings), candidates).candidates[0].candidate.text if candidates else ""
                rows.append(
                    {
                        "input": item.label,
                        "expected": item.expected,
                        "decoder_top": texts[:TOP_N],
                        "expected_decoder_rank": keys.index(expected) + 1 if expected in keys else None,
                        "teacher_pick": pick,
                        "teacher_matches_expected": ctx.key(pick) == expected,
                    }
                )
            out[system.name] = rows
        return out


def main(winner_name: str, daily_lm: str, lexicon_path: str, capacity: int, output: str | None = None) -> int:
    winner = SystemConfig(winner_name, daily_lm, 0.5, Path(lexicon_path))
    report = {
        "note": "observation only: not used for selection, tuning or accuracy",
        "systems": {"V0": "frozen V0", winner_name: {"daily_lm": daily_lm, "daily_weight": 0.5, "lexicon": Path(lexicon_path).name, "lm_cache_entries": capacity}},
        "observations": ManualSanity([(V0, "none"), (winner, capacity)]).observe(),
    }
    path = Path(output) if output else RESULTS / "daily_round3_manual_sanity.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])))
