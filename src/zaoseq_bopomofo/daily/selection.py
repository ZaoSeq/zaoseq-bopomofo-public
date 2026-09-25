from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

PLAN_FILE = PROJECT_ROOT / "benchmarks" / "frozen" / "v0.2_selection_plan.json"
PLAN_RECORD = PROJECT_ROOT / "benchmarks" / "frozen" / "V0.2_PLAN.json"
COVERAGE_ITEMS = 300


class PlanChangedError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConfigScore:
    """一個設定在 DEV 上的全部選擇依據；teacher 指標都是 frozen fine-tuned Laya（K=4）。"""

    name: str
    production_eligible: bool
    gov_baseline_top1: float
    gov_teacher_top1: float
    coverage_teacher_top1: float
    coverage_teacher_correct_to_wrong: int
    coverage_baseline_top1: float
    coverage_mrr: float
    coverage_r5: float
    coverage_window: float
    coverage_p95_ms: float
    rss_mb: float
    artifact_mb: float


@dataclass(frozen=True)
class Reference:
    gov_baseline_top1: float
    gov_teacher_top1: float


@dataclass(frozen=True)
class Decision:
    selected: str | None
    eligible: tuple[str, ...]
    failed_gates: dict[str, tuple[str, ...]]
    tie_set: tuple[str, ...]


class SelectionPlan:
    """讀取事前凍結的 selection plan，確認雜湊與紀錄相同，並依其規則選擇設定。"""

    def __init__(self, plan_file: Path = PLAN_FILE, record_file: Path = PLAN_RECORD) -> None:
        from zaoseq_bopomofo.evaluation.freeze import content_hash

        record = json.loads(record_file.read_text(encoding="utf-8"))
        expected = record["files"][plan_file.relative_to(PROJECT_ROOT).as_posix()]
        if content_hash(plan_file) != expected:
            raise PlanChangedError(f"{plan_file} 與凍結紀錄不符")
        self.sha256 = expected
        self.plan = json.loads(plan_file.read_text(encoding="utf-8"))
        gates = next(layer for layer in self.plan["rule"] if layer["name"] == "regression_gates")
        self.gov_baseline_max_drop = float(gates["gov_baseline_top1_max_drop"])
        self.gov_teacher_max_drop = float(gates["gov_teacher_top1_max_drop"])

    def gate_failures(self, score: ConfigScore, reference: Reference) -> tuple[str, ...]:
        failures = []
        if not score.production_eligible:
            failures.append("not_production_eligible")
        if round(reference.gov_baseline_top1 - score.gov_baseline_top1, 6) > self.gov_baseline_max_drop:
            failures.append("gov_baseline_regression")
        if round(reference.gov_teacher_top1 - score.gov_teacher_top1, 6) > self.gov_teacher_max_drop:
            failures.append("gov_teacher_regression")
        return tuple(failures)

    @staticmethod
    def tie_key(score: ConfigScore) -> tuple[object, ...]:
        r = lambda v: round(v, 6)  # noqa: E731
        return (
            score.coverage_teacher_correct_to_wrong,
            -r(score.coverage_baseline_top1),
            -r(score.coverage_mrr),
            -r(score.coverage_r5),
            -r(score.coverage_window),
            r(score.coverage_p95_ms),
            r(score.rss_mb),
            r(score.artifact_mb),
            score.name,
        )

    def select(self, scores: Sequence[ConfigScore], reference: Reference) -> Decision:
        failed = {s.name: self.gate_failures(s, reference) for s in scores}
        eligible = [s for s in scores if not failed[s.name]]
        if not eligible:
            return Decision(None, (), {k: v for k, v in failed.items() if v}, ())
        best = max(s.coverage_teacher_top1 for s in eligible)
        tolerance = 1 / COVERAGE_ITEMS + 1e-9
        tied = [s for s in eligible if best - s.coverage_teacher_top1 <= tolerance]
        winner = min(tied, key=self.tie_key)
        return Decision(
            winner.name,
            tuple(s.name for s in eligible),
            {k: v for k, v in failed.items() if v},
            tuple(s.name for s in sorted(tied, key=self.tie_key)),
        )

    @staticmethod
    def to_json(decision: Decision, scores: Sequence[ConfigScore]) -> dict[str, object]:
        return {**asdict(decision), "scores": [asdict(s) for s in scores]}
