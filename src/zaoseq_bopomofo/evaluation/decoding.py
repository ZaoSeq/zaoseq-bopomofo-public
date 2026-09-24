"""ExactReadingBenchmark 與 TypoToleranceBenchmark。

    python -m zaoseq_bopomofo.evaluation.decoding --output benchmarks/results/decoding_latest.json

ContextRerankingBenchmark 使用 evaluation.benchmark（固定候選集合、只比較排序）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Protocol

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.decoding.correction import ErrorKind
from zaoseq_bopomofo.evaluation.dataset import load_scenarios
from zaoseq_bopomofo.evaluation.metrics import LatencyStats, latency_stats
from zaoseq_bopomofo.phonetics.keyboard import StandardKeyboardLayout
from zaoseq_bopomofo.phonetics.parser import InvalidBopomofoError, parse_syllable
from zaoseq_bopomofo.phonetics.symbol import FINALS, INITIALS, MEDIALS, Tone
from zaoseq_bopomofo.ranking.base import CandidateRanker, RankingContext

ROOT = Path(__file__).resolve().parents[3]
NOISE_KINDS = (
    ErrorKind.TONE_MISSING,
    ErrorKind.TONE_WRONG,
    ErrorKind.INSERTION,
    ErrorKind.DELETION,
    ErrorKind.SUBSTITUTION,
    ErrorKind.ADJACENT_KEY,
)
_SLOT_SYMBOLS = {"initial": INITIALS, "medial": MEDIALS, "final": FINALS}
_HAN_RUN = re.compile(r"[㐀-䶿一-鿿]+")


@dataclass(frozen=True)
class DecodingItem:
    item_id: str
    origin: str
    left_context: str
    readings: tuple[str, ...]
    gold: str


@dataclass(frozen=True)
class SystemOutput:
    texts: tuple[str, ...]
    top_corrected: bool
    latency_ms: float


class DecodingSystem(Protocol):
    name: str

    def run(self, readings: tuple[str, ...], left_context: str) -> SystemOutput: ...


@dataclass
class SourceSystem:
    """decoder（候選來源）加上可選的 ranker；latency 包含兩者。"""

    name: str
    decode: Callable[[tuple[str, ...], str], tuple[Candidate, ...]]
    ranker: CandidateRanker | None = None

    def run(self, readings: tuple[str, ...], left_context: str) -> SystemOutput:
        started = time.perf_counter()
        candidates = self.decode(readings, left_context)
        if self.ranker is not None and candidates:
            ordered = [rc.candidate for rc in self.ranker.rank(RankingContext(left_context, readings), candidates).candidates]
        else:
            ordered = list(candidates)
        latency = (time.perf_counter() - started) * 1000.0
        return SystemOutput(
            texts=tuple(c.text for c in ordered),
            top_corrected=bool(ordered) and ordered[0].correction is not None,
            latency_ms=latency,
        )


# ---------------------------------------------------------------- items


def hand_items(seed_paths: Sequence[Path]) -> list[DecodingItem]:
    """人工 DEV / sanity 情境：讀音由人工撰寫。"""
    items: list[DecodingItem] = []
    for path in seed_paths:
        for s in load_scenarios(path):
            items.append(
                DecodingItem(
                    item_id=f"{path.parent.name}:{s.case_id}",
                    origin=f"hand:{path.parent.name}",
                    left_context=s.context,
                    readings=s.target_readings + s.suffix_readings,
                    gold=s.target + s.suffix,
                )
            )
    return items


def silver_items(
    corpus_dir: Path,
    annotator: object,
    per_source: int = 150,
    min_chars: int = 4,
    max_chars: int = 10,
) -> tuple[list[DecodingItem], dict[str, Counter[str]]]:
    """corpus test split 中的漢字片段，以規則標注讀音；多音字不確定的片段會被拒絕並計數。
    這些片段沒有參與語言模型訓練。依 sha256 排序抽樣，結果 deterministic。"""
    items: list[DecodingItem] = []
    stats: dict[str, Counter[str]] = {}
    for source_dir in sorted(p for p in corpus_dir.iterdir() if (p / "sentences.jsonl").exists()):
        counter: Counter[str] = Counter()
        pool: list[tuple[str, DecodingItem]] = []
        for line in (source_dir / "sentences.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["split"] != "test":
                continue
            for match in _HAN_RUN.finditer(row["text"]):
                clause = match.group()
                if not min_chars <= len(clause) <= max_chars:
                    continue
                result = annotator.annotate(clause)  # type: ignore[attr-defined]
                if not hasattr(result, "readings"):
                    counter[result.reason.value] += 1
                    continue
                counter["accepted"] += 1
                key = hashlib.sha256(f"{row['source_id']}\x00{row['doc_id']}\x00{clause}".encode()).hexdigest()
                pool.append(
                    (
                        key,
                        DecodingItem(
                            item_id=f"{row['source_id']}:{key[:12]}",
                            origin=f"silver:{row['source_id']}",
                            left_context=row["text"][: match.start()],
                            readings=result.readings,
                            gold=clause,
                        ),
                    )
                )
        pool.sort(key=lambda item: item[0])
        items.extend(item for _, item in pool[:per_source])
        stats[source_dir.name] = counter
    return items, stats


# ---------------------------------------------------------------- noise


def inject_noise(
    readings: tuple[str, ...],
    kind: ErrorKind,
    rng: random.Random,
    inventory: frozenset[str],
    layout: StandardKeyboardLayout,
) -> tuple[tuple[str, ...], int] | None:
    """在一個隨機音節上製造指定類型的輸入錯誤；做不到（例如沒有合法結果）時回傳 None。
    結果必須仍是合法音節：真實使用者打出不存在的音節時 IME 會直接拒絕，不需要修正。"""
    positions = list(range(len(readings)))
    rng.shuffle(positions)
    for position in positions:
        syllable = parse_syllable(readings[position])
        options: list[str] = []
        if kind is ErrorKind.TONE_MISSING and syllable.tone is not Tone.FIRST:
            options = [replace(syllable, tone=Tone.FIRST).text()]
        elif kind is ErrorKind.TONE_WRONG:
            options = [replace(syllable, tone=t).text() for t in Tone if t not in (syllable.tone, Tone.FIRST)]
        else:
            for slot, symbols in _SLOT_SYMBOLS.items():
                current = getattr(syllable, slot)
                if kind is ErrorKind.INSERTION and current is None:
                    options += [replace(syllable, **{slot: s}).text() for s in symbols]
                elif kind is ErrorKind.DELETION and current is not None:
                    options.append(replace(syllable, **{slot: None}).text())
                elif kind is ErrorKind.SUBSTITUTION and current is not None:
                    options += [replace(syllable, **{slot: s}).text() for s in symbols if s != current]
                elif kind is ErrorKind.ADJACENT_KEY and current is not None:
                    options += [
                        replace(syllable, **{slot: s}).text() for s in layout.adjacent_symbols(current) if s in symbols
                    ]
        valid = sorted({o for o in options if o in inventory and o != readings[position] and _parses(o)})
        if valid:
            noisy = rng.choice(valid)
            return readings[:position] + (noisy,) + readings[position + 1 :], position
    return None


def _parses(text: str) -> bool:
    try:
        return parse_syllable(text).has_body
    except InvalidBopomofoError:
        return False


# ---------------------------------------------------------------- metrics


@dataclass(frozen=True)
class DecodeScore:
    items: int
    sentence_accuracy: float | None
    character_accuracy: float | None
    recall_at: dict[int, float]
    corrected_top: int
    latency: LatencyStats


def score_outputs(pairs: Sequence[tuple[DecodingItem, SystemOutput]], ks: Sequence[int] = (1, 5, 10)) -> DecodeScore:
    n = len(pairs)
    chars = correct_chars = 0
    for item, out in pairs:
        top = out.texts[0] if out.texts else ""
        chars += len(item.gold)
        correct_chars += sum(a == b for a, b in zip(top, item.gold)) if len(top) == len(item.gold) else 0
    return DecodeScore(
        items=n,
        sentence_accuracy=sum(bool(o.texts) and o.texts[0] == i.gold for i, o in pairs) / n if n else None,
        character_accuracy=correct_chars / chars if chars else None,
        recall_at={k: sum(i.gold in o.texts[:k] for i, o in pairs) / n for k in ks} if n else {},
        corrected_top=sum(o.top_corrected for _, o in pairs),
        latency=latency_stats([o.latency_ms for _, o in pairs]),
    )


@dataclass(frozen=True)
class CleanInputSafety:
    """只在正確輸入上計算：
    - false_correction_rate：第一名候選帶有讀音修正（系統改了使用者其實打對的輸入）。
    - exact_input_regression_rate：exact-only 系統第一名正確，但這個系統第一名錯誤。"""

    items: int
    false_correction_rate: float | None
    exact_input_regressions: int
    exact_input_regression_rate: float | None


def clean_input_safety(
    items: Sequence[DecodingItem], system: Sequence[SystemOutput], exact_only: Sequence[SystemOutput]
) -> CleanInputSafety:
    n = len(items)
    regressions = sum(
        bool(e.texts) and e.texts[0] == i.gold and not (s.texts and s.texts[0] == i.gold)
        for i, s, e in zip(items, system, exact_only)
    )
    return CleanInputSafety(
        items=n,
        false_correction_rate=sum(s.top_corrected for s in system) / n if n else None,
        exact_input_regressions=regressions,
        exact_input_regression_rate=regressions / n if n else None,
    )


# ---------------------------------------------------------------- runner


def run(
    systems: Sequence[DecodingSystem],
    items: Sequence[DecodingItem],
    inventory: frozenset[str],
    exact_reference: str,
    warmup: int = 3,
) -> dict[str, object]:
    layout = StandardKeyboardLayout()
    noisy: dict[ErrorKind, list[tuple[DecodingItem, tuple[str, ...]]]] = {k: [] for k in NOISE_KINDS}
    for item in items:
        for kind in NOISE_KINDS:
            rng = random.Random(f"{item.item_id}\x00{kind.value}")
            injected = inject_noise(item.readings, kind, rng, inventory, layout)
            if injected is not None:
                noisy[kind].append((item, injected[0]))

    clean_outputs: dict[str, list[SystemOutput]] = {}
    report: dict[str, object] = {"items": len(items), "noise_items": {k.value: len(v) for k, v in noisy.items()}, "systems": {}}
    for system in systems:
        for item in items[:warmup]:
            system.run(item.readings, item.left_context)
        clean = [system.run(i.readings, i.left_context) for i in items]
        clean_outputs[system.name] = clean
        by_origin: dict[str, DecodeScore] = {}
        for origin in sorted({i.origin.split(":")[0] for i in items}):
            pairs = [(i, o) for i, o in zip(items, clean) if i.origin.startswith(origin)]
            by_origin[origin] = score_outputs(pairs)
        typo: dict[str, DecodeScore] = {}
        for kind, cases in noisy.items():
            pairs = [(item, system.run(readings, item.left_context)) for item, readings in cases]
            typo[kind.value] = score_outputs(pairs)
        report["systems"][system.name] = {  # type: ignore[index]
            "exact": {k: asdict(v) for k, v in by_origin.items()},
            "exact_all": asdict(score_outputs(list(zip(items, clean)))),
            "typo": {k: asdict(v) for k, v in typo.items()},
        }
    reference = clean_outputs[exact_reference]
    for name, outputs in clean_outputs.items():
        report["systems"][name]["clean_input_safety"] = asdict(clean_input_safety(items, outputs, reference))  # type: ignore[index]
    return report


def format_report(report: dict[str, object]) -> str:
    def f(value: object, digits: int = 3) -> str:
        return "n/a" if value is None else f"{value:.{digits}f}"  # type: ignore[str-format]

    systems: dict[str, dict[str, object]] = report["systems"]  # type: ignore[assignment]
    lines = [f"items: {report['items']}, noise items: {report['noise_items']}", ""]
    origins = sorted({o for s in systems.values() for o in s["exact"]})  # type: ignore[union-attr]
    lines += ["### ExactReadingBenchmark", "",
              "| system | set | n | sentence acc | char acc | R@1 | R@5 | R@10 | p50 ms | p95 ms |", "|" + "---|" * 10]
    for name, s in systems.items():
        for origin in origins:
            e = s["exact"][origin]  # type: ignore[index]
            r = e["recall_at"]
            lines.append(
                f"| {name} | {origin} | {e['items']} | {f(e['sentence_accuracy'])} | {f(e['character_accuracy'])} "
                f"| {f(r.get(1))} | {f(r.get(5))} | {f(r.get(10))} | {f(e['latency']['p50_ms'], 1)} | {f(e['latency']['p95_ms'], 1)} |"
            )
    lines += ["", "### Clean input safety（正確輸入）", "",
              "| system | n | false correction rate | exact-input regressions | regression rate |", "|---|---|---|---|---|"]
    for name, s in systems.items():
        c = s["clean_input_safety"]  # type: ignore[index]
        lines.append(f"| {name} | {c['items']} | {f(c['false_correction_rate'])} | {c['exact_input_regressions']} | {f(c['exact_input_regression_rate'])} |")
    kinds = list(report["noise_items"])  # type: ignore[arg-type]
    lines += ["", "### TypoToleranceBenchmark：sentence recovery（R@5）", "",
              "| system | " + " | ".join(kinds) + " |", "|" + "---|" * (len(kinds) + 1)]
    for name, s in systems.items():
        cells = [f"{f(s['typo'][k]['sentence_accuracy'])} ({f(s['typo'][k]['recall_at'].get(5))})" for k in kinds]  # type: ignore[index]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines += ["", "### Latency on noisy input（p50 / p95 ms）", "", "| system | " + " | ".join(kinds) + " |", "|" + "---|" * (len(kinds) + 1)]
    for name, s in systems.items():
        cells = [f"{f(s['typo'][k]['latency']['p50_ms'], 1)} / {f(s['typo'][k]['latency']['p95_ms'], 1)}" for k in kinds]  # type: ignore[index]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.evaluation.decoding")
    parser.add_argument("--silver-per-source", type=int, default=150)
    parser.add_argument("--no-laya", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    from zaoseq_bopomofo.corpus.annotate import ReadingAnnotator
    from zaoseq_bopomofo.decoding.generator import CandidateGenerator
    from zaoseq_bopomofo.decoding.pipeline import (
        DecoderSettings,
        build_tolerant_decoder,
        lexicon_characters,
        load_language_model,
    )
    from zaoseq_bopomofo.decoding.scoring import LinearScorer
    from zaoseq_bopomofo.decoding.tolerant import TolerancePolicy
    from zaoseq_bopomofo.lexicon.builder import read_builtin, read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS, load_lexicon

    loaded = load_lexicon()
    lm = load_language_model(candidate_characters=lexicon_characters(loaded))
    annotator = ReadingAnnotator(read_char_readings(DEFAULT_CHAR_READINGS), read_builtin(DEFAULT_BUILTIN))
    items = hand_items([ROOT / "benchmarks" / "dev" / "seeds.jsonl", ROOT / "benchmarks" / "sanity" / "seeds.jsonl"])
    silver, annotation_stats = silver_items(ROOT / "data" / "corpus", annotator, per_source=args.silver_per_source)
    items += silver

    corpus_only = LinearScorer(corpus_weight=1.0, lexical_weight=0.0)
    corpus_lexical = LinearScorer(corpus_weight=1.0, lexical_weight=1.0)
    exact_policy = TolerancePolicy(enabled=False)
    lexicon_generator = CandidateGenerator(loaded.lexicon)
    decoders = {
        "lexicon-exact": lexicon_generator.candidates_for,
        "corpus-exact": build_tolerant_decoder(loaded, lm, DecoderSettings(scorer=corpus_only, policy=exact_policy)).candidates_for,
        "corpus-tolerant": build_tolerant_decoder(loaded, lm, DecoderSettings(scorer=corpus_only)).candidates_for,
        "corpus+lexicon-tolerant": build_tolerant_decoder(loaded, lm, DecoderSettings(scorer=corpus_lexical)).candidates_for,
    }
    systems: list[DecodingSystem] = [SourceSystem(name, decode) for name, decode in decoders.items()]
    report = run(systems, items, frozenset(loaded.lexicon.syllables), exact_reference="corpus-exact")
    report["annotation"] = {k: dict(v) for k, v in annotation_stats.items()}
    report["item_origins"] = dict(Counter(i.origin for i in items))
    print(format_report(report))
    print("\nannotation (silver):", json.dumps(report["annotation"], ensure_ascii=False))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".md").write_text(format_report(report) + "\n", encoding="utf-8")
        print(f"report -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
