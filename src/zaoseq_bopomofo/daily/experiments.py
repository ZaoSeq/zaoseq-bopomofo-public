from __future__ import annotations

import json
import os
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from zaoseq_bopomofo.coverage.analysis import Case, CaseResult, Context, run_config, summarize
from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

RESULTS = PROJECT_ROOT / "benchmarks" / "results"
DAILY_WEIGHTS = (0.25, 0.5, 0.75)
GOV_TOLERANCE = 0.02
WINDOW_SIZES = (4, 5, 6, 8)
DEV_ONLY_MIXES = {
    "G": "oasst1_zh_prompter",
    "H": "daily_all",
}
SELECTION_RULE = (
    "DEV only (Coverage-DEV v1.1 + GOV-DEV). Pick the candidate with the highest Coverage-DEV v1.1 R@5 among those whose "
    f"GOV-DEV R@1 is at least A's minus {GOV_TOLERANCE}; ties go to higher top-4-family window recall, then to the smaller "
    "daily weight / earlier variant. If no candidate satisfies the GOV constraint, the one with the smallest GOV drop is "
    "reported as selected and flagged."
)


@dataclass(frozen=True)
class Variant:
    name: str
    daily_lm: str | None
    daily_weight: float
    lexicon: str = "builtin"


def percent(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[int(round(q * (len(ordered) - 1)))] if ordered else float("nan")


class SetEvaluator:
    """一個設定在 Coverage-DEV v1.1 與 GOV-DEV 上的全部指標，並保留逐句結果供配對分析。"""

    def __init__(self, sets: dict[str, list[Case]]) -> None:
        self.sets = sets

    def evaluate(self, ctx: Context) -> dict[str, dict[str, object]]:
        out: dict[str, dict[str, object]] = {}
        for set_name, cases in self.sets.items():
            results = run_config(ctx, GenerationConfig(), cases)
            metrics = asdict(summarize(results, cases, ctx))
            metrics.update(self._extra(results, cases, ctx))
            out[set_name] = {
                "metrics": metrics,
                "cases": [{"id": r.item_id, "rank": r.rank, "window": r.window_hit, "top1": r.top1} for r in results],
            }
        return out

    @staticmethod
    def _extra(results: Sequence[CaseResult], cases: Sequence[Case], ctx: Context) -> dict[str, float]:
        by_id = {c.item_id: c for c in cases}
        chars = matched = 0
        reciprocal = 0.0
        for result in results:
            case = by_id[result.item_id]
            reciprocal += 1.0 / (result.rank + 1) if result.rank is not None else 0.0
            top = ctx.key(result.top1)
            best = max(sum(a == b for a, b in zip(top, ctx.key(gold))) for gold in case.acceptable)
            matched += best
            chars += len(case.acceptable[0])
        n = len(results)
        return {"top1": sum(r.rank == 0 for r in results) / n, "character_accuracy": matched / chars, "mrr": reciprocal / n}


class SelectionRule:
    def select(self, candidates: dict[str, dict[str, dict[str, object]]], baseline: dict[str, dict[str, object]]) -> dict[str, object]:
        floor = baseline["gov_dev"]["metrics"]["recall"]["@1"] - GOV_TOLERANCE  # type: ignore[index]

        def m(name: str, set_name: str) -> dict[str, object]:
            return candidates[name][set_name]["metrics"]  # type: ignore[return-value]

        order = list(candidates)
        passing = [n for n in order if m(n, "gov_dev")["recall"]["@1"] >= floor]  # type: ignore[index]
        pool = passing or sorted(order, key=lambda n: -m(n, "gov_dev")["recall"]["@1"])[:1]  # type: ignore[index]
        chosen = max(
            pool,
            key=lambda n: (m(n, "coverage_dev")["recall"]["@5"], m(n, "coverage_dev")["window_recall_top4_families"], -order.index(n)),  # type: ignore[index]
        )
        return {"selected": chosen, "gov_r1_floor": round(floor, 4), "passing": passing, "constraint_satisfied": bool(passing)}


class TeacherObserver:
    """公開版本不含私有排序模型。"""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("requires the private ranker package")


def paired(before: Sequence[bool], after: Sequence[bool]) -> dict[str, float]:
    from zaoseq_bopomofo.coverage.teacher import mcnemar

    fixed = sum((not a) and b for a, b in zip(before, after))
    broken = sum(a and (not b) for a, b in zip(before, after))
    return {"wrong_to_correct": fixed, "correct_to_wrong": broken, "mcnemar_p": round(mcnemar(fixed, broken), 4)}


class HomophoneAnalyzer:
    def __init__(self, base_lexicon: object) -> None:
        self._base = base_lexicon

    def competitors(self, entries: Sequence[object]) -> dict[str, object]:
        rows = []
        for entry in entries:
            if not entry.eligible:  # type: ignore[attr-defined]
                continue
            for readings in entry.readings:  # type: ignore[attr-defined]
                rivals = [e for e in self._base.lookup(readings) if len(e.text) == len(entry.text) and e.text != entry.text]  # type: ignore[attr-defined]
                if rivals:
                    best = max(rivals, key=lambda e: e.frequency)
                    weight = entry.weight / len(entry.readings)  # type: ignore[attr-defined]
                    rows.append((entry.text, " ".join(readings), weight, best.text, best.frequency, [e.text for e in rivals][:5]))  # type: ignore[attr-defined]
        rows.sort(key=lambda r: (-r[2], r[0]))
        return {
            "derived_readings_with_competitor": len(rows),
            "derived_outweighs_best_competitor": sum(r[2] > r[4] for r in rows),
            "examples": [
                {"derived": t, "readings": rd, "derived_weight": round(w, 2), "best_competitor": b, "competitor_weight": bw, "competitors": rv}
                for t, rd, w, b, bw, rv in rows[:20]
            ],
        }

    @staticmethod
    def impact(
        ctx: Context, cases: Sequence[Case], before: Sequence[dict], after: Sequence[dict], lattice: CoverageLattice, derived: set[str]  # type: ignore[type-arg]
    ) -> dict[str, object]:
        examples = []
        counts = {"wrong_to_correct": 0, "correct_to_wrong": 0, "wrong_to_correct_with_derived_word": 0, "correct_to_wrong_with_derived_word": 0}
        for case, b, a in zip(cases, before, after):
            was, now = b["rank"] == 0, a["rank"] == 0
            if was == now:
                continue
            candidates = lattice.generate(case.readings, case.left_context).candidates
            words = [s.text for s in candidates[0].segments if s.text in derived] if candidates else []
            kind = "wrong_to_correct" if now else "correct_to_wrong"
            counts[kind] += 1
            counts[f"{kind}_with_derived_word"] += bool(words)
            if kind == "correct_to_wrong" and len(examples) < 15:
                examples.append({"id": case.item_id, "gold": case.acceptable[0], "now_top1": a["top1"], "derived_words_in_top1": words})
        return {**counts, "correct_to_wrong_examples": examples}


class ResourceProbe:
    def __init__(self) -> None:
        import psutil

        self._process = psutil.Process(os.getpid())

    def rss_mb(self) -> float:
        return round(self._process.memory_info().rss / 2**20, 1)

    @staticmethod
    def artifact_mb(daily_lm: str | None) -> dict[str, float]:
        from zaoseq_bopomofo.daily.corpus import LM_DIR

        gov = sum(p.stat().st_size for p in (PROJECT_ROOT / "data" / "corpus" / "lm" / "domain").glob("*/*.gz"))
        daily = sum(p.stat().st_size for p in (LM_DIR / daily_lm).glob("*.gz")) if daily_lm else 0
        return {"gov_lm_mb": round(gov / 2**20, 2), "daily_lm_mb": round(daily / 2**20, 2), "total_lm_mb": round((gov + daily) / 2**20, 2)}

    @staticmethod
    def extend_cost_us(lm: object, cases: Sequence[Case]) -> float:
        from zaoseq_bopomofo.corpus.statistics import initial_history

        texts = [c.acceptable[0] for c in cases]
        started = time.perf_counter()
        calls = 0
        for _ in range(3):
            for case, text in zip(cases, texts):
                history = initial_history(case.left_context)
                for char in text:
                    _, history = lm.extend(history, char)  # type: ignore[attr-defined]
                    calls += 1
        return round((time.perf_counter() - started) / calls * 1e6, 3)


class DailyExperiment:
    """A–H、衍生詞表變體、teacher 觀察、K 視窗診斷與資源量測。所有選擇只看 DEV。"""

    def __init__(self, log: Callable[[str], None]) -> None:
        from zaoseq_bopomofo.coverage.analysis import build_context, coverage_cases, gov_dev_cases
        from zaoseq_bopomofo.coverage.dataset import V1_1
        from zaoseq_bopomofo.daily.mixture import LanguageModelFactory
        from zaoseq_bopomofo.decoding.pipeline import lexicon_characters
        from zaoseq_bopomofo.lexicon.loader import load_lexicon

        self.log = log
        self.probe = ResourceProbe()
        rss = self.probe.rss_mb()
        started = time.perf_counter()
        self.base = build_context()
        self.factory = LanguageModelFactory(lexicon_characters(load_lexicon()))
        self.load = {"gov_context_s": round(time.perf_counter() - started, 2), "rss_after_gov_mb": self.probe.rss_mb(), "rss_before_mb": rss}
        self.evaluator = SetEvaluator({"coverage_dev": coverage_cases(V1_1), "gov_dev": gov_dev_cases(100)})
        self.results: dict[str, dict[str, object]] = {}
        self.variants: dict[str, Variant] = {}
        self.lexicons: dict[str, object] = {"builtin": self.base.lexicon}

    def context(self, variant: Variant) -> Context:
        lm = self.factory.mixture(variant.daily_lm, variant.daily_weight)
        return replace(self.base, lm=lm, lexicon=self.lexicons[variant.lexicon])

    def run(self, variant: Variant) -> dict[str, object]:
        started = time.perf_counter()
        rss = self.probe.rss_mb()
        ctx = self.context(variant)
        load_s = time.perf_counter() - started
        report = self.evaluator.evaluate(ctx)
        report["variant"] = asdict(variant)
        report["resources"] = {
            **self.probe.artifact_mb(variant.daily_lm),
            "lexicon_entries": len(ctx.lexicon),  # type: ignore[arg-type]
            "lm_load_s": round(load_s, 3),
            "rss_mb": self.probe.rss_mb(),
            "rss_delta_mb": round(self.probe.rss_mb() - rss, 1),
            "extend_us": ResourceProbe.extend_cost_us(ctx.lm, self.evaluator.sets["coverage_dev"]),
        }
        self.results[variant.name] = report
        self.variants[variant.name] = variant
        cov = report["coverage_dev"]["metrics"]  # type: ignore[index]
        gov = report["gov_dev"]["metrics"]  # type: ignore[index]
        self.log(f"[done] {variant.name}: cov R@1 {cov['recall']['@1']:.3f} R@5 {cov['recall']['@5']:.3f} | gov R@1 {gov['recall']['@1']:.3f}")
        return report

    def perplexity(self, names: Sequence[str]) -> dict[str, dict[str, float]]:
        """bits / char：日常 DEV split 與 GOV-DEV 語料 split（前 2000 句，依檔案順序）。"""
        from zaoseq_bopomofo.corpus.statistics import tokenize
        from zaoseq_bopomofo.daily.corpus import load_sentences
        from zaoseq_bopomofo.evaluation.testsets import GOV_DEV_SPLIT

        daily = [s.text for s in load_sentences() if s.split == "dev"]
        gov: list[str] = []
        for path in sorted((PROJECT_ROOT / "data" / "corpus").glob("*/sentences.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row["split"] == GOV_DEV_SPLIT and row.get("domain") in ("government_faq", "public_service", "press_release", "legal"):
                    gov.append(row["text"])
        gov = gov[:2000]
        out: dict[str, dict[str, float]] = {}
        for name in names:
            lm = self.context(self.variants[name]).lm
            row = {}
            for label, texts in (("daily_dev", daily), ("gov_dev", gov)):
                tokens = sum(len(tokenize(t)) for t in texts)
                row[f"{label}_bits_per_char"] = round(-sum(lm.score(t) for t in texts) / tokens * 3.321928, 4)  # type: ignore[attr-defined]
            out[name] = row
        return out


def main(output: str | None = None) -> int:
    from zaoseq_bopomofo.corpus.domains import GENERAL_WEIGHTS
    from zaoseq_bopomofo.daily.corpus import PRODUCTION_DAILY, production_source_ids
    from zaoseq_bopomofo.daily.lexicon import (
        LEXICON_DIR,
        DerivedLexiconBuilder,
        ExtractionPolicy,
        FrequencyAwareExtractor,
        InterpolatedEstimator,
        OccurrenceScanner,
        PooledEstimator,
        ReadingResolver,
        build_tables,
        corpus_sentences,
        write_entries,
    )
    from zaoseq_bopomofo.lexicon.builder import read_builtin
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN

    def log(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    exp = DailyExperiment(log)
    report: dict[str, object] = {"selection_rule": SELECTION_RULE, "load": exp.load}
    exp.run(Variant("A_gov", None, 0.0))
    exp.run(Variant("B_daily", PRODUCTION_DAILY, 1.0))
    c_names = [exp.run(Variant(f"C_daily{w:g}", PRODUCTION_DAILY, w))["variant"]["name"] for w in DAILY_WEIGHTS]  # type: ignore[index]
    c_choice = SelectionRule().select({n: exp.results[n] for n in c_names}, exp.results["A_gov"])  # type: ignore[misc]
    report["c_selection"] = c_choice
    weight = exp.variants[c_choice["selected"]].daily_weight  # type: ignore[index]
    log(f"[select] C -> {c_choice}")
    report["identical_configs"] = {
        "D": f"{c_choice['selected']} (V0 already uses the builtin lexicon)",
        "F": f"{c_choice['selected']} (Tatoeba is the only production-scope daily source)",
    }
    for letter, name in DEV_ONLY_MIXES.items():
        exp.run(Variant(f"{letter}_{name}", name, weight))

    gov_weights = {d.value: w for d, w in GENERAL_WEIGHTS.weights.items()}
    started = time.perf_counter()
    sentences = corpus_sentences(gov_weights, production_source_ids())
    tables = build_tables(sentences, gov_weights)
    extractor = FrequencyAwareExtractor(tables, ReadingResolver(), {r.text for r in read_builtin(DEFAULT_BUILTIN)})
    policies = (
        ExtractionPolicy("raw_freq", PooledEstimator(), min_documents=2, min_pmi=0.0),
        ExtractionPolicy("doc_freq", PooledEstimator(), min_documents=5, min_pmi=0.0),
        ExtractionPolicy("pmi", PooledEstimator(), min_documents=5, min_pmi=5.0),
        ExtractionPolicy("daily_weighted", InterpolatedEstimator(0.75), min_documents=5, min_pmi=5.0),
        ExtractionPolicy("interpolated", InterpolatedEstimator(weight), min_documents=5, min_pmi=5.0),
    )
    candidates = set().union(*(extractor.frequent(p) for p in policies))
    occurrences = OccurrenceScanner().scan(sentences, candidates)
    report["lexicon_statistics_build_s"] = round(time.perf_counter() - started, 1)
    lexicon_stats: dict[str, object] = {}
    entries_by_policy = {}
    builder = DerivedLexiconBuilder()
    for policy in policies:
        t = time.perf_counter()
        entries = extractor.extract(policy, occurrences, set(gov_weights))
        entries_by_policy[policy.name] = entries
        write_entries(LEXICON_DIR / f"{policy.name}.jsonl", entries)
        lexicon, rows = builder.build(entries)
        exp.lexicons[policy.name] = lexicon
        eligible = [e for e in entries if e.eligible]
        reasons: dict[str, int] = {}
        for e in entries:
            reasons[e.eligibility] = reasons.get(e.eligibility, 0) + 1
        lexicon_stats[policy.name] = {
            "policy": {**asdict(policy), "estimator": policy.estimator.name},
            "considered": len(entries),
            "eligibility": dict(sorted(reasons.items())),
            "eligible_words": len(eligible),
            "by_length": {n: sum(len(e.text) == n for e in eligible) for n in (2, 3, 4)},
            "daily_only_words": sum(e.government_count == 0 for e in eligible),
            "government_only_words": sum(e.daily_count == 0 for e in eligible),
            "lexicon_rows_added": rows,
            "weight_median": statistics.median(e.weight for e in eligible) if eligible else None,
            "build_s": round(time.perf_counter() - t, 2),
            "top_by_frequency": [e.text for e in sorted(eligible, key=lambda e: -e.estimated_frequency)[:25]],
        }
        exp.run(Variant(f"E_{policy.name}", PRODUCTION_DAILY, weight, policy.name))
    report["lexicon_variants"] = lexicon_stats
    e_names = [f"E_{p.name}" for p in policies]
    e_choice = SelectionRule().select({n: exp.results[n] for n in e_names}, exp.results["A_gov"])  # type: ignore[misc]
    report["e_selection"] = e_choice
    log(f"[select] E -> {e_choice}")
    e_selected = exp.variants[e_choice["selected"]]  # type: ignore[index]

    analyzer = HomophoneAnalyzer(exp.base.lexicon)
    derived_texts = {e.text for e in entries_by_policy[e_selected.lexicon] if e.eligible}
    e_ctx = exp.context(e_selected)
    lattice = CoverageLattice(e_ctx.lexicon, e_ctx.lm, e_ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
    c_selected = c_choice["selected"]
    report["homophone"] = {
        "competitors": analyzer.competitors(entries_by_policy[e_selected.lexicon]),
        **{
            set_name: analyzer.impact(
                e_ctx, cases, exp.results[c_selected][set_name]["cases"], exp.results[e_selected.name][set_name]["cases"], lattice, derived_texts  # type: ignore[index]
            )
            for set_name, cases in exp.evaluator.sets.items()
        },
    }
    report["perplexity"] = exp.perplexity(["A_gov", "B_daily", *c_names, *(f"{k}_{v}" for k, v in DEV_ONLY_MIXES.items())])

    log("[teacher] loading frozen fine-tuned Laya")
    teacher = TeacherObserver()
    observed: dict[str, object] = {}
    diagnostic: dict[str, object] = {}
    for name in ("A_gov", c_selected, e_selected.name):
        ctx = exp.context(exp.variants[name])
        lat = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
        for set_name, cases in exp.evaluator.sets.items():
            lists = [lat.generate(c.readings, c.left_context).candidates for c in cases]
            ks = WINDOW_SIZES if name in ("A_gov", e_selected.name) else (4,)
            runs = {k: teacher.observe(ctx, cases, lists, k) for k in ks}
            order = [r["rank"] == 0 for r in exp.results[name][set_name]["cases"]]  # type: ignore[index]
            base = runs[4]
            observed.setdefault(name, {})[set_name] = {  # type: ignore[union-attr]
                "decoder_top1": sum(order) / len(order),
                "teacher_top1": base["teacher_top1"],
                "teacher_vs_decoder_order": paired(order, base["correct"]),  # type: ignore[arg-type]
                "latency_p50_ms": base["latency_p50_ms"],
                "latency_p95_ms": base["latency_p95_ms"],
                "fallbacks": base["fallbacks"],
                "correct": base["correct"],
            }
            if len(ks) > 1:
                diagnostic.setdefault(name, {})[set_name] = {  # type: ignore[union-attr]
                    f"K={k}": {
                        **{x: r[x] for x in ("window_coverage", "teacher_top1", "latency_p50_ms", "latency_p95_ms", "gpu_peak_mb", "fallbacks")},
                        "same_pick_as_K4": round(sum(a == b for a, b in zip(r["picks"], base["picks"])) / len(cases), 4),  # type: ignore[arg-type]
                        "vs_K4": paired(base["correct"], r["correct"]),  # type: ignore[arg-type]
                    }
                    for k, r in runs.items()
                }
            log(f"[teacher] {name} {set_name} done")
    for set_name in exp.evaluator.sets:
        a = observed["A_gov"][set_name]["correct"]  # type: ignore[index]
        for name in (c_selected, e_selected.name):
            observed[name][set_name]["teacher_vs_A_teacher"] = paired(a, observed[name][set_name]["correct"])  # type: ignore[index]
    report["teacher_observation"] = observed
    report["teacher_window_diagnostic"] = diagnostic
    report["results"] = exp.results
    path = Path(output) if output else RESULTS / "daily_v1_raw.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    log(f"[written] {path}")
    return 0


class FlatWeightAblation:
    """同一份衍生詞表改成固定權重（= 頻率中位數的權重），用來回答頻率資訊本身是否有用。"""

    def __init__(self, experiment: DailyExperiment) -> None:
        self._exp = experiment

    def run(self, policy_name: str, entries: Sequence[object], daily_lm: str, weight: float) -> dict[str, object]:
        from zaoseq_bopomofo.daily.lexicon import DerivedLexiconBuilder

        flat = [replace(e, weight=10.0) for e in entries]  # type: ignore[type-var]
        lexicon, _ = DerivedLexiconBuilder().build(flat)  # type: ignore[arg-type]
        name = f"{policy_name}_flat10"
        self._exp.lexicons[name] = lexicon
        return self._exp.run(Variant(f"E_{name}", daily_lm, weight, name))


class ResourceSnapshot:
    """新 process 中依序載入 V0、日常 LM、衍生詞表，量 RSS 與載入時間。"""

    def measure(self, daily_lm: str, lexicon_file: Path) -> dict[str, float]:
        from zaoseq_bopomofo.daily.lexicon import DerivedLexiconBuilder, DerivedLexiconEntry
        from zaoseq_bopomofo.daily.mixture import LanguageModelFactory
        from zaoseq_bopomofo.decoding.pipeline import lexicon_characters
        from zaoseq_bopomofo.lexicon.loader import load_lexicon

        probe = ResourceProbe()
        out = {"rss_start_mb": probe.rss_mb()}
        started = time.perf_counter()
        factory = LanguageModelFactory(lexicon_characters(load_lexicon()))
        out.update(v0_load_s=round(time.perf_counter() - started, 2), rss_after_v0_mb=probe.rss_mb())
        started = time.perf_counter()
        factory.mixture(daily_lm, 0.25)
        out.update(daily_lm_load_s=round(time.perf_counter() - started, 2), rss_after_daily_lm_mb=probe.rss_mb())
        started = time.perf_counter()
        rows = [json.loads(line) for line in lexicon_file.read_text(encoding="utf-8").splitlines()]
        entries = [
            DerivedLexiconEntry(**{**r, "readings": tuple(tuple(x) for x in r["readings"]), "source_ids": tuple(r["source_ids"])})
            for r in rows
            if r["eligibility"] == "eligible"
        ]
        DerivedLexiconBuilder().build(entries)
        out.update(derived_lexicon_load_s=round(time.perf_counter() - started, 2), rss_after_derived_lexicon_mb=probe.rss_mb())
        return out


def ablation(output: str | None = None) -> int:
    from zaoseq_bopomofo.corpus.domains import GENERAL_WEIGHTS
    from zaoseq_bopomofo.daily.corpus import PRODUCTION_DAILY, production_source_ids
    from zaoseq_bopomofo.daily.lexicon import (
        LEXICON_DIR,
        ExtractionPolicy,
        FrequencyAwareExtractor,
        OccurrenceScanner,
        PooledEstimator,
        ReadingResolver,
        build_tables,
        corpus_sentences,
    )
    from zaoseq_bopomofo.lexicon.builder import read_builtin
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN

    raw = json.loads((RESULTS / "daily_v1_raw.json").read_text(encoding="utf-8"))
    snapshot = ResourceSnapshot().measure(PRODUCTION_DAILY, LEXICON_DIR / "pmi.jsonl")
    weight = raw["results"][raw["c_selection"]["selected"]]["variant"]["daily_weight"]
    exp = DailyExperiment(lambda m: print(m, file=sys.stderr, flush=True))
    gov_weights = {d.value: w for d, w in GENERAL_WEIGHTS.weights.items()}
    sentences = corpus_sentences(gov_weights, production_source_ids())
    extractor = FrequencyAwareExtractor(build_tables(sentences, gov_weights), ReadingResolver(), {r.text for r in read_builtin(DEFAULT_BUILTIN)})
    policy = ExtractionPolicy("pmi", PooledEstimator(), min_documents=5, min_pmi=5.0)
    entries = extractor.extract(policy, OccurrenceScanner().scan(sentences, set(extractor.frequent(policy))), set(gov_weights))
    result = FlatWeightAblation(exp).run("pmi", entries, PRODUCTION_DAILY, weight)
    report = {
        "note": "diagnostic only, not a selection candidate: selected E word list (pmi) with every derived word at the median weight 10",
        "E_pmi_flat10": {k: {"metrics": v["metrics"]} if isinstance(v, dict) and "metrics" in v else v for k, v in result.items()},
        "resource_snapshot_fresh_process": snapshot,
    }
    path = Path(output) if output else RESULTS / "daily_v1_ablation.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"snapshot": snapshot, "coverage": result["coverage_dev"]["metrics"]["recall"], "gov": result["gov_dev"]["metrics"]["recall"]}, ensure_ascii=False))  # type: ignore[index]
    return 0
