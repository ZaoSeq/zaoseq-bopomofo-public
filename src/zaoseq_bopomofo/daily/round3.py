from __future__ import annotations

import gc
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from zaoseq_bopomofo.coverage.analysis import Case, Context
from zaoseq_bopomofo.coverage.lattice import CoverageLattice, GenerationConfig
from zaoseq_bopomofo.daily.lexicon import LEXICON_DIR
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

RESULTS = PROJECT_ROOT / "benchmarks" / "results"
ROUND2_LEXICON = LEXICON_DIR / "round2" / "R2_known_word__L5_doc_frequency__daily_only.bin"


@dataclass(frozen=True)
class SystemConfig:
    """一個 decoder 設定：日常 LM（None = V0 政府 LM）與 compact 衍生詞表（None = builtin）。"""

    name: str
    daily_lm: str | None
    daily_weight: float
    lexicon_path: Path | None


V0 = SystemConfig("V0", None, 0.0, None)
ROUND2_WINNER = SystemConfig("round2_winner", "tatoeba_cmn_hant", 0.5, ROUND2_LEXICON)
ROUND3_WINNER = SystemConfig("round3_winner", "daily_production", 0.5, LEXICON_DIR / "round3" / "S5_tatoeba_common_voice" / ROUND2_LEXICON.name)
# runtime cache 容量尚未定案（PROVISIONAL，不屬於 semantic freeze）；各容量輸出逐項相同。
PROVISIONAL_CAPACITY = "bounded_8mb"


def percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    index = (len(ordered) - 1) * q
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def summary(values: Sequence[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 3),
        "p50": round(percentile(values, 0.5), 3),
        "p95": round(percentile(values, 0.95), 3),
        "p99": round(percentile(values, 0.99), 3),
    }


class SystemFactory:
    """建立 decoder 評估用的 Context：V0 的詞庫、scorer、family table，換上指定的 LM 與詞表。"""

    def __init__(self) -> None:
        from zaoseq_bopomofo.coverage.analysis import build_context
        from zaoseq_bopomofo.daily.mixture import LanguageModelFactory
        from zaoseq_bopomofo.decoding.pipeline import lexicon_characters
        from zaoseq_bopomofo.lexicon.loader import load_lexicon

        self.base = build_context()
        self.lm_factory = LanguageModelFactory(lexicon_characters(load_lexicon()))
        self._lexicons: dict[Path, object] = {}

    def lexicon(self, config: SystemConfig) -> object:
        if config.lexicon_path is None:
            return self.base.lexicon
        if config.lexicon_path not in self._lexicons:
            from zaoseq_bopomofo.daily.compact import CompactLexicon

            self._lexicons[config.lexicon_path] = CompactLexicon(config.lexicon_path)
        return self._lexicons[config.lexicon_path]

    def context(self, config: SystemConfig, cache_capacity: int | None | str = "none") -> Context:
        from zaoseq_bopomofo.daily.mixture import BoundedLanguageModelCache

        lm = self.lm_factory.mixture(config.daily_lm, config.daily_weight)
        if cache_capacity != "none":
            lm = BoundedLanguageModelCache(lm, cache_capacity)  # type: ignore[arg-type]
        return replace(self.base, lm=lm, lexicon=self.lexicon(config))


def dev_cases() -> dict[str, list[Case]]:
    from zaoseq_bopomofo.coverage.analysis import coverage_cases, gov_dev_cases
    from zaoseq_bopomofo.coverage.dataset import V1_1

    return {"coverage_dev": coverage_cases(V1_1), "gov_dev": gov_dev_cases(100)}


class CacheCostProbe:
    """以實際 DEV 解碼收集 cache 項目，再在乾淨的 tracemalloc 區段中重建同樣的 LRU 結構，量每筆的記憶體。"""

    def measure(self, factory: SystemFactory, config: SystemConfig, cases: Sequence[Case]) -> dict[str, float]:
        ctx = factory.context(config, None)
        lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
        for case in cases:
            lattice.generate(case.readings, case.left_context)
        items = list(ctx.lm._cache.items())  # type: ignore[attr-defined]  # noqa: SLF001
        gc.collect()
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        rebuilt: OrderedDict[tuple[str, str], tuple[float, str]] = OrderedDict()
        for (history, char), (value, new_history) in items:
            rebuilt[("".join(list(history)), "".join(list(char)))] = (float(value), "".join(list(new_history)))
        after = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        size = after - before
        return {
            "entries_after_dev": len(items),
            "bytes_total": size,
            "bytes_per_entry": round(size / len(items), 1),
            "stats": ctx.lm.stats(),  # type: ignore[attr-defined]
        }


