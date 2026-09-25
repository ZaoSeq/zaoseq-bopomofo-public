from __future__ import annotations

import json

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

RESULTS = PROJECT_ROOT / "benchmarks" / "results"


def _row(name: str, m: dict) -> list[str]:  # type: ignore[type-arg]
    r = m["recall"]
    return [
        name,
        f"{r['@1']:.3f}",
        f"{r['@3']:.3f}",
        f"{r['@5']:.3f}",
        f"{r['@10']:.3f}",
        f"{m['recall_unlimited']:.3f}",
        f"{m['window_recall_top4_families']:.3f}",
        f"{m['mean_candidates']:.1f}",
        f"{m['latency_p50_ms']:.0f}",
        f"{m['latency_p95_ms']:.0f}",
    ]


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def main() -> int:
    raw = json.loads((RESULTS / "coverage_v1_raw.json").read_text(encoding="utf-8"))
    derived = json.loads((RESULTS / "coverage_v1_derived.json").read_text(encoding="utf-8"))
    teacher = json.loads((RESULTS / "coverage_v1_teacher.json").read_text(encoding="utf-8"))
    metrics = dict(raw["metrics"])
    for name, entry in derived["results"].items():
        metrics[name] = {k: entry[k] for k in ("coverage_dev", "gov_dev")}
    header = ["config", "R@1", "R@3", "R@5", "R@10", "unlimited", "top-4 family window", "candidates", "p50 ms", "p95 ms"]
    parts = ["# Coverage V1 results（DEV only）", ""]
    parts.append(f"V0 equivalence：{json.dumps(raw['v0_equivalence'], ensure_ascii=False)}")
    for set_name, title in (("coverage_dev", "Coverage-DEV（300）"), ("gov_dev", "GOV-DEV（400）")):
        parts += ["", f"## {title}", "", _table(header, [_row(n, m[set_name]) for n, m in metrics.items()])]
    v0 = raw["metrics"]["v0"]["coverage_dev"]
    parts += [
        "",
        "## V0 coverage indicators（Coverage-DEV）",
        "",
        f"- OOV rate {v0['oov_rate']:.3f}；reading coverage {v0['reading_coverage']:.3f}；multi-character word coverage {v0['word_coverage']:.3f}",
        f"- gold never generated {v0['never_generated']}（unreachable {v0['unreachable']}，beam-pruned {v0['beam_pruned']}）；"
        f"generated but outside top-5 {v0['generated_but_outside_top5']}",
    ]
    oracle = raw["oracle_lexicon_diagnostic"]
    parts += ["", "## Oracle lexicon diagnostic（upper bound, not adoptable）", "", oracle["note"], "", _table(header, [_row(f"v0 + {oracle['words_added']} gold words", oracle["coverage_dev"])])]
    for set_name in ("coverage_dev", "gov_dev"):
        tax = raw["taxonomy_v0"][set_name]
        rows = [[c, str(v["count"]), f"{v['share']:.3f}"] for c, v in tax["by_category"].items()]
        parts += ["", f"## Missing-candidate taxonomy, V0, {set_name}（{tax['missing_or_outside_top5_or_window']} cases）", "", _table(["category", "count", "share"], rows)]
        parts += ["", "stage: " + json.dumps(tax["by_stage"], ensure_ascii=False)]
    parts += ["", "## Timing breakdown（V0, Coverage-DEV, instrumented）", "", json.dumps(raw["timing_breakdown_v0"], ensure_ascii=False)]
    parts += ["", "## Frozen fine-tuned Laya on each candidate set（observation only）", "", "```json", json.dumps(teacher, ensure_ascii=False, indent=2), "```"]
    parts += ["", "## Derived-lexicon statistics", ""]
    parts += [f"- {n}: {json.dumps(e['stats'], ensure_ascii=False)}" for n, e in derived["results"].items()]
    (RESULTS / "coverage_v1.md").write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
    summary = {
        "role": "Coverage V1 (DEV only; v0.1 TEST not used)",
        "v0_equivalence": raw["v0_equivalence"],
        "metrics": metrics,
        "oracle_lexicon_diagnostic": oracle,
        "taxonomy_v0": raw["taxonomy_v0"],
        "timing_breakdown_v0": raw["timing_breakdown_v0"],
        "derived_lexicon": {n: {"stats": e["stats"], "lexicon_size": e["lexicon_size"]} for n, e in derived["results"].items()},
        "teacher_observation": teacher,
        "raw_files": ["benchmarks/results/coverage_v1_raw.json", "benchmarks/results/coverage_v1_derived.json", "benchmarks/results/coverage_v1_teacher.json"],
    }
    (RESULTS / "coverage_v1.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print((RESULTS / "coverage_v1.md").read_text(encoding="utf-8")[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
