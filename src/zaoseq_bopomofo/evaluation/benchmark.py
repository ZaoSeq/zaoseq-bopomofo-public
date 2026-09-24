"""Temporal benchmark runner 與 CLI；不依賴 web/service。

    python -m zaoseq_bopomofo.evaluation.benchmark build benchmarks/dev/seeds.jsonl benchmarks/dev
    python -m zaoseq_bopomofo.evaluation.benchmark run benchmarks/dev --output benchmarks/results/dev_latest.json
    python -m zaoseq_bopomofo.evaluation.benchmark coverage benchmarks/dev/seeds.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from zaoseq_bopomofo.evaluation.dataset import RankingCase, build_cases, dump_cases, load_cases, load_scenarios
from zaoseq_bopomofo.evaluation.metrics import (
    CaseOutcome,
    LatencyStats,
    RankingSummary,
    TemporalSummary,
    latency_stats,
    summarize,
    summarize_temporal,
)
from zaoseq_bopomofo.ranking.base import CandidateRanker, RankingContext
from zaoseq_bopomofo.ranking.confidence import ConfidenceConfig, assess_confidence

IMMEDIATE_FILE = "immediate.jsonl"
COMPOSITION_FILE = "composition.jsonl"


class RankerContractError(RuntimeError):
    """ranker 輸出不是輸入候選的排列；這是程式錯誤，benchmark 必須直接失敗。"""


class StaleCasesError(RuntimeError):
    """case 檔的候選與目前 decoder 輸出不一致，代表詞庫或 decoder 改過但沒有重建 case。"""


@dataclass(frozen=True)
class RankerReport:
    ranker: str
    immediate: RankingSummary
    immediate_unambiguous: RankingSummary
    composition: RankingSummary
    temporal: TemporalSummary
    immediate_outcomes: tuple[CaseOutcome, ...]
    composition_outcomes: tuple[CaseOutcome, ...]


def evaluate_case(
    ranker: CandidateRanker, case: RankingCase, confidence_config: ConfidenceConfig | None = None
) -> CaseOutcome:
    result = ranker.rank(RankingContext(case.left_context, case.readings), case.to_candidates())
    texts = result.texts()
    if sorted(texts) != sorted(case.candidates):
        raise RankerContractError(f"{ranker.name} 在 {case.case_id} 的輸出不是候選的排列")
    target_text = texts[0][: case.target_length]
    contextual = {
        rc.candidate.text: rc.contextual_probability
        for rc in result.candidates
        if rc.contextual_probability is not None and rc.family_representative
    }
    confidence = result.context_confidence
    if confidence is None and contextual:
        # 沒有 gating 的 ranker 也用同一套標準評估其 contextual 分佈，才能比較 high-confidence wrong。
        confidence = assess_confidence(contextual, result.signal, confidence_config or ConfidenceConfig())  # type: ignore[arg-type]
    contextual_top: str | None = None
    if contextual:
        # 同分時依 contextual 機率再依文字 code point，與 ranker 內部一樣 deterministic。
        contextual_top = min(contextual, key=lambda t: (-contextual[t], t))  # type: ignore[operator]
    return CaseOutcome(
        case_id=case.case_id,
        answer_rank=case.answer_rank(texts),
        baseline_answer_rank=case.answer_rank(case.candidates),
        status=result.status,
        fallback_reason=result.fallback.reason if result.fallback else None,
        latency_ms=result.latency_ms,
        model_latency_ms=result.model_latency_ms,
        top_text=texts[0],
        target_text=target_text,
        target_correct=case.is_target(target_text),
        ambiguous_at_t0=case.ambiguous_at_t0,
        tags=case.tags,
        contextual_top_correct=None if contextual_top is None else contextual_top in case.answers,
        context_confident=None if confidence is None else confidence.confident,
        effective_weight=result.context_confidence.effective_weight if result.context_confidence else None,
        forward_passes=result.signal.forward_passes if result.signal else 0,
        questions=result.signal.questions if result.signal else 0,
        disagreement=result.signal.disagreement if result.signal else None,
        order_instability=result.signal.order_instability if result.signal else None,
    )


def run_benchmark(
    rankers: Sequence[CandidateRanker],
    immediate: Sequence[RankingCase],
    composition: Sequence[RankingCase],
    warmup: int = 3,
) -> tuple[RankerReport, ...]:
    """`warmup` 筆 case 先各跑一次且不計時：第一次 GPU 推論包含 kernel 初始化，會讓 p95 失真。"""
    reports: list[RankerReport] = []
    for ranker in rankers:
        for case in list(immediate[:warmup]) + list(composition[:warmup]):
            ranker.rank(RankingContext(case.left_context, case.readings), case.to_candidates())
        t0 = tuple(evaluate_case(ranker, c) for c in immediate)
        t1 = tuple(evaluate_case(ranker, c) for c in composition)
        reports.append(
            RankerReport(
                ranker=ranker.name,
                immediate=summarize(t0),
                immediate_unambiguous=summarize([o for o in t0 if not o.ambiguous_at_t0]),
                composition=summarize(t1),
                temporal=summarize_temporal({o.case_id: o for o in t0}, t1),
                immediate_outcomes=t0,
                composition_outcomes=t1,
            )
        )
    return tuple(reports)


def measure_decoder(cases: Sequence[RankingCase], generate: Callable[[tuple[str, ...]], Sequence[str]]) -> LatencyStats:
    """重新解碼每個 case 並計時；同時確認 case 檔的候選仍與目前 decoder 一致。"""
    samples: list[float] = []
    for case in cases:
        started = time.perf_counter()
        texts = tuple(generate(case.readings))
        samples.append((time.perf_counter() - started) * 1000.0)
        if texts != case.candidates:
            raise StaleCasesError(f"{case.case_id} 的候選與目前 decoder 不同，請重新執行 build")
    return latency_stats(samples)


def _fmt(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def format_ranking_table(title: str, rows: Sequence[tuple[str, RankingSummary]]) -> str:
    lines = [
        f"### {title}",
        "",
        "| ranker | n | top-1 | MRR | regressions | improvements | fallback | confident | high-conf wrong "
        "| low-conf correct | mean w_eff | disagreement | order instability | forward passes | questions |",
        "|" + "---|" * 15,
    ]
    for name, s in rows:
        lines.append(
            f"| {name} | {s.cases} | {_fmt(s.top1_accuracy)} | {_fmt(s.mrr)} | {s.regressions} | {s.improvements} "
            f"| {s.fallback_count} | {s.confident_cases}/{s.assessed_cases} | {s.high_confidence_wrong} "
            f"| {s.low_confidence_correct} | {_fmt(s.mean_effective_weight)} | {_fmt(s.mean_disagreement)} "
            f"| {_fmt(s.mean_order_instability)} | {s.forward_passes} | {s.questions} |"
        )
    return "\n".join(lines)


def format_temporal_table(reports: Sequence[RankerReport]) -> str:
    lines = [
        "### Temporal：目標段從 t0 到 t1",
        "",
        "| ranker | paired | initial top-1 | final top-1 | final sequence top-1 | wrong→correct | correct→wrong "
        "| unchanged correct | unchanged wrong | changed | correction precision | w→c ambiguous |",
        "|" + "---|" * 12,
    ]
    for r in reports:
        t = r.temporal
        lines.append(
            f"| {r.ranker} | {t.paired_cases} | {_fmt(t.initial_top1_accuracy)} | {_fmt(t.final_top1_accuracy)} "
            f"| {_fmt(t.final_sequence_top1)} | {t.wrong_to_correct} | {t.correct_to_wrong} | {t.unchanged_correct} "
            f"| {t.unchanged_wrong} | {t.changed} | {_fmt(t.correction_precision)} "
            f"| {t.wrong_to_correct_ambiguous}/{t.initial_wrong_ambiguous} |"
        )
    return "\n".join(lines)


def format_latency_table(reports: Sequence[RankerReport], decoder: LatencyStats | None) -> str:
    lines = ["### Latency（CompositionReranking cases，ms）", ""]
    if decoder is not None:
        lines.append(f"decoder（candidate generation）：p50 {_fmt(decoder.p50_ms, 2)} / p95 {_fmt(decoder.p95_ms, 2)}")
        lines.append("")
    lines += [
        "| ranker | Laya p50 | Laya p95 | total rerank p50 | total rerank p95 |",
        "|---|---|---|---|---|",
    ]
    for r in reports:
        m, t = r.composition.model_latency, r.composition.rerank_latency
        lines.append(f"| {r.ranker} | {_fmt(m.p50_ms, 2)} | {_fmt(m.p95_ms, 2)} | {_fmt(t.p50_ms, 2)} | {_fmt(t.p95_ms, 2)} |")
    return "\n".join(lines)


def format_report(reports: Sequence[RankerReport], decoder: LatencyStats | None) -> str:
    return "\n\n".join(
        [
            format_temporal_table(reports),
            format_ranking_table("CompositionReranking：完整序列", [(r.ranker, r.composition) for r in reports]),
            format_ranking_table("ImmediateRanking（t0 任一合理答案排第一即算對）", [(r.ranker, r.immediate) for r in reports]),
            format_ranking_table(
                "ImmediateRanking：只看 unambiguous cases", [(r.ranker, r.immediate_unambiguous) for r in reports]
            ),
            format_latency_table(reports, decoder),
        ]
    )


RANKER_CHOICES = (
    "frequency",
    "corpus-raw",
    "corpus-raw+lexicon",
    "corpus-general",
    "corpus-general+lexicon",
)
_ON_GENERAL: set[str] = set()
DEFAULT_RANKERS = "frequency"


def _build_rankers(args: argparse.Namespace) -> list[CandidateRanker]:
    # 延遲 import：只跑 frequency 時不需要安裝 laya。
    from zaoseq_bopomofo.ranking.frequency import FrequencyRanker

    names = [n.strip() for n in args.rankers.split(",") if n.strip()]
    unknown = sorted(set(names) - set(RANKER_CHOICES))
    if unknown:
        raise SystemExit(f"未知的 ranker：{unknown}；可用：{', '.join(RANKER_CHOICES)}")
    baseline = FrequencyRanker()
    corpus_rankers: dict[str, CandidateRanker] = {}
    if any(n.startswith("corpus-") or n in _ON_GENERAL for n in names):
        from zaoseq_bopomofo.decoding.pipeline import LanguageModelConfig, lexicon_characters, load_language_model
        from zaoseq_bopomofo.lexicon.loader import load_lexicon
        from zaoseq_bopomofo.ranking.corpus import CorpusRanker

        characters = lexicon_characters(load_lexicon())
        for key, config in (("raw", LanguageModelConfig.RAW), ("general", LanguageModelConfig.GENERAL)):
            lm = load_language_model(config, characters)
            corpus_rankers[f"corpus-{key}"] = CorpusRanker(lm, lexical_weight=0.0, name=f"corpus-{key}")
            corpus_rankers[f"corpus-{key}+lexicon"] = CorpusRanker(lm, lexical_weight=1.0, name=f"corpus-{key}+lexicon")
    if all(n == "frequency" or n in corpus_rankers for n in names):
        return [baseline if n == "frequency" else corpus_rankers[n] for n in names]

    raise SystemExit("contextual rankers require the private ranker package")


def _on_general(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
    """公開版本不含私有排序模型。"""
    raise RuntimeError("requires the private ranker package")


def _cmd_build(args: argparse.Namespace) -> int:
    from zaoseq_bopomofo.decoding.generator import CandidateGenerator
    from zaoseq_bopomofo.lexicon.loader import load_lexicon

    outcome = build_cases(load_scenarios(args.seeds), CandidateGenerator(load_lexicon().lexicon))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    note = f"generated from {args.seeds.as_posix()} with the builtin lexicon + CNS11643; rebuild instead of editing."
    dump_cases(outcome.immediate, args.output_dir / IMMEDIATE_FILE, "造序注音 ImmediateRanking cases\n" + note)
    dump_cases(outcome.composition, args.output_dir / COMPOSITION_FILE, "造序注音 CompositionReranking cases\n" + note)
    print(f"immediate: {len(outcome.immediate)} cases, composition: {len(outcome.composition)} cases")
    for item in outcome.excluded:
        print(f"  excluded {item}", file=sys.stderr)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    immediate = load_cases(args.cases_dir / IMMEDIATE_FILE)
    composition = load_cases(args.cases_dir / COMPOSITION_FILE)

    decoder: LatencyStats | None = None
    if not args.skip_decoder:
        from zaoseq_bopomofo.decoding.generator import CandidateGenerator
        from zaoseq_bopomofo.lexicon.loader import load_lexicon

        generator = CandidateGenerator(load_lexicon().lexicon)
        decoder = measure_decoder(composition, lambda r: [c.text for c in generator.candidates_for(r)])

    reports = run_benchmark(_build_rankers(args), immediate, composition, warmup=args.warmup)
    ambiguous = sum(c.ambiguous_at_t0 for c in immediate)
    print(f"immediate: {len(immediate)} cases ({ambiguous} ambiguous at t0), composition: {len(composition)} cases\n")
    print(format_report(reports, decoder))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cases_dir": args.cases_dir.as_posix(),
            "config": {
                "laya_checkpoint": "convaiinnovations/laya (subfolder=multilingual, revision pinned in the private ranker package)",
                "rankers": args.rankers,
                "fixed_hybrid_weight": args.hybrid_weight,
                "confidence_config": asdict(ConfidenceConfig()),
                "timeout_s": args.timeout,
                "top_k": args.top_k,
                "warmup": args.warmup,
            },
            "decoder_latency": asdict(decoder) if decoder else None,
            "reports": [_report_json(r) for r in reports],
        }
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nreport -> {args.output}")
    return 0


def _report_json(report: RankerReport) -> dict[str, object]:
    def outcomes(items: Sequence[CaseOutcome]) -> list[dict[str, object]]:
        return [
            {**asdict(o), "status": o.status.value, "fallback_reason": o.fallback_reason.value if o.fallback_reason else None}
            for o in items
        ]

    return {
        "ranker": report.ranker,
        "temporal": asdict(report.temporal),
        "composition": asdict(report.composition),
        "immediate": asdict(report.immediate),
        "immediate_unambiguous": asdict(report.immediate_unambiguous),
        "immediate_outcomes": outcomes(report.immediate_outcomes),
        "composition_outcomes": outcomes(report.composition_outcomes),
    }


def _cmd_order_bias(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
    """公開版本不含私有排序模型。"""
    raise RuntimeError("requires the private ranker package")


def _cmd_coverage(args: argparse.Namespace) -> int:
    from zaoseq_bopomofo.decoding.generator import CandidateGenerator
    from zaoseq_bopomofo.evaluation.coverage import measure_coverage
    from zaoseq_bopomofo.lexicon.loader import load_lexicon

    lexicon = load_lexicon().lexicon
    summary = measure_coverage(load_scenarios(args.seeds), lexicon, CandidateGenerator(lexicon))
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.evaluation.benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="由 seeds 產生 immediate / composition cases")
    build.add_argument("seeds", type=Path)
    build.add_argument("output_dir", type=Path)

    run = sub.add_parser("run", help="執行 temporal benchmark")
    run.add_argument("cases_dir", type=Path)
    run.add_argument("--rankers", default=DEFAULT_RANKERS, help=f"逗號分隔：{', '.join(RANKER_CHOICES)}")
    run.add_argument("--hybrid-weight", type=float, default=0.5, help="固定權重 hybrid（對照組）的權重")
    run.add_argument("--device", default=None)
    run.add_argument("--timeout", type=float, default=2.0)
    run.add_argument("--top-k", type=int, default=4)
    run.add_argument("--warmup", type=int, default=3)
    run.add_argument("--skip-decoder", action="store_true", help="不量測 decoder（沒有詞庫檔時使用）")
    run.add_argument("--output", type=Path, default=None)

    bias = sub.add_parser("order-bias", help="量測 Laya 對選項順序的敏感度（單一順序、全排列）")
    bias.add_argument("cases_dir", type=Path)
    bias.add_argument("--top-k", type=int, default=4)
    bias.add_argument("--device", default=None)
    bias.add_argument("--output", type=Path, default=None)

    coverage = sub.add_parser("coverage", help="詞庫與 decoder coverage（與 ranking benchmark 分開）")
    coverage.add_argument("seeds", type=Path)

    args = parser.parse_args(argv)
    commands = {"build": _cmd_build, "run": _cmd_run, "order-bias": _cmd_order_bias, "coverage": _cmd_coverage}
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
