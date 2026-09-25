from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from zaoseq_bopomofo.coverage.analysis import Case, Context
from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig
from zaoseq_bopomofo.daily.clean_lexicon import (
    BoundedReadings,
    CandidateStatistics,
    CartesianReadings,
    CleanLexiconFactory,
    DailyOnlyFilter,
    DailyOnlyPrior,
    DailySupportedFilter,
    DocumentFrequencyFilter,
    DocumentPrior,
    DomainRatioFilter,
    FlatPrior,
    InterpolatedPrior,
    KnownWordReadings,
    LexiconRecipe,
    LogPrior,
    MixedFilter,
    RankBucketPrior,
    RawPrior,
    ReadingEvidence,
    UnambiguousReadings,
    false_competitors,
)
from zaoseq_bopomofo.daily.experiments import RESULTS, SetEvaluator, TeacherObserver, paired
from zaoseq_bopomofo.daily.lexicon import LEXICON_DIR
from zaoseq_bopomofo.daily.selection import ConfigScore, Reference, SelectionPlan
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

ARTIFACT_DIR = LEXICON_DIR / "round2"
DEFAULT_WEIGHT = 0.25
STAGE4_WEIGHTS = (0.0, 0.1, 0.25, 0.5)


@dataclass(frozen=True)
class Round2Config:
    name: str
    stage: str
    daily_lm: str | None
    daily_weight: float
    recipe: LexiconRecipe | None
    production_eligible: bool

    def describe(self) -> dict[str, object]:
        return {
            "name": self.name,
            "stage": self.stage,
            "daily_lm": self.daily_lm,
            "daily_weight": self.daily_weight,
            "lexicon": self.recipe.name if self.recipe else "builtin",
            "production_eligible": self.production_eligible,
        }


class LexiconArtifacts:
    """recipe → 衍生詞 → frozen Lexicon → compact artifact 與 provenance 表；同一 recipe 只建一次。"""

    def __init__(self, factory: CleanLexiconFactory, base_lexicon: object, evidence: ReadingEvidence, out_dir: Path = ARTIFACT_DIR) -> None:
        self._factory = factory
        self._base = base_lexicon
        self._supported = BoundedReadings(evidence)
        self._out = out_dir
        self._cache: dict[str, tuple[object, dict[str, object]]] = {}
        self.entries: dict[str, tuple] = {}  # type: ignore[type-arg]

    @staticmethod
    def slug(recipe: LexiconRecipe) -> str:
        return recipe.name.replace("|", "__")

    def path(self, recipe: LexiconRecipe) -> Path:
        return self._out / f"{self.slug(recipe)}.bin"

    def get(self, recipe: LexiconRecipe) -> tuple[object, dict[str, object]]:
        if recipe.name in self._cache:
            return self._cache[recipe.name]
        from zaoseq_bopomofo.daily.compact import CompactLexicon, CompactLexiconWriter, LexiconSnapshot, ProvenanceTable
        from zaoseq_bopomofo.daily.lexicon import DerivedLexiconBuilder

        started = time.perf_counter()
        result = self._factory.build(recipe)
        lexicon, rows = DerivedLexiconBuilder().build(result.entries)
        self._out.mkdir(parents=True, exist_ok=True)
        table = ProvenanceTable(result.entries)
        CompactLexiconWriter().write(LexiconSnapshot.of(lexicon), self.path(recipe), table.ids)
        table.write(self._out / f"{self.slug(recipe)}.provenance.json")
        compact = CompactLexicon(self.path(recipe))
        info = {
            "recipe": recipe.name,
            "derived_words": len(result.entries),
            "by_length": {n: sum(len(e.text) == n for e in result.entries) for n in (2, 3, 4)},
            "lexicon_rows_added": rows,
            "lexicon_entries": len(compact),
            "rejected": dict(result.rejected),
            "daily_supported_words": sum(e.daily_count > 0 for e in result.entries),
            "government_only_words": sum(e.daily_count == 0 for e in result.entries),
            **false_competitors(result.entries, self._supported, self._base),
            "weight_distribution": weight_summary([e.weight for e in result.entries]),
            "artifact_mb": round(self.path(recipe).stat().st_size / 2**20, 3),
            "build_s": round(time.perf_counter() - started, 2),
        }
        self._cache[recipe.name] = (compact, info)
        self.entries[recipe.name] = result.entries
        return compact, info


