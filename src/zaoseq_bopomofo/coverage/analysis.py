from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from zaoseq_bopomofo.coverage.dataset import V1_0, CoverageDataset, CoverageItem
from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig, reachable, tone_variants
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

K_VALUES = (1, 3, 5, 10)
WINDOW = 4
CONFIGS = (
    GenerationConfig("v0"),
    GenerationConfig("nbest50", nbest=50),
    GenerationConfig("nbest100", nbest=100),
    GenerationConfig("beam24", beam=24),
    GenerationConfig("beam96", beam=96),
    GenerationConfig("beam96_nbest100", beam=96, nbest=100),
    GenerationConfig("beam192_nbest100", beam=192, nbest=100),
    GenerationConfig("span8", max_entries_per_span=8),
    GenerationConfig("span16", max_entries_per_span=16),
    GenerationConfig("span32", max_entries_per_span=32),
    GenerationConfig("lexslots16", lexical_slots=16),
    GenerationConfig("lexslots32", lexical_slots=32),
    GenerationConfig("tonevar", tone_variant_lookup=True),
    GenerationConfig("prune_lexical", prune_by_lexical=True),
)


@dataclass
class Case:
    item_id: str
    left_context: str
    readings: tuple[str, ...]
    acceptable: tuple[str, ...]
    category: str = ""
    item: CoverageItem | None = None


@dataclass
class CaseResult:
    item_id: str
    rank: int | None  # 在輸出候選中的位置（family 等價）；None = 不在輸出
    final_rank: int | None  # 在所有完整假設中的位置；None = 完全沒有產生
    window_hit: bool
    reachable: bool
    first_lost: int | None
    exact_surface_in_output: bool
    candidates: int
    families: int
    top1: str
    latency_ms: float


@dataclass
class SetMetrics:
    items: int
    recall: dict[str, float]
    recall_unlimited: float
    reachable: float
    window_recall_top4_families: float
    generated_but_outside_top5: int
    never_generated: int
    unreachable: int
    beam_pruned: int
    mean_candidates: float
    mean_families: float
    latency_p50_ms: float
    latency_p95_ms: float
    oov_rate: float | None = None
    reading_coverage: float | None = None
    word_coverage: float | None = None


@dataclass
class Context:
    lexicon: object
    lm: object
    scorer: object
    variants: object
    cns: dict[str, set[str]]
    plane: dict[tuple[str, str], int] = field(default_factory=dict)

    def key(self, text: str) -> str:
        return self.variants.family_key(text)  # type: ignore[attr-defined]


def _percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    index = (len(ordered) - 1) * q
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def run_config(ctx: Context, config: GenerationConfig, cases: Sequence[Case], lexicon: object | None = None) -> list[CaseResult]:
    from zaoseq_bopomofo.decoding.family import group_families

    lattice = CoverageLattice(lexicon or ctx.lexicon, ctx.lm, ctx.scorer, config)  # type: ignore[arg-type]
    for case in cases[:10]:  # 暖機
        lattice.generate(case.readings, case.left_context)
    results: list[CaseResult] = []
    for case in cases:
        gold_keys = {ctx.key(a) for a in case.acceptable}
        prefixes = [{k[:p] for k in gold_keys} for p in range(len(case.readings) + 1)]

        def is_gold(text: str, keys: set[str] = gold_keys) -> bool:
            return ctx.key(text) in keys

        def prefix(position: int, texts, table=prefixes) -> bool:  # type: ignore[no-untyped-def]
            wanted = table[position]
            return any(ctx.key(t) in wanted for t in texts)

        started = time.perf_counter()
        plain = lattice.generate(case.readings, case.left_context)
        latency = (time.perf_counter() - started) * 1000.0
        traced = lattice.generate(case.readings, case.left_context, gold_keys=is_gold, gold_prefix=prefix)
        assert traced.trace is not None
        texts = [c.text for c in plain.candidates]
        rank = next((i for i, t in enumerate(texts) if is_gold(t)), None)
        families = group_families(plain.candidates, ctx.variants)  # type: ignore[arg-type]
        window = any(is_gold(f.representative.text) or any(is_gold(m.text) for m in f.members) for f in families[:WINDOW])

        def accepts(i: int, j: int, text: str, keys: set[str] = gold_keys) -> bool:
            return any(ctx.key(text) == k[i:j] for k in keys)

        results.append(
            CaseResult(
                item_id=case.item_id,
                rank=rank,
                final_rank=traced.trace.final_rank,
                window_hit=window,
                reachable=reachable(lexicon or ctx.lexicon, case.readings, accepts, config.tone_variant_lookup),  # type: ignore[arg-type]
                first_lost=traced.trace.first_lost,
                exact_surface_in_output=any(t in case.acceptable for t in texts),
                candidates=len(texts),
                families=len(families),
                top1=texts[0] if texts else "",
                latency_ms=latency,
            )
        )
    return results


