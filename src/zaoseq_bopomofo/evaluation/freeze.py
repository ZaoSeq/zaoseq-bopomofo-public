"""Frozen configuration 紀錄：以內容 SHA-256 鎖定 baseline、模型與 TEST 所依賴的檔案。

    python -m zaoseq_bopomofo.evaluation.freeze write-v0
    python -m zaoseq_bopomofo.evaluation.freeze verify benchmarks/frozen/V0.json

雜湊的是「內容」：.gz 先解壓（gzip header 帶有時間戳），文字檔統一換行為 LF，
所以重新 build 相同內容或在不同作業系統 checkout 都得到相同雜湊。
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

FROZEN_DIR = PROJECT_ROOT / "benchmarks" / "frozen"
V0_RECORD = FROZEN_DIR / "V0.json"
FINAL_RECORD = FROZEN_DIR / "FINAL.json"

_TEXT_SUFFIXES = {".py", ".tsv", ".json", ".jsonl", ".md", ".txt"}

V0_SOURCES = (
    "src/zaoseq_bopomofo/corpus/domains.py",
    "src/zaoseq_bopomofo/corpus/statistics.py",
    "src/zaoseq_bopomofo/decoding/candidate.py",
    "src/zaoseq_bopomofo/decoding/errors.py",
    "src/zaoseq_bopomofo/decoding/family.py",
    "src/zaoseq_bopomofo/decoding/lattice.py",
    "src/zaoseq_bopomofo/decoding/scoring.py",
    "src/zaoseq_bopomofo/decoding/tolerant.py",
    "src/zaoseq_bopomofo/lexicon/builder.py",
    "src/zaoseq_bopomofo/lexicon/lexicon.py",
    "src/zaoseq_bopomofo/lexicon/loader.py",
    "src/zaoseq_bopomofo/ranking/corpus.py",
)
V0_DATA = (
    "data/builtin/lexicon.tsv",
    "data/builtin/variants.tsv",
    "data/cns11643/cns_char_readings.tsv",
)
# 語料衍生檔不進 git（由 `python -m zaoseq_bopomofo.corpus build` 重建）；缺檔時 verify 會標示為 missing。
V0_DERIVED_GLOBS = ("data/corpus/lm/raw/*.gz", "data/corpus/lm/domain/*/*.gz")


def content_hash(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    elif path.suffix in _TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def hash_files(paths: list[str]) -> dict[str, str]:
    return {p: content_hash(PROJECT_ROOT / p) for p in sorted(paths)}


def v0_paths() -> tuple[list[str], list[str]]:
    derived = sorted(
        p.relative_to(PROJECT_ROOT).as_posix() for pattern in V0_DERIVED_GLOBS for p in PROJECT_ROOT.glob(pattern)
    )
    return [*V0_SOURCES, *V0_DATA], derived


def v0_settings_json() -> dict[str, object]:
    from zaoseq_bopomofo.corpus.domains import GENERAL_WEIGHTS
    from zaoseq_bopomofo.decoding.pipeline import V0_SETTINGS

    return {
        "language_model": "GeneralCorpusLanguageModel",
        "domain_weights": {d.value: w for d, w in sorted(GENERAL_WEIGHTS.weights.items(), key=lambda kv: kv[0].value)},
        "scorer": asdict(V0_SETTINGS.scorer),
        "lattice": asdict(V0_SETTINGS.lattice),
        "typo_correction": V0_SETTINGS.policy.enabled,
        "candidate_family": "data/builtin/variants.tsv",
    }


def write_v0(path: Path = V0_RECORD) -> dict[str, object]:
    tracked, derived = v0_paths()
    if not derived:
        raise FileNotFoundError("找不到語料 LM 檔；先執行 `python -m zaoseq_bopomofo.corpus build`")
    record = {
        "name": "V0",
        "frozen_at": "2026-09-23",
        "statement": (
            "Frozen V0 baseline: licensed government corpus pipeline, GeneralCorpusLanguageModel, builtin lexicon, "
            "CandidateFamily, exact decoder, typo correction OFF. Not modified based on any later TEST result. "
            "DEV results have influenced architecture decisions and are not final test results."
        ),
        "settings": v0_settings_json(),
        "tracked_files": hash_files(tracked),
        "derived_files": hash_files(derived),
        "dev_reports": [
            "benchmarks/results/domain_latest.md",
            "benchmarks/results/dev_invariant_fix.json",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return record


def verify(path: Path) -> dict[str, list[str]]:
    """回傳 {'changed': [...], 'missing': [...]}；兩者都空才代表與紀錄一致。"""
    record = json.loads(path.read_text(encoding="utf-8"))
    changed: list[str] = []
    missing: list[str] = []
    for section in ("tracked_files", "derived_files", "files"):
        for rel, expected in record.get(section, {}).items():
            target = PROJECT_ROOT / rel
            if not target.exists():
                missing.append(rel)
            elif content_hash(target) != expected:
                changed.append(rel)
    return {"changed": changed, "missing": missing}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.evaluation.freeze")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write-v0")
    check = sub.add_parser("verify")
    check.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    if args.command == "write-v0":
        record = write_v0()
        print(f"wrote {V0_RECORD} ({len(record['tracked_files'])} tracked, {len(record['derived_files'])} derived)")  # type: ignore[arg-type]
        return 0
    result = verify(args.record)
    for key, items in result.items():
        for item in items:
            print(f"{key}: {item}")
    return 1 if result["changed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