def weight_summary(weights: Sequence[float]) -> dict[str, float]:
    if not weights:
        return {}
    ordered = sorted(weights)
    pick = lambda q: ordered[int(round(q * (len(ordered) - 1)))]  # noqa: E731
    return {"min": ordered[0], "p25": pick(0.25), "median": pick(0.5), "p75": pick(0.75), "max": ordered[-1]}


RUNTIME_SNAPSHOT = """
import json, os, sys, time, gc
import psutil
proc = psutil.Process(os.getpid())
rss = lambda: proc.memory_info().rss / 2**20
from zaoseq_bopomofo.daily.mixture import LanguageModelFactory
from zaoseq_bopomofo.decoding.pipeline import lexicon_characters
from zaoseq_bopomofo.lexicon.loader import load_lexicon
daily, weight, lexicon_path = sys.argv[1], float(sys.argv[2]), sys.argv[3]
out = {"rss_start_mb": rss()}
t = time.perf_counter(); factory = LanguageModelFactory(lexicon_characters(load_lexicon())); gc.collect()
out.update(v0_load_s=time.perf_counter() - t, rss_after_v0_mb=rss())
t = time.perf_counter(); lm = factory.mixture(None if daily == "-" else daily, weight); gc.collect()
out.update(daily_lm_load_s=time.perf_counter() - t, rss_after_daily_lm_mb=rss())
if lexicon_path != "-":
    from zaoseq_bopomofo.daily.compact import CompactLexicon
    t = time.perf_counter(); lexicon = CompactLexicon(__import__("pathlib").Path(lexicon_path)); gc.collect()
    out.update(lexicon_load_s=time.perf_counter() - t, rss_after_lexicon_mb=rss())
print(json.dumps(out))
"""


class RuntimeProbe:
    """新 process 中依序載入 V0、日常 LM 與 compact 詞表，量增量 RSS 與載入時間。"""

    def measure(self, config: Round2Config, lexicon_path: Path | None) -> dict[str, float]:
        args = [config.daily_lm or "-", str(config.daily_weight), str(lexicon_path) if lexicon_path else "-"]
        env = {**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}
        done = subprocess.run([sys.executable, "-c", RUNTIME_SNAPSHOT, *args], capture_output=True, text=True, env=env, check=True)
        out = json.loads(done.stdout.strip().splitlines()[-1])
        end = out.get("rss_after_lexicon_mb", out["rss_after_daily_lm_mb"])
        out["incremental_rss_mb"] = round(end - out["rss_after_v0_mb"], 1)
        return {k: round(v, 3) for k, v in out.items()}