def summarize(results: Sequence[CaseResult], cases: Sequence[Case], ctx: Context) -> SetMetrics:
    n = len(results)
    recall = {f"@{k}": sum(r.rank is not None and r.rank < k for r in results) / n for k in K_VALUES}
    metrics = SetMetrics(
        items=n,
        recall=recall,
        recall_unlimited=sum(r.final_rank is not None for r in results) / n,
        reachable=sum(r.reachable for r in results) / n,
        window_recall_top4_families=sum(r.window_hit for r in results) / n,
        generated_but_outside_top5=sum(r.final_rank is not None and (r.rank is None or r.rank >= 5) for r in results),
        never_generated=sum(r.final_rank is None for r in results),
        unreachable=sum(not r.reachable for r in results),
        beam_pruned=sum(r.reachable and r.final_rank is None for r in results),
        mean_candidates=statistics.fmean(r.candidates for r in results),
        mean_families=statistics.fmean(r.families for r in results),
        latency_p50_ms=_percentile([r.latency_ms for r in results], 0.5),
        latency_p95_ms=_percentile([r.latency_ms for r in results], 0.95),
    )
    chars = covered = syllables_ok = 0
    words = words_ok = 0
    lexicon = ctx.lexicon
    for case in cases:
        text = case.acceptable[0]
        for char, reading in zip(text, case.readings):
            chars += 1
            entries = lexicon.lookup((reading,))  # type: ignore[attr-defined]
            syllables_ok += bool(entries)
            covered += any(e.text == char for e in entries)
        if case.item is not None:
            for start, end, word in case.item.word_spans():
                if end - start < 2:
                    continue
                words += 1
                entries = lexicon.lookup(case.readings[start:end])  # type: ignore[attr-defined]
                words_ok += any(e.text == word.text for e in entries)
    metrics.oov_rate = 1 - covered / chars if chars else None
    metrics.reading_coverage = syllables_ok / chars if chars else None
    metrics.word_coverage = words_ok / words if words else None
    return metrics


TAXONOMY = (
    "lexical_missing",
    "pronunciation_variant_missing",
    "segmentation_missing",
    "beam_pruned",
    "score_pruned",
    "proper_noun",
    "colloquial_word",
    "orthographic_variant",
    "character_reading_missing",
    "candidate_family_issue",
    "other",
)


@dataclass
class Missing:
    item_id: str
    text: str
    top1: str
    stage: str
    category: str
    error_position: int | None
    detail: str


def _stage(result: CaseResult) -> str:
    if not result.reachable:
        return "unreachable"
    if result.final_rank is None:
        return "beam_pruned"
    if result.rank is None:
        return "outside_output"
    if result.rank >= 5:
        return "generated_ranked_low"
    return "top5"