def environment() -> dict[str, object]:
    import numpy
    import psutil

    try:
        import torch

        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        torch_version = torch.__version__
    except ImportError:
        gpu = torch_version = None
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "torch": torch_version,
        "gpu": gpu,
        "pid": os.getpid(),
    }


def main_cache_cost(output: Path | None = None) -> int:
    factory = SystemFactory()
    cases = [c for cs in dev_cases().values() for c in cs]
    result = {
        "environment": environment(),
        "config": ROUND2_WINNER.name,
        "cases": len(cases),
        "cost": CacheCostProbe().measure(factory, ROUND2_WINNER, cases),
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    path = output or RESULTS / "round3_cache_cost.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


WARMUP_CASES = 20
REPETITIONS = 5
CACHE_CANDIDATES = {"disabled": 0, "bounded_8mb": 22000, "bounded_16mb": 44000, "bounded_32mb": 88000, "unbounded_reference": None}
SYSTEMS = {c.name: c for c in (V0, ROUND2_WINNER, ROUND3_WINNER)}


def rss_mb() -> float:
    import psutil

    return round(psutil.Process(os.getpid()).memory_info().rss / 2**20, 1)


class OutputSignature:
    """所有 case 的候選文字與分數的雜湊；用來確認不同 cache 容量的輸出逐項相同。"""

    def __init__(self) -> None:
        import hashlib

        self._digest = hashlib.sha256()

    def add(self, candidates: Sequence[object]) -> None:
        for c in candidates:
            self._digest.update(f"{c.text}\t{c.baseline_score!r}\n".encode())  # type: ignore[attr-defined]
        self._digest.update(b"|")

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


class DecoderLatencyRun:
    """單一 process 內：載入 → warm-up → 固定案例順序重複計時 generate()。cache 在重複之間保留（與常駐服務相同）。"""

    def __init__(self, system: SystemConfig, capacity: int | None | str) -> None:
        self.system = system
        self.capacity = capacity

    def run(self) -> dict[str, object]:
        rss_start = rss_mb()
        started = time.perf_counter()
        factory = SystemFactory()
        ctx = factory.context(self.system, self.capacity)
        cases = [c for cs in dev_cases().values() for c in cs]
        load_s = time.perf_counter() - started
        rss_loaded = rss_mb()
        lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
        for case in cases[:WARMUP_CASES]:
            lattice.generate(case.readings, case.left_context)
        repetitions = []
        signature = OutputSignature()
        for rep in range(REPETITIONS):
            times = []
            for case in cases:
                t = time.perf_counter()
                out = lattice.generate(case.readings, case.left_context)
                times.append((time.perf_counter() - t) * 1000)
                if rep == 0:
                    signature.add(out.candidates)
            repetitions.append(summary(times))
        cache = ctx.lm.stats() if hasattr(ctx.lm, "stats") else None  # type: ignore[attr-defined]
        return {
            "system": self.system.name,
            "capacity": self.capacity,
            "cases": len(cases),
            "load_s": round(load_s, 2),
            "rss_start_mb": rss_start,
            "rss_after_load_mb": rss_loaded,
            "rss_after_runs_mb": rss_mb(),
            "repetitions": repetitions,
            "median": {k: round(statistics.median(r[k] for r in repetitions), 3) for k in ("mean", "p50", "p95", "p99")},
            "cache": cache,
            "output_signature": signature.hexdigest(),
        }


class TeacherLatencyRun:
    """decoder 先產生全部候選（不計時），再分別計時 teacher-only 與 decoder + teacher 端到端。"""

    def __init__(self, system: SystemConfig, capacity: int | None) -> None:
        self.system = system
        self.capacity = capacity

    def run(self) -> dict[str, object]:
        from zaoseq_bopomofo.daily.experiments import TeacherObserver
        from zaoseq_bopomofo.ranking.base import RankingContext

        started = time.perf_counter()
        factory = SystemFactory()
        ctx = factory.context(self.system, self.capacity)
        decoder_load_s = time.perf_counter() - started
        rss_decoder = rss_mb()
        started = time.perf_counter()
        observer = TeacherObserver()
        ranker = observer.ranker(4)
        teacher_load_s = time.perf_counter() - started
        rss_teacher = rss_mb()
        cases = [c for cs in dev_cases().values() for c in cs]
        lattice = CoverageLattice(ctx.lexicon, ctx.lm, ctx.scorer, GenerationConfig())  # type: ignore[arg-type]
        lists = [lattice.generate(c.readings, c.left_context).candidates for c in cases]
        for case, candidates in list(zip(cases, lists))[:WARMUP_CASES]:
            ranker.rank(RankingContext(case.left_context, case.readings), candidates)
        teacher_reps, e2e_reps = [], []
        for _ in range(REPETITIONS):
            times = []
            for case, candidates in zip(cases, lists):
                t = time.perf_counter()
                ranker.rank(RankingContext(case.left_context, case.readings), candidates)
                times.append((time.perf_counter() - t) * 1000)
            teacher_reps.append(summary(times))
        for _ in range(REPETITIONS):
            times = []
            for case in cases:
                t = time.perf_counter()
                candidates = lattice.generate(case.readings, case.left_context).candidates
                ranker.rank(RankingContext(case.left_context, case.readings), candidates)
                times.append((time.perf_counter() - t) * 1000)
            e2e_reps.append(summary(times))

        def median(reps: list[dict[str, float]]) -> dict[str, float]:
            return {k: round(statistics.median(r[k] for r in reps), 3) for k in ("mean", "p50", "p95", "p99")}

        return {
            "system": self.system.name,
            "capacity": self.capacity,
            "cases": len(cases),
            "decoder_load_s": round(decoder_load_s, 2),
            "teacher_load_s": round(teacher_load_s, 2),
            "rss_after_decoder_mb": rss_decoder,
            "rss_after_teacher_mb": rss_teacher,
            "teacher_only": {"repetitions": teacher_reps, "median": median(teacher_reps)},
            "end_to_end": {"repetitions": e2e_reps, "median": median(e2e_reps)},
        }


class QuietBenchmark:
    """依序在新 process 中執行每個量測，一次只跑一個，結果寫入單一 JSON。"""

    def __init__(self, output: Path) -> None:
        self.output = output
        self.results: dict[str, object] = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}

    def child(self, *args: str) -> dict[str, object]:
        import subprocess

        env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
        done = subprocess.run([sys.executable, "-m", "zaoseq_bopomofo.daily.round3", *args], capture_output=True, text=True, env=env, check=True)
        return json.loads(done.stdout.strip().splitlines()[-1])

    def save(self) -> None:
        self.output.write_text(json.dumps(self.results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    def decoder(self, system: str, capacity_name: str) -> dict[str, object]:
        key = f"decoder|{system}|{capacity_name}"
        if key not in self.results:
            self.results[key] = self.child("child-decoder", system, capacity_name)
            self.save()
            median = self.results[key]["median"]  # type: ignore[index]
            print(f"[done] {key}: {median}", file=sys.stderr, flush=True)
        return self.results[key]  # type: ignore[return-value]

    def teacher(self, system: str, capacity_name: str) -> dict[str, object]:
        key = f"teacher|{system}|{capacity_name}"
        if key not in self.results:
            self.results[key] = self.child("child-teacher", system, capacity_name)
            self.save()
            print(f"[done] {key}", file=sys.stderr, flush=True)
        return self.results[key]  # type: ignore[return-value]


class CacheSelection:
    """addendum 的規則：只看有上限的容量；p50 / p95 ≤ 最佳 ×1.05、p99 ≤ 最佳 ×1.10 中取最小容量。"""

    def select(self, runs: dict[str, dict[str, object]]) -> dict[str, object]:
        signatures = {name: r["output_signature"] for name, r in runs.items()}
        identical = len(set(signatures.values())) == 1
        bounded = {n: r["median"] for n, r in runs.items() if isinstance(CACHE_CANDIDATES[n], int) and CACHE_CANDIDATES[n] > 0}  # type: ignore[misc]
        best = {k: min(m[k] for m in bounded.values()) for k in ("p50", "p95", "p99")}  # type: ignore[index]
        limits = {"p50": 1.05, "p95": 1.05, "p99": 1.10}
        acceptable = [n for n, m in bounded.items() if all(m[k] <= best[k] * limits[k] for k in limits)]  # type: ignore[index]
        chosen = min(acceptable, key=lambda n: CACHE_CANDIDATES[n]) if acceptable and identical else None  # type: ignore[arg-type,return-value]
        return {"outputs_identical": identical, "signatures": signatures, "best_bounded": best, "acceptable": acceptable, "selected": chosen}


def capacity_value(name: str) -> int | None | str:
    return "none" if name == "none" else CACHE_CANDIDATES[name]


def main_child_decoder(system: str, capacity_name: str) -> int:
    print(json.dumps(DecoderLatencyRun(SYSTEMS[system], capacity_value(capacity_name)).run(), ensure_ascii=False))
    return 0


def main_child_teacher(system: str, capacity_name: str) -> int:
    print(json.dumps(TeacherLatencyRun(SYSTEMS[system], capacity_value(capacity_name)).run(), ensure_ascii=False))  # type: ignore[arg-type]
    return 0


def main_quiet(output: Path | None = None) -> int:
    bench = QuietBenchmark(output or RESULTS / "round3_quiet_latency.json")
    bench.results["environment"] = environment()
    bench.results["protocol"] = {"warmup_cases": WARMUP_CASES, "repetitions": REPETITIONS, "cache_candidates": CACHE_CANDIDATES}
    bench.save()
    bench.decoder("V0", "none")
    runs = {name: bench.decoder(ROUND2_WINNER.name, name) for name in CACHE_CANDIDATES}
    selection = CacheSelection().select(runs)
    bench.results["cache_selection"] = selection
    bench.save()
    print(f"[select] cache -> {selection['selected']} identical={selection['outputs_identical']}", file=sys.stderr, flush=True)
    if selection["selected"]:
        bench.teacher("V0", "none")
        bench.teacher(ROUND2_WINNER.name, selection["selected"])  # type: ignore[arg-type]
    print("[written]", bench.output, file=sys.stderr, flush=True)
    return 0


def main_quiet_winner(output: Path | None = None) -> int:
    """Round 3 winner 用暫定 cache 容量量延遲；另量關閉 cache 的 decoder 以確認輸出逐項相同。"""
    bench = QuietBenchmark(output or RESULTS / "round3_quiet_latency.json")
    runs = {name: bench.decoder(ROUND3_WINNER.name, name) for name in ("disabled", PROVISIONAL_CAPACITY)}
    identical = len({r["output_signature"] for r in runs.values()}) == 1
    bench.results["round3_winner_cache"] = {"capacity": PROVISIONAL_CAPACITY, "outputs_identical": identical}
    bench.save()
    print(f"[select] round3 winner cache {PROVISIONAL_CAPACITY} identical={identical}", file=sys.stderr, flush=True)
    bench.teacher(ROUND3_WINNER.name, PROVISIONAL_CAPACITY)
    print("[written]", bench.output, file=sys.stderr, flush=True)
    return 0


class CacheMemory:
    """每個容量的實際 cache 記憶體：筆數 × cache-cost 量到的每筆成本，並附上 process RSS 的增量。"""

    def __init__(self, cost_file: Path = RESULTS / "round3_cache_cost.json") -> None:
        self.bytes_per_entry = float(json.loads(cost_file.read_text(encoding="utf-8"))["cost"]["bytes_per_entry"])

    def describe(self, runs: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
        out: dict[str, dict[str, object]] = {}
        for name, run in runs.items():
            cache = run["cache"] or {}  # type: ignore[assignment]
            entries = int(cache.get("entries", 0))  # type: ignore[union-attr]
            out[name] = {
                "entries": entries,
                "hit_rate": cache.get("hit_rate"),  # type: ignore[union-attr]
                "evictions": cache.get("evictions"),  # type: ignore[union-attr]
                "cache_mb_estimated": round(entries * self.bytes_per_entry / 2**20, 2),
                "rss_after_load_mb": run["rss_after_load_mb"],
                "rss_after_runs_mb": run["rss_after_runs_mb"],
                "rss_growth_mb": round(float(run["rss_after_runs_mb"]) - float(run["rss_after_load_mb"]), 1),  # type: ignore[arg-type]
            }
        return out


def main_final_cache(output: Path | None = None) -> int:
    """addendum：corpus winner 改變時，對 Round 3 winner 以同一規則重做 bounded cache selection。"""
    bench = QuietBenchmark(output or RESULTS / "round3_final_cache.json")
    bench.results["environment"] = environment()
    bench.results["protocol"] = {"system": ROUND3_WINNER.name, "warmup_cases": WARMUP_CASES, "repetitions": REPETITIONS, "cache_candidates": CACHE_CANDIDATES}
    bench.save()
    runs = {name: bench.decoder(ROUND3_WINNER.name, name) for name in CACHE_CANDIDATES}
    selection = CacheSelection().select(runs)
    selection["memory"] = CacheMemory().describe(runs)
    bench.results["cache_selection"] = selection
    bench.save()
    print(f"[select] cache -> {selection['selected']} identical={selection['outputs_identical']}", file=sys.stderr, flush=True)
    if selection["selected"]:
        bench.teacher(ROUND3_WINNER.name, selection["selected"])  # type: ignore[arg-type]
    print("[written]", bench.output, file=sys.stderr, flush=True)
    return 0


def run_cli(argv: Sequence[str]) -> int:
    commands: dict[str, Callable[..., int]] = {
        "cache-cost": main_cache_cost,
        "quiet": main_quiet,
        "quiet-winner": main_quiet_winner,
        "final-cache": main_final_cache,
        "child-decoder": main_child_decoder,
        "child-teacher": main_child_teacher,
    }
    if not argv or argv[0] not in commands:
        print(f"usage: python -m zaoseq_bopomofo.daily.round3 {{{','.join(commands)}}}", file=sys.stderr)
        return 2
    return commands[argv[0]](*argv[1:])


if __name__ == "__main__":
    sys.exit(run_cli(sys.argv[1:]))