class Round2Runner:
    def __init__(self, log: Callable[[str], None]) -> None:
        from zaoseq_bopomofo.corpus.domains import GENERAL_WEIGHTS
        from zaoseq_bopomofo.coverage.analysis import build_context, coverage_cases, gov_dev_cases
        from zaoseq_bopomofo.coverage.dataset import V1_1
        from zaoseq_bopomofo.daily.corpus import production_source_ids
        from zaoseq_bopomofo.daily.mixture import LanguageModelFactory
        from zaoseq_bopomofo.decoding.pipeline import lexicon_characters
        from zaoseq_bopomofo.lexicon.builder import read_char_readings
        from zaoseq_bopomofo.lexicon.loader import DEFAULT_CHAR_READINGS, load_lexicon

        self.log = log
        self.plan = SelectionPlan()
        self.base = build_context()
        self.lm_factory = LanguageModelFactory(lexicon_characters(load_lexicon()))
        self.evaluator = SetEvaluator({"coverage_dev": coverage_cases(V1_1), "gov_dev": gov_dev_cases(100)})
        self.gov_weights = {d.value: w for d, w in GENERAL_WEIGHTS.weights.items()}
        self.evidence = ReadingEvidence.load()
        started = time.perf_counter()
        self.candidates = self.candidate_statistics(production_source_ids())
        self.statistics_s = round(time.perf_counter() - started, 1)
        planes: dict[str, list[str]] = {}
        for row in read_char_readings(DEFAULT_CHAR_READINGS):
            if row.plane in (1, 2) and row.reading not in planes.setdefault(row.char, []):
                planes[row.char].append(row.reading)
        self.planes = planes
        self.artifacts = self.lexicon_artifacts(self.candidates)
        self.runtime = RuntimeProbe()
        self.teacher = TeacherObserver()
        self.results: dict[str, dict[str, object]] = {}
        self.scores: dict[str, ConfigScore] = {}
        self.reference: Reference | None = None
        self.reference_correct: dict[str, list[bool]] = {}

    def candidate_statistics(self, daily_sources: set[str]) -> CandidateStatistics:
        """候選詞統計：政府 train split 加上 `daily_sources` 的 train split。"""
        from zaoseq_bopomofo.daily.lexicon import build_tables, corpus_sentences
        from zaoseq_bopomofo.lexicon.builder import read_builtin
        from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN

        sentences = corpus_sentences(self.gov_weights, daily_sources)
        tables = build_tables(sentences, self.gov_weights)
        return CandidateStatistics(tables, sentences, {r.text for r in read_builtin(DEFAULT_BUILTIN)})

    def lexicon_artifacts(self, candidates: CandidateStatistics, out_dir: Path = ARTIFACT_DIR) -> LexiconArtifacts:
        return LexiconArtifacts(CleanLexiconFactory(candidates, set(self.gov_weights)), self.base.lexicon, self.evidence, out_dir)

    def context(self, config: Round2Config) -> Context:
        from zaoseq_bopomofo.daily.mixture import CachedLanguageModel

        lexicon = self.artifacts.get(config.recipe)[0] if config.recipe else self.base.lexicon
        lm = CachedLanguageModel(self.lm_factory.mixture(config.daily_lm, config.daily_weight))
        return replace(self.base, lm=lm, lexicon=lexicon)

    def run(self, config: Round2Config) -> ConfigScore:
        if config.name in self.scores:
            return self.scores[config.name]
        ctx = self.context(config)
        report = self.evaluator.evaluate(ctx)
        teacher: dict[str, dict[str, object]] = {}
        lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
        for set_name, cases in self.evaluator.sets.items():
            lists = [lattice.generate(c.readings, c.left_context).candidates for c in cases]
            teacher[set_name] = self.teacher.observe(ctx, cases, lists, 4)
        lexicon_info = self.artifacts.get(config.recipe)[1] if config.recipe else {"lexicon_entries": len(self.base.lexicon), "artifact_mb": 0.0}  # type: ignore[arg-type]
        runtime = self.runtime.measure(config, self.artifacts.path(config.recipe) if config.recipe else None)
        daily_mb = sum(p.stat().st_size for p in (PROJECT_ROOT / "data" / "daily" / "lm" / config.daily_lm).glob("*.gz")) / 2**20 if config.daily_lm and config.daily_weight else 0.0
        if self.reference is None:
            self.reference = Reference(report["gov_dev"]["metrics"]["recall"]["@1"], teacher["gov_dev"]["teacher_top1"])  # type: ignore[index,arg-type]
            self.reference_correct = {s: teacher[s]["correct"] for s in teacher}  # type: ignore[misc]
        cov, gov = report["coverage_dev"]["metrics"], report["gov_dev"]["metrics"]  # type: ignore[index]
        vs_reference = {s: paired(self.reference_correct[s], teacher[s]["correct"]) for s in teacher}  # type: ignore[index,arg-type]
        score = ConfigScore(
            name=config.name,
            production_eligible=config.production_eligible,
            gov_baseline_top1=gov["recall"]["@1"],  # type: ignore[index]
            gov_teacher_top1=teacher["gov_dev"]["teacher_top1"],  # type: ignore[arg-type]
            coverage_teacher_top1=teacher["coverage_dev"]["teacher_top1"],  # type: ignore[arg-type]
            coverage_teacher_correct_to_wrong=int(vs_reference["coverage_dev"]["correct_to_wrong"]),
            coverage_baseline_top1=cov["top1"],  # type: ignore[index]
            coverage_mrr=cov["mrr"],  # type: ignore[index]
            coverage_r5=cov["recall"]["@5"],  # type: ignore[index]
            coverage_window=cov["window_recall_top4_families"],  # type: ignore[index]
            coverage_p95_ms=cov["latency_p95_ms"],  # type: ignore[index]
            rss_mb=runtime["incremental_rss_mb"],
            artifact_mb=round(daily_mb + float(lexicon_info["artifact_mb"]), 3),  # type: ignore[arg-type]
        )
        self.scores[config.name] = score
        self.results[config.name] = {
            "config": config.describe(),
            **report,
            "teacher": {s: {k: v for k, v in t.items() if k not in ("correct", "picks")} for s, t in teacher.items()},
            "teacher_vs_v0_teacher": vs_reference,
            "teacher_correct": {s: t["correct"] for s, t in teacher.items()},
            "lexicon": lexicon_info,
            "runtime": runtime,
            "lm_cache": {"hits": ctx.lm.hits, "misses": ctx.lm.misses},  # type: ignore[attr-defined]
            "score": asdict(score),
        }
        self.log(
            f"[done] {config.name}: cov base {score.coverage_baseline_top1:.3f} teacher {score.coverage_teacher_top1:.3f} "
            f"| gov base {score.gov_baseline_top1:.3f} teacher {score.gov_teacher_top1:.3f} | +RSS {score.rss_mb} MB"
        )
        return score

    def select(self, names: Sequence[str]) -> dict[str, object]:
        assert self.reference is not None
        scores = [self.scores[n] for n in names]
        decision = self.plan.select(scores, self.reference)
        out = SelectionPlan.to_json(decision, scores)
        if decision.selected is None:
            eligible = [s for s in scores if s.production_eligible]
            best = max(s.coverage_teacher_top1 for s in eligible)
            tied = [s for s in eligible if best - s.coverage_teacher_top1 <= 1 / 300 + 1e-9]
            out["fallback_without_gates"] = min(tied, key=SelectionPlan.tie_key).name
        return out