def classify(result: CaseResult, case: Case, ctx: Context) -> Missing:
    """先看 gold 在管線哪一步消失（stage），再看錯誤位置涵蓋的詞（cause）。一個 case 只有一個主要類別。"""
    item = case.item
    gold = case.acceptable[0]
    stage = _stage(result)
    top = result.top1
    diff = next((i for i, (a, b) in enumerate(zip(ctx.key(gold), ctx.key(top))) if a != b), None) if top else 0
    if stage == "top5" and not result.window_hit:
        return Missing(case.item_id, gold, top, stage, "candidate_family_issue", diff, "gold in top-5 surfaces but not in top-4 families")
    if stage == "unreachable":
        for position, (char, reading) in enumerate(zip(gold, case.readings)):
            entries = ctx.lexicon.lookup((reading,))  # type: ignore[attr-defined]
            if any(e.text == char for e in entries):
                continue
            variant_hit = any(
                any(e.text == char for e in ctx.lexicon.lookup((v,)))  # type: ignore[attr-defined]
                for v in tone_variants(reading)
            )
            if variant_hit:
                return Missing(case.item_id, gold, top, stage, "pronunciation_variant_missing", position, f"{char} {reading}: only a tone variant is in the lexicon")
            plane = ctx.plane.get((char, reading))
            return Missing(case.item_id, gold, top, stage, "character_reading_missing", position, f"{char} {reading}: CNS plane {plane}, not in the default lexicon")
        return Missing(case.item_id, gold, top, stage, "other", None, "unreachable with every character present")
    if not result.exact_surface_in_output and result.rank is not None:
        return Missing(case.item_id, gold, top, stage, "orthographic_variant", diff, "only a variant surface was generated")
    word = None
    if item is not None and diff is not None:
        word = next((w for s, e, w in item.word_spans() if s <= diff < e), None)
    if word is not None:
        start, end = next((s, e) for s, e, w in item.word_spans() if w is word)  # type: ignore[union-attr]
        in_lexicon = any(e.text == word.text for e in ctx.lexicon.lookup(case.readings[start:end]))  # type: ignore[attr-defined]
        if word.proper_noun:
            return Missing(case.item_id, gold, top, stage, "proper_noun", diff, f"{word.text} (in lexicon: {in_lexicon})")
        if word.colloquial:
            return Missing(case.item_id, gold, top, stage, "colloquial_word", diff, f"{word.text} (in lexicon: {in_lexicon})")
        if len(word.text) >= 2 and not in_lexicon:
            return Missing(case.item_id, gold, top, stage, "lexical_missing", diff, f"{word.text} not in lexicon")
        if len(word.text) >= 2:
            return Missing(case.item_id, gold, top, stage, "segmentation_missing", diff, f"{word.text} in lexicon but lost")
    category = "beam_pruned" if stage == "beam_pruned" else "score_pruned"
    detail = f"single-character choice at position {diff}" + (f" ({word.text})" if word else "")
    return Missing(case.item_id, gold, top, stage, category, diff, detail)


def taxonomy(results: Sequence[CaseResult], cases: Sequence[Case], ctx: Context, top: int = 5) -> dict[str, object]:
    by_id = {c.item_id: c for c in cases}
    missing = [classify(r, by_id[r.item_id], ctx) for r in results if r.rank is None or r.rank >= top or not r.window_hit]
    counts = Counter(m.category for m in missing)
    stages = Counter(m.stage for m in missing)
    cross = Counter((m.category, m.stage) for m in missing)
    examples: dict[str, list[dict[str, object]]] = {}
    for m in missing:
        examples.setdefault(m.category, [])
        if len(examples[m.category]) < 4:
            examples[m.category].append({"id": m.item_id, "gold": m.text, "v0_top1": m.top1, "stage": m.stage, "detail": m.detail})
    total = len(missing)
    return {
        "cases_considered": len(results),
        "missing_or_outside_top5_or_window": total,
        "by_category": {c: {"count": counts.get(c, 0), "share": round(counts.get(c, 0) / total, 3) if total else 0.0} for c in TAXONOMY},
        "by_stage": dict(stages.most_common()),
        "category_x_stage": {f"{c}|{s}": v for (c, s), v in sorted(cross.items())},
        "examples": examples,
    }



