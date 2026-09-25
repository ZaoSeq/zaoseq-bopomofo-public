from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from zaoseq_bopomofo.corpus.normalize import is_han

DERIVED_TIER = 101


@dataclass(frozen=True)
class DerivedConfig:
    name: str
    min_count: int
    min_pmi: float
    weight: float
    max_readings: int = 4


@dataclass
class DerivedStats:
    bigram_words: int
    trigram_words: int
    entries: int
    ambiguous_words: int
    skipped_too_many_readings: int


def extract_words(counts: object, config: DerivedConfig, known: set[str]) -> list[tuple[str, int]]:
    """2 字：c(xy) >= min_count 且 PMI >= min_pmi；3 字：兩種切法 (x|yz)、(xy|z) 的 PMI 都 >= min_pmi。"""
    unigrams = counts.unigrams  # type: ignore[attr-defined]
    bigrams = counts.bigrams  # type: ignore[attr-defined]
    trigrams = counts.trigrams  # type: ignore[attr-defined]
    total = sum(c for t, c in unigrams.items() if len(t) == 1 and is_han(t))

    def pmi(joint: int, left: int, right: int) -> float:
        return math.log2(joint * total / (left * right)) if left and right else -math.inf

    words: list[tuple[str, int]] = []
    for gram, count in bigrams.items():
        if count < config.min_count or len(gram) != 2 or not all(is_han(c) for c in gram) or gram in known:
            continue
        if pmi(count, unigrams.get(gram[0], 0), unigrams.get(gram[1], 0)) >= config.min_pmi:
            words.append((gram, count))
    for gram, count in trigrams.items():
        if count < config.min_count or len(gram) != 3 or not all(is_han(c) for c in gram) or gram in known:
            continue
        left = pmi(count, unigrams.get(gram[0], 0), bigrams.get(gram[1:], 0))
        right = pmi(count, bigrams.get(gram[:2], 0), unigrams.get(gram[2], 0))
        if min(left, right) >= config.min_pmi:
            words.append((gram, count))
    return sorted(words)


def build_derived_lexicon(config: DerivedConfig):  # type: ignore[no-untyped-def]
    """讀音：標注器能無歧義標注時只用一種；否則列出 CNS 組合（最多 max_readings 種，權重平分）。"""
    from zaoseq_bopomofo.corpus.annotate import ReadingAnnotator
    from zaoseq_bopomofo.corpus.statistics import load_counts
    from zaoseq_bopomofo.decoding.pipeline import DEFAULT_LM_DIR
    from zaoseq_bopomofo.lexicon.builder import BuiltinRow, FrequencyConfig, build_lexicon, read_builtin, read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

    char_rows = read_char_readings(DEFAULT_CHAR_READINGS)
    builtin = list(read_builtin(DEFAULT_BUILTIN))
    annotator = ReadingAnnotator(char_rows, builtin)
    readings_of: dict[str, list[str]] = {}
    for row in char_rows:
        if row.plane in (1, 2) and row.reading not in readings_of.setdefault(row.char, []):
            readings_of[row.char].append(row.reading)
    counts, _, _ = load_counts(DEFAULT_LM_DIR / "raw")
    words = extract_words(counts, config, {r.text for r in builtin})
    rows: list[BuiltinRow] = []
    existing = {(r.text, r.readings) for r in builtin}
    ambiguous = skipped = 0
    tiers: dict[int, float] = {}
    for word, _count in words:
        annotation = annotator.annotate(word)
        if hasattr(annotation, "readings"):
            options = [tuple(annotation.readings)]
        else:
            options = list(itertools.islice(itertools.product(*(readings_of.get(c, []) for c in word)), config.max_readings + 1))
            if not options or len(options) > config.max_readings:
                skipped += 1
                continue
            ambiguous += 1
        tier = DERIVED_TIER + len(options)
        tiers[tier] = config.weight / len(options)
        for readings in options:
            if (word, readings) in existing:
                continue
            existing.add((word, readings))
            rows.append(BuiltinRow(word, tier, readings, -1))
    frequency = FrequencyConfig(tier_weights={**FrequencyConfig().tier_weights, **tiers})
    report = build_lexicon(char_rows, [*builtin, *rows], frequency)
    if report.errors:
        raise ValueError(report.errors[:5])
    stats = DerivedStats(
        bigram_words=sum(len(w) == 2 for w, _ in words),
        trigram_words=sum(len(w) == 3 for w, _ in words),
        entries=len(rows),
        ambiguous_words=ambiguous,
        skipped_too_many_readings=skipped,
    )
    return report.lexicon, stats


GRID = (
    DerivedConfig("derived_c50_pmi3_w10", 50, 3.0, 10.0),
    DerivedConfig("derived_c20_pmi3_w10", 20, 3.0, 10.0),
    DerivedConfig("derived_c20_pmi5_w10", 20, 5.0, 10.0),
    DerivedConfig("derived_c50_pmi3_w3", 50, 3.0, 3.0),
)


def main(argv: list[str] | None = None) -> int:
    from zaoseq_bopomofo.coverage.analysis import (
        build_context,
        coverage_cases,
        gov_dev_cases,
        run_config,
        summarize,
        taxonomy,
    )
    from zaoseq_bopomofo.coverage.lattice import GenerationConfig

    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.coverage.derived_lexicon")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gov-per-domain", type=int, default=100)
    parser.add_argument("--beam", type=int, default=48)
    args = parser.parse_args(argv)

    ctx = build_context()
    sets = {"coverage_dev": coverage_cases(), "gov_dev": gov_dev_cases(args.gov_per_domain)}
    report: dict[str, object] = {"grid": [asdict(c) for c in GRID], "results": {}}
    for config in GRID:
        lexicon, stats = build_derived_lexicon(config)
        generation = GenerationConfig(config.name, beam=args.beam)
        entry: dict[str, object] = {"stats": asdict(stats), "lexicon_size": len(lexicon)}
        for set_name, cases in sets.items():
            results = run_config(ctx, generation, cases, lexicon=lexicon)
            metrics = summarize(results, cases, ctx)
            # 詞表覆蓋率以衍生詞表計算。
            words = hits = 0
            for case in cases:
                if case.item is None:
                    continue
                for start, end, word in case.item.word_spans():
                    if end - start >= 2:
                        words += 1
                        hits += any(e.text == word.text for e in lexicon.lookup(case.readings[start:end]))
            metrics.word_coverage = hits / words if words else None
            entry[set_name] = asdict(metrics)
            if set_name == "coverage_dev":
                derived_ctx = type(ctx)(lexicon, ctx.lm, ctx.scorer, ctx.variants, ctx.cns, ctx.plane)
                entry["taxonomy_coverage_dev"] = taxonomy(results, cases, derived_ctx)
        report["results"][config.name] = entry  # type: ignore[index]
        print(f"[done] {config.name} {asdict(stats)}", file=sys.stderr)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