class DevEquivalence:
    """同一設定下：frozen Lexicon vs compact、未快取 vs 快取 LM，700 句候選文字與分數逐項比較。"""

    def check(self, runner: Round2Runner, config: Round2Config) -> dict[str, object]:
        from zaoseq_bopomofo.daily.lexicon import DerivedLexiconBuilder

        compact_ctx = runner.context(config)
        plain_lm = runner.lm_factory.mixture(config.daily_lm, config.daily_weight)
        reference_lexicon = DerivedLexiconBuilder().build(runner.artifacts.entries[config.recipe.name])[0] if config.recipe else runner.base.lexicon
        systems = {
            "frozen_lexicon_uncached_lm": CoverageLattice(reference_lexicon, plain_lm, compact_ctx.scorer, GenerationConfig()),  # type: ignore[arg-type]
            "compact_lexicon_cached_lm": CoverageLattice(compact_ctx.lexicon, compact_ctx.lm, compact_ctx.scorer, GenerationConfig()),  # type: ignore[arg-type]
        }
        timing: dict[str, list[float]] = {k: [] for k in systems}
        mismatches: list[str] = []
        cases: list[Case] = [c for cs in runner.evaluator.sets.values() for c in cs]
        for case in cases:
            outputs = []
            for name, lattice in systems.items():
                started = time.perf_counter()
                candidates = lattice.generate(case.readings, case.left_context).candidates
                timing[name].append((time.perf_counter() - started) * 1000)
                outputs.append([(c.text, c.baseline_score) for c in candidates])
            if outputs[0] != outputs[1]:
                mismatches.append(case.item_id)
        from zaoseq_bopomofo.daily.experiments import percent

        return {
            "config": config.name,
            "cases": len(cases),
            "mismatches": mismatches,
            "latency_ms": {k: {"p50": round(percent(v, 0.5), 1), "p95": round(percent(v, 0.95), 1)} for k, v in timing.items()},
        }