def timing_breakdown(ctx: Context, config: GenerationConfig, cases: Sequence[Case]) -> dict[str, float]:
    from zaoseq_bopomofo.decoding.family import group_families

    lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, config)  # type: ignore[arg-type]
    totals = Counter()
    for case in cases:
        started = time.perf_counter()
        out = lattice.generate(case.readings, case.left_context, timed=True)
        total = time.perf_counter() - started
        t = time.perf_counter()
        group_families(out.candidates, ctx.variants)  # type: ignore[arg-type]
        family = time.perf_counter() - t
        totals["total"] += total
        totals["lexicon_lookup"] += out.timing.lookup_s
        totals["lm_scoring"] += out.timing.lm_s
        totals["beam_sort_prune"] += out.timing.prune_s
        totals["kbest_finalize"] += out.timing.finalize_s
        totals["candidate_family"] += family
    grand = totals["total"]
    parts = {k: round(v / grand, 3) for k, v in totals.items() if k != "total"}
    parts["other_lattice_overhead"] = round(1 - sum(v for k, v in parts.items() if k != "candidate_family"), 3)
    parts["mean_total_ms_instrumented"] = round(grand / len(cases) * 1000, 2)
    return parts



def build_context() -> Context:
    from zaoseq_bopomofo.decoding.family import VariantTable
    from zaoseq_bopomofo.decoding.pipeline import V0_SETTINGS, LanguageModelConfig, lexicon_characters, load_language_model
    from zaoseq_bopomofo.lexicon.builder import read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_CHAR_READINGS, load_lexicon

    loaded = load_lexicon()
    lm = load_language_model(LanguageModelConfig.GENERAL, lexicon_characters(loaded))
    cns: dict[str, set[str]] = {}
    plane: dict[tuple[str, str], int] = {}
    for row in read_char_readings(DEFAULT_CHAR_READINGS):
        cns.setdefault(row.char, set()).add(row.reading)
        key = (row.char, row.reading)
        plane[key] = min(plane.get(key, 99), row.plane)
    return Context(loaded.lexicon, lm, V0_SETTINGS.scorer, VariantTable.load(), cns, plane)


def coverage_cases(dataset: CoverageDataset = V1_0) -> list[Case]:
    return [Case(i.item_id, i.left_context, i.readings, i.acceptable, i.category, i) for i in dataset.load()]


def gov_dev_cases(per_domain: int) -> list[Case]:
    from zaoseq_bopomofo.corpus.annotate import ReadingAnnotator
    from zaoseq_bopomofo.evaluation.domains import domain_silver_items
    from zaoseq_bopomofo.lexicon.builder import read_builtin, read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

    annotator = ReadingAnnotator(read_char_readings(DEFAULT_CHAR_READINGS), read_builtin(DEFAULT_BUILTIN))
    silver = domain_silver_items(PROJECT_ROOT / "data" / "corpus", annotator, per_domain=per_domain)  # corpus split "test" = GOV-DEV
    return [
        Case(i.item_id, i.left_context, i.readings, (i.gold,), domain)
        for domain in ("legal", "government_faq", "public_service", "press_release")
        for i in silver.get(domain, [])
    ]


def check_v0_equivalence(ctx: Context, cases: Sequence[Case]) -> dict[str, object]:
    """V0 設定必須與 frozen V0 decoder 逐項相同（文字、順序與分數）。"""
    from zaoseq_bopomofo.decoding.pipeline import build_v0_decoder
    from zaoseq_bopomofo.lexicon.loader import load_lexicon

    frozen = build_v0_decoder(load_lexicon())
    lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
    mismatches = []
    for case in cases:
        a = [(c.text, round(c.baseline_score, 9)) for c in frozen.candidates_for(case.readings, case.left_context)]
        b = [(c.text, round(c.baseline_score, 9)) for c in lattice.generate(case.readings, case.left_context).candidates]
        if a != b:
            mismatches.append(case.item_id)
    return {"cases": len(cases), "mismatches": mismatches}


