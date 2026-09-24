"""領域分開的 ExactReadingBenchmark 與功能詞錯誤分析。

    python -m zaoseq_bopomofo.evaluation.domains --output benchmarks/results/domain_latest.json

所有 system 都是 exact-only（typo correction 關閉）；本輪比較的是語言模型的組法，不是容錯。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.evaluation.decoding import DecodingItem, hand_items
from zaoseq_bopomofo.evaluation.metrics import LatencyStats, latency_stats

ROOT = Path(__file__).resolve().parents[3]
FUNCTION_WORD_GROUPS = ROOT / "data" / "builtin" / "function_word_groups.tsv"


@dataclass(frozen=True)
class TimedCall:
    """包住語言模型，累計 decoder 花在語言模型上的時間；只用於量測，不改變任何分數。"""

    model: object
    elapsed: list[float]

    def probability(self, token: str, history: str) -> float:
        return self.model.probability(token, history)  # type: ignore[attr-defined]

    def log10_probability(self, token: str, history: str) -> float:
        return self.model.log10_probability(token, history)  # type: ignore[attr-defined]

    def score(self, text: str, left_context: str = "") -> float:
        return self.model.score(text, left_context)  # type: ignore[attr-defined]

    def extend(self, history: str, char: str) -> tuple[float, str]:
        started = time.perf_counter()
        result = self.model.extend(history, char)  # type: ignore[attr-defined]
        self.elapsed[0] += time.perf_counter() - started
        return result


@dataclass(frozen=True)
class SetScore:
    items: int
    sentence_top1: float | None
    character_accuracy: float | None
    recall_at_5: float | None
    lexicon_oov_rate: float | None
    corpus_oov_rate: float | None
    decoder_latency: LatencyStats
    lm_latency: LatencyStats
    errors_by_group: dict[str, int]
    homophone_errors_outside_groups: int
    non_homophone_errors: int


def load_groups(path: Path = FUNCTION_WORD_GROUPS) -> dict[str, str]:
    """字 → 組名。一個字只能屬於一組，避免同一個錯誤被重複計數。"""
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, chars = line.split("\t")
        for ch in chars.split():
            if ch in mapping:
                raise ValueError(f"{ch} 同時屬於 {mapping[ch]} 與 {name}")
            mapping[ch] = name
    return mapping


def classify_errors(
    gold: str,
    predicted: str,
    readings: Sequence[str],
    groups: Mapping[str, str],
    homophones: Callable[[str, str], bool],
) -> list[str]:
    """逐字比較（長度相同時），每個錯字歸類為某個功能詞組、組外同音字、或非同音字。"""
    if len(gold) != len(predicted):
        return ["length_mismatch"]
    labels: list[str] = []
    for g, p, reading in zip(gold, predicted, readings):
        if g == p:
            continue
        group = groups.get(g)
        if group is not None and groups.get(p) == group:
            labels.append(group)
        elif homophones(p, reading):
            labels.append("homophone_other")
        else:
            labels.append("non_homophone")
    return labels


def domain_silver_items(corpus_dir: Path, annotator: object, per_domain: int = 200) -> dict[str, list[DecodingItem]]:
    """各領域 test split 的漢字片段（4–10 字），以規則標注讀音；依 sha256 抽樣，結果 deterministic。"""
    import re

    han_run = re.compile(r"[㐀-䶿一-鿿]+")
    pools: dict[str, list[tuple[str, DecodingItem]]] = {}
    for path in sorted(corpus_dir.glob("*/sentences.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["split"] != "test":
                continue
            for match in han_run.finditer(row["text"]):
                clause = match.group()
                if not 4 <= len(clause) <= 10:
                    continue
                result = annotator.annotate(clause)  # type: ignore[attr-defined]
                if not hasattr(result, "readings"):
                    continue
                key = hashlib.sha256(f"{row['source_id']}\x00{row['doc_id']}\x00{clause}".encode()).hexdigest()
                item = DecodingItem(
                    item_id=f"{row['source_id']}:{key[:12]}",
                    origin=f"silver:{row['domain']}",
                    left_context=row["text"][: match.start()],
                    readings=result.readings,
                    gold=clause,
                )
                pools.setdefault(row["domain"], []).append((key, item))
    return {domain: [item for _, item in sorted(pool, key=lambda p: p[0])[:per_domain]] for domain, pool in pools.items()}


def evaluate(
    decode: Callable[[tuple[str, ...], str], tuple[Candidate, ...]],
    items: Sequence[DecodingItem],
    lm_elapsed: list[float],
    lexicon_pairs: Callable[[str, str], bool],
    corpus_chars: frozenset[str],
    groups: Mapping[str, str],
) -> SetScore:
    decoder_ms: list[float] = []
    lm_ms: list[float] = []
    top1 = recall5 = chars = correct_chars = oov = corpus_oov = 0
    errors: Counter[str] = Counter()
    for item in items:
        lm_elapsed[0] = 0.0
        started = time.perf_counter()
        texts = [c.text for c in decode(item.readings, item.left_context)]
        decoder_ms.append((time.perf_counter() - started) * 1000.0)
        lm_ms.append(lm_elapsed[0] * 1000.0)
        top = texts[0] if texts else ""
        top1 += top == item.gold
        recall5 += item.gold in texts[:5]
        chars += len(item.gold)
        if len(top) == len(item.gold):
            correct_chars += sum(a == b for a, b in zip(top, item.gold))
        oov += sum(not lexicon_pairs(ch, r) for ch, r in zip(item.gold, item.readings))
        corpus_oov += sum(ch not in corpus_chars for ch in item.gold)
        errors.update(classify_errors(item.gold, top, item.readings, groups, lexicon_pairs))
    n = len(items)
    in_groups = {k: v for k, v in errors.items() if k not in ("homophone_other", "non_homophone", "length_mismatch")}
    return SetScore(
        items=n,
        sentence_top1=top1 / n if n else None,
        character_accuracy=correct_chars / chars if chars else None,
        recall_at_5=recall5 / n if n else None,
        lexicon_oov_rate=oov / chars if chars else None,
        corpus_oov_rate=corpus_oov / chars if chars else None,
        decoder_latency=latency_stats(decoder_ms),
        lm_latency=latency_stats(lm_ms),
        errors_by_group=dict(sorted(in_groups.items(), key=lambda kv: (-kv[1], kv[0]))),
        homophone_errors_outside_groups=errors["homophone_other"],
        non_homophone_errors=errors["non_homophone"] + errors["length_mismatch"],
    )


def format_report(report: dict[str, dict[str, SetScore]]) -> str:
    def f(value: float | None, digits: int = 3) -> str:
        return "n/a" if value is None else f"{value:.{digits}f}"

    sets = list(next(iter(report.values())))
    lines = [
        "| system | set | n | top-1 | char acc | R@5 | lexicon OOV | corpus OOV | decoder p50/p95 ms | LM p50/p95 ms |",
        "|" + "---|" * 10,
    ]
    for system, by_set in report.items():
        for name in sets:
            s = by_set[name]
            lines.append(
                f"| {system} | {name} | {s.items} | {f(s.sentence_top1)} | {f(s.character_accuracy)} | {f(s.recall_at_5)} "
                f"| {f(s.lexicon_oov_rate)} | {f(s.corpus_oov_rate)} "
                f"| {f(s.decoder_latency.p50_ms, 1)} / {f(s.decoder_latency.p95_ms, 1)} "
                f"| {f(s.lm_latency.p50_ms, 1)} / {f(s.lm_latency.p95_ms, 1)} |"
            )
    lines += ["", "### 錯字分類（第一名 vs gold，逐字）", "", "| system | set | 功能詞組錯誤 | 組外同音字 | 非同音 |", "|---|---|---|---|---|"]
    for system, by_set in report.items():
        for name in sets:
            s = by_set[name]
            grouped = "、".join(f"{k} {v}" for k, v in s.errors_by_group.items()) or "—"
            lines.append(f"| {system} | {name} | {grouped} | {s.homophone_errors_outside_groups} | {s.non_homophone_errors} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.evaluation.domains")
    parser.add_argument("--per-domain", type=int, default=200)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    from zaoseq_bopomofo.corpus.annotate import ReadingAnnotator
    from zaoseq_bopomofo.corpus.statistics import load_counts
    from zaoseq_bopomofo.decoding.generator import CandidateGenerator
    from zaoseq_bopomofo.decoding.pipeline import (
        DEFAULT_LM_DIR,
        DecoderSettings,
        LanguageModelConfig,
        build_tolerant_decoder,
        lexicon_characters,
        load_language_model,
    )
    from zaoseq_bopomofo.decoding.scoring import LinearScorer
    from zaoseq_bopomofo.lexicon.builder import read_builtin, read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS, load_lexicon

    loaded = load_lexicon()
    characters = lexicon_characters(loaded)
    annotator = ReadingAnnotator(read_char_readings(DEFAULT_CHAR_READINGS), read_builtin(DEFAULT_BUILTIN))
    silver = domain_silver_items(ROOT / "data" / "corpus", annotator, per_domain=args.per_domain)
    sets: dict[str, list[DecodingItem]] = {
        "everyday_dev": hand_items([ROOT / "benchmarks" / "dev" / "seeds.jsonl", ROOT / "benchmarks" / "sanity" / "seeds.jsonl"]),
        "legal": silver.get("legal", []),
        "faq_public_service": silver.get("government_faq", []) + silver.get("public_service", []),
        "press_release": silver.get("press_release", []),
    }
    sets["mixed"] = sets["legal"] + sets["faq_public_service"] + sets["press_release"]

    raw_counts, _, _ = load_counts(DEFAULT_LM_DIR / "raw")
    corpus_chars = frozenset(raw_counts.unigrams)
    groups = load_groups()
    lexicon = loaded.lexicon

    def lexicon_pair(char: str, reading: str) -> bool:
        return any(e.text == char for e in lexicon.lookup((reading,)))

    systems: dict[str, tuple[Callable[[tuple[str, ...], str], tuple[Candidate, ...]], list[float]]] = {}
    systems["lexicon (old baseline)"] = (CandidateGenerator(lexicon).candidates_for, [0.0])
    for label, config, lexical in (
        ("raw corpus", LanguageModelConfig.RAW, 0.0),
        ("raw corpus + lexicon", LanguageModelConfig.RAW, 1.0),
        ("capped corpus", LanguageModelConfig.CAPPED, 0.0),
        ("balanced corpus (general)", LanguageModelConfig.GENERAL, 0.0),
        ("balanced corpus + lexicon", LanguageModelConfig.GENERAL, 1.0),
    ):
        elapsed = [0.0]
        model = TimedCall(load_language_model(config, characters), elapsed)
        settings = DecoderSettings(scorer=LinearScorer(corpus_weight=1.0, lexical_weight=lexical))
        systems[label] = (build_tolerant_decoder(loaded, model, settings).candidates_for, elapsed)  # type: ignore[arg-type]

    report: dict[str, dict[str, SetScore]] = {}
    for name, (decode, elapsed) in systems.items():
        for item in sets["everyday_dev"][:3]:
            decode(item.readings, item.left_context)
        report[name] = {
            set_name: evaluate(decode, items, elapsed, lexicon_pair, corpus_chars, groups) for set_name, items in sets.items()
        }
        print(f"[done] {name}", file=sys.stderr)
    text = format_report(report)
    print(f"sets: { {k: len(v) for k, v in sets.items()} }\n")
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = {name: {s: asdict(v) for s, v in by_set.items()} for name, by_set in report.items()}
        args.output.write_text(json.dumps({"sets": {k: len(v) for k, v in sets.items()}, "report": payload}, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".md").write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