class LexiconBenchmark:
    """同一份衍生詞在三種表示下的載入時間、增量 RSS 與 lookup 延遲（各自在新 process 量測）。"""

    SCRIPT = """
import json, os, sys, time, gc, random
import psutil
proc = psutil.Process(os.getpid())
rss = lambda: proc.memory_info().rss / 2**20
from pathlib import Path
mode, path, provenance = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
from zaoseq_bopomofo.lexicon.loader import load_lexicon
base = load_lexicon().lexicon
gc.collect(); before = rss(); t = time.perf_counter()
if mode == "compact":
    from zaoseq_bopomofo.daily.compact import CompactLexicon
    lexicon = CompactLexicon(path)
else:
    from zaoseq_bopomofo.daily.lexicon import DerivedLexiconBuilder, DerivedLexiconEntry
    rows = json.loads(provenance.read_text(encoding="utf-8"))
    entries = [DerivedLexiconEntry(**{k: v for k, v in r.items() if k != "id"} | {"readings": tuple(tuple(x) for x in r["readings"]), "source_ids": tuple(r["source_ids"])}) for r in rows]
    lexicon = DerivedLexiconBuilder().build(entries)[0]
    if mode == "frozen_lexicon":
        del rows, entries
gc.collect(); load = time.perf_counter() - t; after = rss()
keys = sorted({tuple(e.readings) for s in base.syllables for e in base.lookup((s,))})
random.seed(0); probes = [random.choice(keys) for _ in range(20000)]
t = time.perf_counter()
for k in probes: lexicon.lookup(k)
lookup_us = (time.perf_counter() - t) / len(probes) * 1e6
print(json.dumps({"load_s": round(load, 3), "incremental_rss_mb": round(after - before, 1), "lookup_us": round(lookup_us, 3)}))
"""

    def measure(self, artifacts: LexiconArtifacts, recipe: LexiconRecipe) -> dict[str, object]:
        import os

        path = artifacts.path(recipe)
        provenance = path.with_name(path.name.replace(".bin", ".provenance.json"))
        env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}
        out: dict[str, object] = {"artifact_mb": round(path.stat().st_size / 2**20, 3), "provenance_json_mb": round(provenance.stat().st_size / 2**20, 3)}
        for mode in ("frozen_lexicon_with_provenance_alive", "frozen_lexicon", "compact"):
            done = subprocess.run([sys.executable, "-c", self.SCRIPT, mode, str(path), str(provenance)], capture_output=True, text=True, env=env, check=True)
            out[mode] = json.loads(done.stdout.strip().splitlines()[-1])
        return out


def gold_word_order(runner: Round2Runner, recipes: Sequence[LexiconRecipe]) -> dict[str, dict[str, int]]:
    """Coverage-DEV 的 gold 多字詞：若同讀音有其他同長度詞，gold 是否排在同音詞之前（詞庫順序即先驗大小）。"""
    out: dict[str, dict[str, int]] = {}
    cases = runner.evaluator.sets["coverage_dev"]
    for recipe in recipes:
        lexicon = runner.artifacts.get(recipe)[0]
        contested = first = 0
        for case in cases:
            if case.item is None:
                continue
            for start, end, word in case.item.word_spans():
                if end - start < 2:
                    continue
                entries = [e for e in lexicon.lookup(case.readings[start:end]) if len(e.text) == end - start]  # type: ignore[attr-defined]
                texts = [e.text for e in entries]
                if word.text in texts and len(texts) > 1:
                    contested += 1
                    first += texts[0] == word.text
        out[recipe.prior.name] = {"contested_gold_words": contested, "gold_ranked_first": first}
    return out