def oracle_lexicon(ctx: Context, cases: Sequence[Case]):  # type: ignore[no-untyped-def]
    """診斷用上限：把 Coverage-DEV 的多字 gold 詞加進詞庫（等級 3）。只用來回答「缺詞影響多大」，不採用。"""
    from zaoseq_bopomofo.lexicon.builder import BuiltinRow, build_lexicon, read_builtin, read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

    builtin = list(read_builtin(DEFAULT_BUILTIN))
    known = {(r.text, r.readings) for r in builtin}
    added = 0
    for case in cases:
        if case.item is None:
            continue
        for start, end, word in case.item.word_spans():
            key = (word.text, tuple(case.readings[start:end]))
            if end - start >= 2 and key not in known and not any(e.text == word.text for e in ctx.lexicon.lookup(key[1])):  # type: ignore[attr-defined]
                known.add(key)
                builtin.append(BuiltinRow(word.text, 3, key[1], -1))
                added += 1
    report = build_lexicon(read_char_readings(DEFAULT_CHAR_READINGS), builtin)
    return report.lexicon, added


def teacher_observation(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
    """公開版本不含私有排序模型。"""
    raise RuntimeError("requires the private ranker package")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.coverage.analysis")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gov-per-domain", type=int, default=100)
    parser.add_argument("--configs", default="")
    parser.add_argument("--teacher", default="", help="逗號分隔的 config 名稱，用 frozen fine-tuned Laya 觀察")
    args = parser.parse_args(argv)

    ctx = build_context()
    sets = {"coverage_dev": coverage_cases(), "gov_dev": gov_dev_cases(args.gov_per_domain)}
    print(f"[sets] { {k: len(v) for k, v in sets.items()} }", file=sys.stderr)
    report: dict[str, object] = {"sets": {k: len(v) for k, v in sets.items()}}
    report["v0_equivalence"] = {name: check_v0_equivalence(ctx, cases) for name, cases in sets.items()}
    print(f"[equivalence] {report['v0_equivalence']}", file=sys.stderr)

    extra = {c.name: c for c in CONFIGS}
    for spec in filter(None, args.configs.split(";")):
        name, _, params = spec.partition(":")
        kwargs = {k: (v == "true" if v in ("true", "false") else int(v)) for k, v in (p.split("=") for p in params.split(",") if p)}
        extra[name] = GenerationConfig(name, **kwargs)  # type: ignore[arg-type]

    results: dict[str, dict[str, list[CaseResult]]] = {}
    metrics: dict[str, dict[str, dict[str, object]]] = {}
    for config in extra.values():
        for set_name, cases in sets.items():
            res = run_config(ctx, config, cases)
            results.setdefault(config.name, {})[set_name] = res
            metrics.setdefault(config.name, {})[set_name] = asdict(summarize(res, cases, ctx))
        print(f"[done] {config.name}", file=sys.stderr)
    report["configs"] = {c.name: asdict(c) for c in extra.values()}
    report["metrics"] = metrics
    report["taxonomy_v0"] = {name: taxonomy(results["v0"][name], cases, ctx) for name, cases in sets.items()}

    oracle, added = oracle_lexicon(ctx, sets["coverage_dev"])
    oracle_results = run_config(ctx, GenerationConfig("v0_oracle_lexicon"), sets["coverage_dev"], lexicon=oracle)
    report["oracle_lexicon_diagnostic"] = {
        "note": "upper bound only: Coverage-DEV gold words added to the lexicon; not an adoptable configuration",
        "words_added": added,
        "coverage_dev": asdict(summarize(oracle_results, sets["coverage_dev"], ctx)),
    }
    report["timing_breakdown_v0"] = timing_breakdown(ctx, GenerationConfig(), sets["coverage_dev"])
    report["per_case_v0"] = {name: [asdict(r) for r in res] for name, res in results["v0"].items()}
    if args.teacher:
        chosen = [extra[n] for n in args.teacher.split(",")]
        report["teacher_observation"] = teacher_observation(ctx, sets["coverage_dev"], chosen)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("sets", "v0_equivalence")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
