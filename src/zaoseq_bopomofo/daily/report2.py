from __future__ import annotations

import json

from zaoseq_bopomofo.daily.report import RESULTS, f3, table


class Round2Report:
    def __init__(self, raw: dict[str, object]) -> None:
        self.raw = raw
        self.results: dict[str, dict] = raw["results"]  # type: ignore[assignment]

    def config_rows(self, names: list[str]) -> str:
        final = self.raw["final"]["selected"]  # type: ignore[index]
        failed = self.raw["final"]["failed_gates"]  # type: ignore[index]
        rows = []
        for name in names:
            r = self.results[name]
            cov, gov = r["coverage_dev"]["metrics"], r["gov_dev"]["metrics"]
            vs = r["teacher_vs_v0_teacher"]
            gates = "not eligible" if not r["config"]["production_eligible"] else (", ".join(failed.get(name, [])) or "pass")
            rows.append(
                [
                    name + (" **(final)**" if name == final else ""),
                    gates,
                    f3(cov["top1"]),
                    f3(r["teacher"]["coverage_dev"]["teacher_top1"]),
                    f"{vs['coverage_dev']['wrong_to_correct']} / {vs['coverage_dev']['correct_to_wrong']}",
                    f3(cov["mrr"]),
                    f3(cov["recall"]["@3"]),
                    f3(cov["recall"]["@5"]),
                    f3(cov["recall"]["@10"]),
                    f3(cov["window_recall_top4_families"]),
                    f3(gov["top1"]),
                    f3(r["teacher"]["gov_dev"]["teacher_top1"]),
                    f"{vs['gov_dev']['wrong_to_correct']} / {vs['gov_dev']['correct_to_wrong']}",
                    r["lexicon"]["lexicon_entries"],
                    r["runtime"]["incremental_rss_mb"],
                    f"{cov['latency_p50_ms']:.0f} / {cov['latency_p95_ms']:.0f}",
                ]
            )
        header = [
            "config",
            "gates",
            "everyday base top1",
            "everyday teacher top1",
            "teacher vs V0 teacher W→C / C→W",
            "MRR",
            "R@3",
            "R@5",
            "R@10",
            "top-4 window",
            "GOV base top1",
            "GOV teacher top1",
            "GOV teacher vs V0 W→C / C→W",
            "lexicon entries",
            "+RSS MB",
            "decoder p50/p95 ms",
        ]
        return table(header, rows)

    def lexicon_rows(self) -> str:
        seen: dict[str, dict] = {}
        for r in self.results.values():
            info = r["lexicon"]
            if "recipe" in info and info["recipe"] not in seen:
                seen[info["recipe"]] = info
        rows = [
            [
                name,
                info["derived_words"],
                json.dumps(info["by_length"]),
                info["daily_supported_words"],
                info["government_only_words"],
                info["unsupported_readings"],
                info["false_competitors"],
                info["artifact_mb"],
                json.dumps(info["weight_distribution"]),
            ]
            for name, info in seen.items()
        ]
        header = ["recipe", "derived words", "by length", "daily-supported", "gov-only", "unsupported readings", "false competitors", "compact MB", "weights"]
        return table(header, rows)

    def rejections(self) -> str:
        seen: dict[str, dict] = {}
        for r in self.results.values():
            info = r["lexicon"]
            if "recipe" in info:
                seen.setdefault(info["recipe"], info["rejected"])
        return "\n".join(f"- {name}: {json.dumps(rej, ensure_ascii=False)}" for name, rej in seen.items())

    def stage_names(self, stage: str) -> list[str]:
        return [n for n, r in self.results.items() if r["config"]["stage"] == stage]

    def markdown(self) -> str:
        parts = [
            "# Daily Corpus Round 2 + Production Lexicon Cleanup（v0.2 development, DEV only）",
            "",
            f"Selection plan sha256 `{self.raw['plan_sha256']}`（benchmarks/frozen/v0.2_selection_plan.json，實驗前凍結）。",
            f"Production daily sources: {self.raw['production_daily_sources']}。v0.1 TEST 只用於語料排除。",
            "",
        ]
        for stage in ("reference", "1_reading", "2_extraction", "3_prior", "4_lm_weight", "diagnostic"):
            names = self.stage_names(stage)
            if not names:
                continue
            parts += [f"## {stage}", "", self.config_rows(names), ""]
            decision = self.raw["stages"].get(stage) if stage in self.raw["stages"] else None  # type: ignore[union-attr]
            if decision:
                parts += [
                    f"selected: **{decision['selected']}**; tie set {decision['tie_set']}; failed gates {json.dumps(decision['failed_gates'])}"
                    + (f"; fallback without gates: {decision['fallback_without_gates']}" if "fallback_without_gates" in decision else ""),
                    "",
                ]
        final = self.raw["final"]
        parts += [
            "## Final selection（PRECOMMITTED rule）",
            "",
            f"selected **{final['selected']}**; tie set {final['tie_set']}; eligible {len(final['eligible'])}",  # type: ignore[index]
            "",
            "## Lexicon variants",
            "",
            self.lexicon_rows(),
            "",
            "Rejections:",
            "",
            self.rejections(),
            "",
            "## Homophone order by prior（Coverage-DEV gold multi-character words that share a reading with another same-length entry）",
            "",
            table(["prior", "contested gold words", "gold ranked first"], [[k, v["contested_gold_words"], v["gold_ranked_first"]] for k, v in self.raw["gold_word_order_by_prior"].items()]),  # type: ignore[union-attr]
            "",
            "## Memory: representation comparison（fresh process each）",
            "",
        ]
        for key in ("lexicon_benchmark", "lexicon_benchmark_R0"):
            if key in self.raw:
                bench = self.raw[key]
                rows = [[mode, bench[mode]["load_s"], bench[mode]["incremental_rss_mb"], bench[mode]["lookup_us"]] for mode in ("frozen_lexicon_with_provenance_alive", "frozen_lexicon", "compact")]  # type: ignore[index]
                parts += [f"{key}: compact artifact {bench['artifact_mb']} MB, provenance JSON {bench['provenance_json_mb']} MB", "", table(["representation", "load s", "+RSS MB", "lookup µs"], rows), ""]  # type: ignore[index]
        eq = self.raw["dev_equivalence"]
        parts += [
            "## Exact equivalence（frozen Lexicon + uncached LM vs compact lexicon + cached LM）",
            "",
            f"{eq['config']}: {eq['cases']} DEV cases, mismatches {len(eq['mismatches'])}; latency {json.dumps(eq['latency_ms'])}",  # type: ignore[index]
            "",
        ]
        return "\n".join(parts) + "\n"

    def summary(self) -> dict[str, object]:
        results = {
            n: {
                "config": r["config"],
                "coverage_dev": r["coverage_dev"]["metrics"],
                "gov_dev": r["gov_dev"]["metrics"],
                "teacher": r["teacher"],
                "teacher_vs_v0_teacher": r["teacher_vs_v0_teacher"],
                "lexicon": r["lexicon"],
                "runtime": r["runtime"],
                "lm_cache": r["lm_cache"],
                "score": r["score"],
            }
            for n, r in self.results.items()
        }
        keep = [k for k in self.raw if k != "results"]
        return {"role": "Daily Corpus Round 2 (v0.2 development, DEV only)", **{k: self.raw[k] for k in keep}, "results": results, "raw_file": "benchmarks/results/daily_round2_raw.json"}


def main() -> int:
    raw = json.loads((RESULTS / "daily_round2_raw.json").read_text(encoding="utf-8"))
    report = Round2Report(raw)
    (RESULTS / "daily_round2.md").write_text(report.markdown(), encoding="utf-8", newline="\n")
    (RESULTS / "daily_round2.json").write_text(json.dumps(report.summary(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(report.markdown()[:3000])
    return 0