def main(output: str | None = None) -> int:
    from zaoseq_bopomofo.daily.corpus import ALL_DAILY, PRODUCTION_DAILY, production_source_ids

    def log(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    runner = Round2Runner(log)
    ev = runner.evidence
    report: dict[str, object] = {
        "plan_sha256": runner.plan.sha256,
        "candidate_statistics_s": runner.statistics_s,
        "candidate_ngrams": len(runner.candidates.stats),
        "production_daily_sources": sorted(production_source_ids()),
    }

    def config(name: str, stage: str, recipe: LexiconRecipe | None, weight: float = DEFAULT_WEIGHT, daily: str = PRODUCTION_DAILY, eligible: bool = True) -> Round2Config:
        return Round2Config(name, stage, daily if weight else None, weight, recipe, eligible)

    reference = config("A_v0", "reference", None, 0.0)
    runner.run(reference)
    stages: dict[str, object] = {}

    readings = {
        "R0": CartesianReadings(ev, runner.planes),
        "R1": UnambiguousReadings(ev),
        "R2": KnownWordReadings(ev),
        "R3": BoundedReadings(ev),
    }
    stage1 = {k: config(f"S1_{k}", "1_reading", LexiconRecipe(p, MixedFilter(), FlatPrior()), eligible=k != "R0") for k, p in readings.items()}
    for c in stage1.values():
        runner.run(c)
    stages["1_reading"] = runner.select([c.name for c in stage1.values()])
    reading = stage1[winner(stages["1_reading"])[3:]].recipe.reading  # type: ignore[index,union-attr]
    log(f"[select] stage 1 -> {winner(stages['1_reading'])}")

    filters = {"L1": MixedFilter(), "L2": DailyOnlyFilter(), "L3": DailySupportedFilter(), "L4": DomainRatioFilter(), "L5": DocumentFrequencyFilter()}
    stage2 = {k: config(f"S2_{k}", "2_extraction", LexiconRecipe(reading, f, FlatPrior())) for k, f in filters.items()}
    for c in stage2.values():
        runner.run(c)
    stages["2_extraction"] = runner.select([c.name for c in stage2.values()])
    extraction = stage2[winner(stages["2_extraction"])[3:]].recipe.extraction  # type: ignore[index,union-attr]
    log(f"[select] stage 2 -> {winner(stages['2_extraction'])}")

    priors = [FlatPrior(), RawPrior(), LogPrior(), DocumentPrior(), DailyOnlyPrior(), InterpolatedPrior(), RankBucketPrior()]
    stage3 = {p.name: config(f"S3_{p.name}", "3_prior", LexiconRecipe(reading, extraction, p)) for p in priors}
    for c in stage3.values():
        runner.run(c)
    stages["3_prior"] = runner.select([c.name for c in stage3.values()])
    recipe = stage3[winner(stages["3_prior"])[3:]].recipe
    log(f"[select] stage 3 -> {winner(stages['3_prior'])}")
    report["gold_word_order_by_prior"] = gold_word_order(runner, [c.recipe for c in stage3.values()])  # type: ignore[misc]

    stage4 = {w: config(f"S4_daily{w:g}", "4_lm_weight", recipe, w) for w in STAGE4_WEIGHTS}
    for c in stage4.values():
        runner.run(c)
    stages["4_lm_weight"] = runner.select([c.name for c in stage4.values()])
    log(f"[select] stage 4 -> {winner(stages['4_lm_weight'])}")
    stages["5_corpus_ablation"] = {"skipped": "only one production-approved daily source (tatoeba_cmn_hant)"}
    report["stages"] = stages

    chosen_stage4 = next(c for c in stage4.values() if c.name == winner(stages["4_lm_weight"]))
    diagnostic = config("DIAG_oasst_mix", "diagnostic", recipe, chosen_stage4.daily_weight or DEFAULT_WEIGHT, ALL_DAILY, eligible=False)
    runner.run(diagnostic)

    eligible = [n for n, s in runner.scores.items() if s.production_eligible]
    report["final"] = runner.select(eligible)
    final_name = winner(report["final"])  # type: ignore[arg-type]
    log(f"[select] final -> {final_name}")
    configs = {c.name: c for c in (reference, *stage1.values(), *stage2.values(), *stage3.values(), *stage4.values(), diagnostic)}
    final = configs[final_name]
    if final.recipe:
        report["lexicon_benchmark"] = LexiconBenchmark().measure(runner.artifacts, final.recipe)
        report["lexicon_benchmark_R0"] = LexiconBenchmark().measure(runner.artifacts, stage1["R0"].recipe)  # type: ignore[arg-type]
    report["dev_equivalence"] = DevEquivalence().check(runner, final)
    report["results"] = runner.results
    path = Path(output) if output else RESULTS / "daily_round2_raw.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    log(f"[written] {path}")
    return 0


def winner(selection: object) -> str:
    data = selection  # type: ignore[assignment]
    return data["selected"] or data["fallback_without_gates"]  # type: ignore[index]
