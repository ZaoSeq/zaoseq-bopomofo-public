from __future__ import annotations

import argparse
import json
import sys


def audit() -> int:
    from zaoseq_bopomofo.daily.sources import LicenseGate, SourceRegistry

    gate = LicenseGate()
    for source in SourceRegistry.load():
        problems = gate.problems(source)
        verdict = "importable" if not problems else "blocked: " + "；".join(problems[:3])
        print(f"{source.status.value:9} {source.source_id:30} {verdict}")
    return 0


def script_classifier():  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.daily.script import ScriptClassifier, read_simplified_characters
    from zaoseq_bopomofo.daily.sources import LicenseGate, RawFiles, SourceRegistry
    from zaoseq_bopomofo.lexicon.builder import read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_CHAR_READINGS

    unihan = SourceRegistry.load()["unihan_variants"]
    LicenseGate().require(unihan)
    simplified = read_simplified_characters(RawFiles().verify(unihan)["Unihan.zip"])
    standard = {r.char for r in read_char_readings(DEFAULT_CHAR_READINGS) if r.plane in (1, 2)}
    return ScriptClassifier(standard, simplified)


def build() -> int:
    from zaoseq_bopomofo.daily.corpus import DailyCorpusBuilder, DailyCorpusWriter
    from zaoseq_bopomofo.daily.guard import EvaluationGuard, default_references
    from zaoseq_bopomofo.daily.importers import IMPORTERS
    from zaoseq_bopomofo.daily.quality import SentenceInspector
    from zaoseq_bopomofo.daily.sources import SourceRegistry
    from zaoseq_bopomofo.evaluation.testsets import NEAR_DUP_THRESHOLD

    registry = SourceRegistry.load()
    guard = EvaluationGuard(default_references(), NEAR_DUP_THRESHOLD)
    builder = DailyCorpusBuilder([cls(registry) for cls in IMPORTERS], SentenceInspector(script_classifier()), guard)
    sentences, stats = builder.build()
    manifest = DailyCorpusWriter(registry).write(sentences, stats, guard.sizes)
    summary = {
        k: {f: v[f] for f in ("documents", "sentences_seen", "sentences_kept", "sentences_dropped", "splits")}
        for k, v in manifest["quality"].items()  # type: ignore[union-attr]
    }
    print(json.dumps({"quality": summary, "language_models": manifest["language_models"]}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.daily")
    parser.add_argument("command", choices=("audit", "build", "experiments", "ablation", "round2", "stage5", "compare", "report", "report2"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    if args.command == "audit":
        return audit()
    if args.command == "build":
        return build()
    if args.command == "experiments":
        from zaoseq_bopomofo.daily.experiments import main as run

        return run(args.output)
    if args.command == "round2":
        from zaoseq_bopomofo.daily.round2 import main as round2

        return round2(args.output)
    if args.command == "compare":
        from zaoseq_bopomofo.daily.corpus_compare import main as compare

        return compare(args.output)
    if args.command == "stage5":
        from zaoseq_bopomofo.daily.corpus_ablation import main as stage5

        return stage5(args.output)
    if args.command == "ablation":
        from zaoseq_bopomofo.daily.experiments import ablation

        return ablation(args.output)
    if args.command == "report2":
        from zaoseq_bopomofo.daily.report2 import main as report2

        return report2()
    from zaoseq_bopomofo.daily.report import main as report

    return report()


if __name__ == "__main__":
    sys.exit(main())
