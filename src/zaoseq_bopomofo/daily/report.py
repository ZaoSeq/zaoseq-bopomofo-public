from __future__ import annotations

import json
from collections.abc import Sequence

from zaoseq_bopomofo.daily.corpus import CORPUS_DIR
from zaoseq_bopomofo.daily.sources import SourceRegistry
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

RESULTS = PROJECT_ROOT / "benchmarks" / "results"
LABELS = {
    "A_gov": "A gov only (V0)",
    "B_daily": "B daily only",
    "G_oasst1_zh_prompter": "G gov + OASST1 prompter (DEV only)",
    "H_daily_all": "H gov + Tatoeba + OASST1 (DEV only)",
}


def table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def f3(value: object) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) and value is not None else "–"


class DailyReport:
    def __init__(self, raw: dict[str, object]) -> None:
        self.raw = raw
        self.results: dict[str, dict] = raw["results"]  # type: ignore[assignment]
        self.c_selected = raw["c_selection"]["selected"]  # type: ignore[index]
        self.e_selected = raw["e_selection"]["selected"]  # type: ignore[index]

    def label(self, name: str) -> str:
        if name == self.c_selected:
            return f"C {name[2:]} (selected; = D = F)"
        if name.startswith("C_"):
            return f"C {name[2:]}"
        if name.startswith("E_"):
            return f"E {name[2:]}" + (" (selected)" if name == self.e_selected else "")
        return LABELS.get(name, name)

    def names(self) -> list[str]:
        return list(self.results)

    def teacher_top1(self, name: str, set_name: str) -> str:
        row = self.raw["teacher_observation"].get(name, {}).get(set_name)  # type: ignore[union-attr]
        return f3(row["teacher_top1"]) if row else "–"

    def tradeoff(self) -> str:
        rows = []
        for name in self.names():
            r = self.results[name]
            cov, gov, res = r["coverage_dev"]["metrics"], r["gov_dev"]["metrics"], r["resources"]
            rows.append(
                [
                    self.label(name),
                    f3(cov["top1"]),
                    f3(cov["recall"]["@5"]),
                    f3(cov["window_recall_top4_families"]),
                    self.teacher_top1(name, "coverage_dev"),
                    f3(gov["top1"]),
                    self.teacher_top1(name, "gov_dev"),
                    res["lexicon_entries"],
                    res["total_lm_mb"],
                    f"{cov['latency_p50_ms']:.0f} / {cov['latency_p95_ms']:.0f}",
                ]
            )
        header = ["config", "everyday top1", "everyday R@5", "top-4 window", "teacher everyday top1", "GOV top1", "teacher GOV top1", "lexicon entries", "LM MB", "decoder p50/p95 ms"]
        return table(header, rows)

    def metrics(self, set_name: str) -> str:
        rows = []
        for name in self.names():
            m = self.results[name][set_name]["metrics"]
            rows.append(
                [
                    self.label(name),
                    *(f3(m["recall"][k]) for k in ("@1", "@3", "@5", "@10")),
                    f3(m["recall_unlimited"]),
                    f3(m["window_recall_top4_families"]),
                    f3(m["word_coverage"]),
                    f3(m["character_accuracy"]),
                    f3(m["mrr"]),
                ]
            )
        return table(["config", "R@1 (top1)", "R@3", "R@5", "R@10", "unlimited", "top-4 window", "word coverage", "char acc", "MRR"], rows)

    def resources(self) -> str:
        rows = []
        for name in self.names():
            res = self.results[name]["resources"]
            cov, gov = self.results[name]["coverage_dev"]["metrics"], self.results[name]["gov_dev"]["metrics"]
            rows.append(
                [
                    self.label(name),
                    res["gov_lm_mb"],
                    res["daily_lm_mb"],
                    res["lexicon_entries"],
                    res["lm_load_s"],
                    res["rss_delta_mb"],
                    res["extend_us"],
                    f"{cov['latency_p50_ms']:.0f} / {cov['latency_p95_ms']:.0f}",
                    f"{gov['latency_p50_ms']:.0f} / {gov['latency_p95_ms']:.0f}",
                ]
            )
        header = ["config", "gov LM MB", "daily LM MB", "lexicon entries", "extra load s", "RSS delta MB", "LM extend µs", "Coverage p50/p95 ms", "GOV p50/p95 ms"]
        return table(header, rows)

    def teacher(self) -> str:
        rows = []
        for name, sets in self.raw["teacher_observation"].items():  # type: ignore[union-attr]
            for set_name, row in sets.items():
                vs_order = row["teacher_vs_decoder_order"]
                vs_a = row.get("teacher_vs_A_teacher", {})
                rows.append(
                    [
                        self.label(name),
                        set_name,
                        f3(row["decoder_top1"]),
                        f3(row["teacher_top1"]),
                        f"{vs_order['wrong_to_correct']} / {vs_order['correct_to_wrong']}",
                        f"{vs_a['wrong_to_correct']} / {vs_a['correct_to_wrong']} (p={vs_a['mcnemar_p']})" if vs_a else "–",
                        f"{row['latency_p50_ms']} / {row['latency_p95_ms']}",
                        row["fallbacks"],
                    ]
                )
        header = ["config", "set", "decoder top1", "teacher top1", "teacher vs decoder: W→C / C→W", "teacher vs A teacher: W→C / C→W", "teacher p50/p95 ms", "fallbacks"]
        return table(header, rows)

    def window(self) -> str:
        rows = []
        for name, sets in self.raw["teacher_window_diagnostic"].items():  # type: ignore[union-attr]
            for set_name, ks in sets.items():
                for k, r in ks.items():
                    rows.append(
                        [
                            self.label(name),
                            set_name,
                            k,
                            f3(r["window_coverage"]),
                            f3(r["teacher_top1"]),
                            f3(r["same_pick_as_K4"]),
                            f"{r['vs_K4']['wrong_to_correct']} / {r['vs_K4']['correct_to_wrong']}",
                            f"{r['latency_p50_ms']} / {r['latency_p95_ms']}",
                            r["gpu_peak_mb"],
                        ]
                    )
        header = ["config", "set", "K", "gold in window", "teacher top1", "same pick as K=4", "vs K=4: W→C / C→W", "p50/p95 ms", "GPU peak MB"]
        return table(header, rows)

    def lexicon(self) -> str:
        rows = []
        for name, s in self.raw["lexicon_variants"].items():  # type: ignore[union-attr]
            rows.append(
                [
                    name,
                    s["policy"]["estimator"],
                    s["policy"]["min_documents"],
                    s["policy"]["min_pmi"],
                    s["considered"],
                    s["eligible_words"],
                    json.dumps(s["by_length"]),
                    s["daily_only_words"],
                    s["government_only_words"],
                    s["weight_median"],
                ]
            )
        header = ["variant", "estimator", "min docs", "min PMI", "n-grams ≥2/M", "eligible", "by length", "daily-only", "gov-only", "median weight"]
        return table(header, rows)

    def corpus(self) -> str:
        manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
        rows = []
        for source_id, q in manifest["quality"].items():
            rows.append(
                [
                    source_id,
                    q["documents"],
                    q["sentences_seen"],
                    q["sentences_kept"],
                    q["han_chars_kept"],
                    f3(q["traditional_ratio_mean_all_seen"]),
                    f3(q["simplified_rate"]),
                    f3(q["han_ratio_mean_kept"]),
                    q["length_han_chars"]["median"],
                    q["source_concentration"]["top10_share"],
                    json.dumps(q["splits"]),
                ]
            )
        header = ["source", "documents", "sentences seen", "kept", "Han chars kept", "traditional ratio", "simplified rate", "Han ratio", "median length", "top-10 contributor share", "splits"]
        drops = {s: q["sentences_dropped"] | {f"doc:{k}": v for k, v in q["documents_dropped"].items()} for s, q in manifest["quality"].items()}
        overlap = {s: q["eval_overlap_by_reference"] for s, q in manifest["quality"].items()}
        lm = manifest["language_models"]
        return "\n\n".join(
            [
                table(header, rows),
                "Drops: " + json.dumps(drops, ensure_ascii=False),
                "Evaluation-set exclusions: " + json.dumps(overlap, ensure_ascii=False),
                "Language models (train split): " + json.dumps(lm, ensure_ascii=False),
            ]
        )

    def sources(self) -> str:
        rows = [[s.source_id, s.status.value, s.approval_scope.value, s.license_name, s.training_use, s.redistribution] for s in SourceRegistry.load()]
        return table(["source", "status", "scope", "license", "training use", "redistribution"], rows)

    @staticmethod
    def ablation() -> list[str]:
        path = RESULTS / "daily_v1_ablation.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        flat = data["E_pmi_flat10"]
        rows = [
            [
                "E pmi, every derived word weight 10",
                f3(flat[s]["metrics"]["recall"]["@1"]),
                f3(flat[s]["metrics"]["recall"]["@5"]),
                f3(flat[s]["metrics"]["window_recall_top4_families"]),
            ]
            for s in ("coverage_dev", "gov_dev")
        ]
        return [
            "## Frequency weights vs flat weights（diagnostic）",
            "",
            data["note"],
            "",
            table(["config", "R@1", "R@5", "top-4 window"], [[r[0] + f" ({s})", *r[1:]] for r, s in zip(rows, ("Coverage-DEV", "GOV-DEV"))]),
            "",
            "Fresh-process memory: " + json.dumps(data["resource_snapshot_fresh_process"]),
            "",
        ]

    def markdown(self) -> str:
        homophone = self.raw["homophone"]
        parts = [
            "# Daily Corpus V1 results（v0.2 development, DEV only）",
            "",
            "Coverage-DEV v1.1（300）與 GOV-DEV（400）。v0.1 TEST 只用於語料排除，未用於任何選擇。",
            "",
            f"Selection rule: {self.raw['selection_rule']}",
            "",
            f"- C selection: {json.dumps(self.raw['c_selection'], ensure_ascii=False)}",
            f"- E selection: {json.dumps(self.raw['e_selection'], ensure_ascii=False)}",
            "",
            "## Trade-off",
            "",
            self.tradeoff(),
            "",
            "## Coverage-DEV v1.1",
            "",
            self.metrics("coverage_dev"),
            "",
            "## GOV-DEV",
            "",
            self.metrics("gov_dev"),
            "",
            "## Language-model cross-entropy（bits / char）",
            "",
            table(["config", "daily DEV split", "GOV-DEV split (2000 sentences)"], [[self.label(n), v["daily_dev_bits_per_char"], v["gov_dev_bits_per_char"]] for n, v in self.raw["perplexity"].items()]),  # type: ignore[union-attr]
            "",
            "## Frequency-aware derived lexicon",
            "",
            self.lexicon(),
            "",
            *self.ablation(),
            "## Homophone competitors（selected E）",
            "",
            f"- derived readings with an existing same-length competitor: {homophone['competitors']['derived_readings_with_competitor']}; "
            f"derived weight above best competitor: {homophone['competitors']['derived_outweighs_best_competitor']}",
            f"- Coverage-DEV change vs selected C: {json.dumps({k: v for k, v in homophone['coverage_dev'].items() if k != 'correct_to_wrong_examples'})}",
            f"- GOV-DEV change vs selected C: {json.dumps({k: v for k, v in homophone['gov_dev'].items() if k != 'correct_to_wrong_examples'})}",
            "",
            "## Frozen fine-tuned Laya（observation only）",
            "",
            self.teacher(),
            "",
            "## Teacher window diagnostic（not adopted; production stays K=4）",
            "",
            self.window(),
            "",
            "## Latency / RAM / artifact size",
            "",
            f"Load: {json.dumps(self.raw['load'])}; lexicon statistics build {self.raw['lexicon_statistics_build_s']} s",
            "",
            self.resources(),
            "",
            "## Corpus V1",
            "",
            self.corpus(),
            "",
            "## Sources",
            "",
            self.sources(),
        ]
        return "\n".join(parts) + "\n"

    def summary(self) -> dict[str, object]:
        def strip(result: dict) -> dict:  # type: ignore[type-arg]
            return {k: ({"metrics": v["metrics"]} if isinstance(v, dict) and "metrics" in v else v) for k, v in result.items()}

        teacher = {
            n: {s: {k: v for k, v in row.items() if k != "correct"} for s, row in sets.items()}
            for n, sets in self.raw["teacher_observation"].items()  # type: ignore[union-attr]
        }
        keep = ("selection_rule", "c_selection", "e_selection", "load", "lexicon_statistics_build_s", "lexicon_variants", "perplexity", "teacher_window_diagnostic")
        return {
            "role": "Daily Corpus V1 (v0.2 development, DEV only; v0.1 TEST used only for corpus exclusion)",
            **{k: self.raw[k] for k in keep},
            "homophone": self.raw["homophone"],
            "teacher_observation": teacher,
            "results": {n: strip(r) for n, r in self.results.items()},
            "raw_file": "benchmarks/results/daily_v1_raw.json",
            "ablation_file": "benchmarks/results/daily_v1_ablation.json",
        }


def main() -> int:
    raw = json.loads((RESULTS / "daily_v1_raw.json").read_text(encoding="utf-8"))
    report = DailyReport(raw)
    (RESULTS / "daily_v1.md").write_text(report.markdown(), encoding="utf-8", newline="\n")
    (RESULTS / "daily_v1.json").write_text(json.dumps(report.summary(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(report.tradeoff())
    return 0
