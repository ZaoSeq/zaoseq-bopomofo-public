"""Temporal benchmark 資料格式：同一個情境拆成 ImmediateRanking 與 CompositionReranking 兩種 case。"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypeVar

from zaoseq_bopomofo.decoding.candidate import Candidate, CandidateKind
from zaoseq_bopomofo.decoding.generator import CandidateGenerator
from zaoseq_bopomofo.phonetics.parser import parse_syllable


_T = TypeVar("_T")


class CaseFormatError(ValueError):
    """載入時就失敗，避免 benchmark 默默略過資料而讓分母變小。"""


@dataclass(frozen=True)
class Scenario:
    """人工撰寫的輸入情境。

    時間 t0：使用者剛輸入 `target_readings`；t1：接著輸入了 `suffix_readings`（可為空）。
    `acceptable_at_t0` 是 t0 時只憑 `context` 與目標讀音仍合理的答案，必含 `target`。
    `final_answers` 是 t1 時可接受的完整句子（例如台北／臺北）；空 tuple 表示只有 target + suffix。
    """

    case_id: str
    context: str
    target: str
    target_readings: tuple[str, ...]
    suffix: str
    suffix_readings: tuple[str, ...]
    acceptable_at_t0: tuple[str, ...]
    tags: tuple[str, ...] = ()
    final_answers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.target) != len(self.target_readings) or len(self.suffix) != len(self.suffix_readings):
            raise CaseFormatError(f"{self.case_id}: 文字與讀音數量不一致")
        if self.final_answers and self.target + self.suffix not in self.final_answers:
            raise CaseFormatError(f"{self.case_id}: final_answers 必須包含 target + suffix")
        if self.target not in self.acceptable_at_t0:
            raise CaseFormatError(f"{self.case_id}: acceptable_at_t0 必須包含 target")


@dataclass(frozen=True)
class RankingCase:
    """一個封閉候選集合與它的正確答案集合。`candidates` 依 baseline 順序排列。

    ImmediateRanking：`answers` 是 t0 時所有合理答案，可能多於一個。
    CompositionReranking：`answers` 只有完整 composition，`target_length` 是目標段的字數。
    """

    case_id: str
    left_context: str
    readings: tuple[str, ...]
    candidates: tuple[str, ...]
    baseline_scores: tuple[float, ...]
    answers: tuple[str, ...]
    target: str
    target_length: int
    ambiguous_at_t0: bool
    tags: tuple[str, ...] = ()
    # 使用者最終意圖可接受的目標段寫法（例如台／臺）；空 tuple 表示只有 target。
    target_variants: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidates or len(set(self.candidates)) != len(self.candidates):
            raise CaseFormatError(f"{self.case_id}: 候選為空或重複")
        if len(self.baseline_scores) != len(self.candidates) or not all(map(math.isfinite, self.baseline_scores)):
            raise CaseFormatError(f"{self.case_id}: baseline_scores 不合法")
        if not self.answers or any(a not in self.candidates for a in self.answers):
            raise CaseFormatError(f"{self.case_id}: answers 必須非空且都在候選中")

    def is_target(self, segment: str) -> bool:
        return segment == self.target or segment in self.target_variants

    def answer_rank(self, ordered_texts: Sequence[str]) -> int:
        """最前面的正確答案名次（0-based）。"""
        return min(ordered_texts.index(a) for a in self.answers)

    def to_candidates(self) -> tuple[Candidate, ...]:
        kind = CandidateKind.WORD if len(self.readings) == 1 else CandidateKind.COMPOSITION
        return tuple(
            Candidate(text=text, readings=self.readings, baseline_score=score, baseline_rank=rank, kind=kind)
            for rank, (text, score) in enumerate(zip(self.candidates, self.baseline_scores))
        )


def load_scenarios(path: Path) -> tuple[Scenario, ...]:
    scenarios: list[Scenario] = []
    for data in _read_jsonl(path):
        scenarios.append(
            Scenario(
                case_id=data["id"],
                context=data["context"],
                target=data["target"],
                # 以 parser 正規化，手寫讀音格式錯誤時在這裡就失敗。
                target_readings=tuple(parse_syllable(r).text() for r in data["target_readings"]),
                suffix=data.get("suffix", ""),
                suffix_readings=tuple(parse_syllable(r).text() for r in data.get("suffix_readings", [])),
                acceptable_at_t0=tuple(data["acceptable_at_t0"]),
                tags=tuple(data.get("tags", ())),
                final_answers=tuple(data.get("final_answers", ())),
            )
        )
    return _unique(scenarios, path)


def load_cases(path: Path) -> tuple[RankingCase, ...]:
    cases: list[RankingCase] = []
    for data in _read_jsonl(path):
        cases.append(
            RankingCase(
                case_id=data["case_id"],
                left_context=data["left_context"],
                readings=tuple(data["readings"]),
                candidates=tuple(data["candidates"]),
                baseline_scores=tuple(float(s) for s in data["baseline_scores"]),
                answers=tuple(data["answers"]),
                target=data["target"],
                target_length=int(data["target_length"]),
                ambiguous_at_t0=bool(data["ambiguous_at_t0"]),
                tags=tuple(data.get("tags", ())),
                target_variants=tuple(data.get("target_variants", ())),
            )
        )
    return _unique(cases, path)


def dump_cases(cases: Iterable[RankingCase], path: Path, header: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for line in header.splitlines():
            handle.write(f"# {line}\n")
        for case in cases:
            handle.write(json.dumps(asdict(case), ensure_ascii=False) + "\n")


@dataclass(frozen=True)
class BuildOutcome:
    immediate: tuple[RankingCase, ...]
    composition: tuple[RankingCase, ...]
    # 答案不在候選中的情境：不補進候選，因為 ranker 只能重排既有候選；這代表 decoder recall 不足。
    excluded: tuple[str, ...]


def build_cases(scenarios: Sequence[Scenario], generator: CandidateGenerator) -> BuildOutcome:
    immediate: list[RankingCase] = []
    composition: list[RankingCase] = []
    excluded: list[str] = []
    for s in scenarios:
        ambiguous = len(s.acceptable_at_t0) > 1
        variants = tuple(sorted({a[: len(s.target)] for a in s.final_answers} - {s.target}))
        t0 = generator.candidates_for(s.target_readings)
        t0_texts = tuple(c.text for c in t0)
        answers = tuple(a for a in s.acceptable_at_t0 if a in t0_texts)
        if s.target not in t0_texts:
            excluded.append(f"{s.case_id} immediate: {s.target!r} 不在候選 {t0_texts[:6]}")
        else:
            immediate.append(
                RankingCase(
                    case_id=s.case_id,
                    left_context=s.context,
                    readings=s.target_readings,
                    candidates=t0_texts,
                    baseline_scores=tuple(c.baseline_score for c in t0),
                    answers=answers,
                    target=s.target,
                    target_length=len(s.target),
                    ambiguous_at_t0=ambiguous,
                    tags=s.tags + (("ambiguous",) if ambiguous else ()),
                    target_variants=variants,
                )
            )

        readings = s.target_readings + s.suffix_readings
        expected = s.target + s.suffix
        t1 = generator.candidates_for(readings)
        t1_texts = tuple(c.text for c in t1)
        if expected not in t1_texts:
            excluded.append(f"{s.case_id} composition: {expected!r} 不在候選 {t1_texts[:4]}")
            continue
        finals = tuple(a for a in (s.final_answers or (expected,)) if a in t1_texts)
        composition.append(
            RankingCase(
                case_id=s.case_id,
                left_context=s.context,
                readings=readings,
                candidates=t1_texts,
                baseline_scores=tuple(c.baseline_score for c in t1),
                answers=finals,
                target=s.target,
                target_length=len(s.target),
                ambiguous_at_t0=ambiguous,
                tags=s.tags + (("with_suffix",) if s.suffix else ("no_suffix",)),
                target_variants=variants,
            )
        )
    return BuildOutcome(tuple(immediate), tuple(composition), tuple(excluded))


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as exc:
            raise CaseFormatError(f"{path}:{number}: {exc}") from exc


def _unique(items: list[_T], path: Path) -> tuple[_T, ...]:
    ids = [item.case_id for item in items]  # type: ignore[attr-defined]
    if len(set(ids)) != len(ids):
        raise CaseFormatError(f"{path}: id 重複")
    return tuple(items)
