from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

PROPER_NOUN = "#"
COLLOQUIAL = "~"


@dataclass(frozen=True)
class Word:
    text: str
    proper_noun: bool = False
    colloquial: bool = False


@dataclass(frozen=True)
class CoverageItem:
    item_id: str
    category: str
    left_context: str
    words: tuple[Word, ...]
    readings: tuple[str, ...]
    acceptable: tuple[str, ...]

    @property
    def text(self) -> str:
        return "".join(w.text for w in self.words)

    def word_spans(self) -> list[tuple[int, int, Word]]:
        spans: list[tuple[int, int, Word]] = []
        position = 0
        for word in self.words:
            spans.append((position, position + len(word.text), word))
            position += len(word.text)
        return spans

    def to_json(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "left_context": self.left_context,
            "text": self.text,
            "words": [asdict(w) for w in self.words],
            "readings": list(self.readings),
            "acceptable": list(self.acceptable),
        }

    @classmethod
    def from_json(cls, row: dict[str, object]) -> CoverageItem:
        return cls(
            item_id=str(row["item_id"]),
            category=str(row["category"]),
            left_context=str(row["left_context"]),
            words=tuple(Word(**w) for w in row["words"]),  # type: ignore[arg-type,union-attr]
            readings=tuple(row["readings"]),  # type: ignore[arg-type]
            acceptable=tuple(row["acceptable"]),  # type: ignore[arg-type]
        )


class SourceParser:
    """source.tsv：id、category、left_context、以空白分詞的文字（# 專有名詞、~ 口語詞）、讀音、以 | 分隔的其他可接受寫法。"""

    def parse(self, path: Path) -> list[CoverageItem]:
        items: list[CoverageItem] = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                raise ValueError(f"{path}:{number} 欄位不足")
            item_id, category, context, segmented, readings = parts[:5]
            words = tuple(self._word(t) for t in segmented.split())
            text = "".join(w.text for w in words)
            manual = [a for a in (parts[5].split("|") if len(parts) > 5 else []) if a]
            items.append(
                CoverageItem(
                    item_id=f"coverage:{item_id}",
                    category=category,
                    left_context=context,
                    words=words,
                    readings=tuple(readings.split()),
                    acceptable=tuple(dict.fromkeys([text, *manual])),
                )
            )
        duplicated = [k for k, v in Counter(i.item_id for i in items).items() if v > 1]
        if duplicated:
            raise ValueError(f"重複 id：{duplicated}")
        return items

    @staticmethod
    def _word(token: str) -> Word:
        return Word(
            token.rstrip(PROPER_NOUN + COLLOQUIAL),
            proper_noun=token.endswith(PROPER_NOUN),
            colloquial=token.endswith(COLLOQUIAL),
        )


class ReadingValidator:
    def issues(self, items: Sequence[CoverageItem]) -> list[str]:
        from zaoseq_bopomofo.evaluation.testsets import TestItem, _cns_readings, reading_issues

        cns = _cns_readings()
        problems: list[str] = []
        for item in items:
            probe = TestItem(item.item_id, "coverage-dev", item.left_context, item.text, item.readings, item.acceptable)
            problems += [f"{item.item_id} {item.text}: {issue}" for issue in reading_issues(probe, cns)]
        return problems


class LeakageChecker:
    """與語料全部 split、人工 DEV / sanity、v0.1 TEST（只作洩漏檢查）以及集合本身做近重複比對。"""

    def report(self, items: Sequence[CoverageItem]) -> dict[str, object]:
        from zaoseq_bopomofo.corpus.neardup import NearDuplicateIndex
        from zaoseq_bopomofo.evaluation.testsets import (
            EVERYDAY_SOURCE,
            GOV_FILE,
            NEAR_DUP_THRESHOLD,
            _hand_dev_sentences,
            _read_jsonl,
            leakage_index,
            read_everyday_source,
        )

        reference = [(i.item_id, i.left_context + i.text) for i in read_everyday_source(EVERYDAY_SOURCE)]
        reference += [(i.item_id, i.left_context + i.text) for i in _read_jsonl(GOV_FILE)]
        index = leakage_index(PROJECT_ROOT / "data" / "corpus", ("train", "dev", "test"), [*_hand_dev_sentences(), *reference])
        hits: dict[str, list[str]] = {}
        for item in items:
            matches = index.query(item.left_context + item.text)
            if matches:
                hits[item.item_id] = [f"{m.key} ({m.similarity:.2f})" for m in matches[:3]]
        internal = NearDuplicateIndex(threshold=NEAR_DUP_THRESHOLD)
        internal_hits: list[str] = []
        for item in items:
            internal_hits += [f"{item.item_id}~{m.key}" for m in internal.query(item.text)]
            internal.add(item.item_id, item.text)
        return {
            "method": f"char 4-gram MinHash LSH, Jaccard >= {NEAR_DUP_THRESHOLD}, Han-only normalized text",
            "checked_against": [
                "corpus splits train / dev / test",
                "benchmarks/dev + benchmarks/sanity",
                "v0.1 TEST-EVERYDAY and TEST-GOV (leakage check only)",
                "Coverage-DEV itself",
            ],
            "index_size": len(index),
            "external_hits": hits,
            "internal_hits": internal_hits,
        }


def read_items(path: Path) -> list[CoverageItem]:
    return [
        CoverageItem.from_json(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


class BuildError(RuntimeError):
    pass


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@dataclass(frozen=True)
class CoverageDataset:
    """一個 Coverage-DEV 版本。舊版本的檔案不修改；新版本以 `parent` 與 `changes` 記錄差異。"""

    version: str
    directory: Path
    parent: CoverageDataset | None = None
    changes: tuple[str, ...] = ()
    parser: SourceParser = field(default_factory=SourceParser, compare=False, repr=False)

    @property
    def source(self) -> Path:
        return self.directory / "source.tsv"

    @property
    def items_file(self) -> Path:
        return self.directory / "coverage_dev.jsonl"

    @property
    def manifest_file(self) -> Path:
        return self.directory / "MANIFEST.json"

    def read_source(self) -> list[CoverageItem]:
        return self.parser.parse(self.source)

    def load(self) -> list[CoverageItem]:
        return read_items(self.items_file)

    def verify(self) -> list[str]:
        manifest = json.loads(self.manifest_file.read_text(encoding="utf-8"))
        return [rel for rel, digest in manifest["files"].items() if file_hash(PROJECT_ROOT / rel) != digest]

    def changed_items(self) -> list[str]:
        if self.parent is None:
            return []
        before = {i.item_id: i.to_json() for i in self.parent.load()}
        return sorted(i.item_id for i in self.read_source() if before.get(i.item_id) != i.to_json())

    def build(self, validator: ReadingValidator | None = None, leakage: LeakageChecker | None = None) -> dict[str, object]:
        items = self.read_source()
        problems = (validator or ReadingValidator()).issues(items)
        if problems:
            raise BuildError("\n".join(problems))
        report = (leakage or LeakageChecker()).report(items)
        if report["external_hits"] or report["internal_hits"]:
            raise BuildError(json.dumps(report, ensure_ascii=False))
        header = f"# 造序注音 Coverage-DEV v{self.version}（DEV，可用於開發；由 source.tsv 產生）"
        lines = [header, *(json.dumps(i.to_json(), ensure_ascii=False) for i in items)]
        self.items_file.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        manifest = {
            "name": f"Coverage-DEV v{self.version}",
            "role": "DEV for candidate generation / decoder coverage; not a sealed test",
            "provenance": (
                "hand-written by the ZaoSeq Bopomofo project; not rewritten from v0.1 TEST sentences and not modelled on "
                "any decoder failure case; word segmentation and proper-noun / colloquial tags are manual"
            ),
            "license": "Apache-2.0 (project-authored)",
            "items": len(items),
            "characters": sum(len(i.text) for i in items),
            "with_left_context": sum(bool(i.left_context) for i in items),
            "by_category": dict(sorted(Counter(i.category for i in items).items())),
            "proper_noun_words": sum(w.proper_noun for i in items for w in i.words),
            "colloquial_words": sum(w.colloquial for i in items for w in i.words),
            "files": {
                self.source.relative_to(PROJECT_ROOT).as_posix(): file_hash(self.source),
                self.items_file.relative_to(PROJECT_ROOT).as_posix(): file_hash(self.items_file),
            },
            "leakage": report,
            "reading_convention": "MOE: 一／不 tone sandhi, particles neutral; CNS base tone when the neutral reading is absent",
        }
        if self.parent is not None:
            manifest["parent"] = {
                "version": self.parent.version,
                "manifest": self.parent.manifest_file.relative_to(PROJECT_ROOT).as_posix(),
                "source_sha256": file_hash(self.parent.source),
            }
            manifest["changes"] = list(self.changes)
            manifest["changed_items"] = self.changed_items()
        self.manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return manifest


V1_0 = CoverageDataset("1.0", PROJECT_ROOT / "benchmarks" / "coverage_v1")
V1_1 = CoverageDataset(
    "1.1",
    PROJECT_ROOT / "benchmarks" / "coverage_v1_1",
    parent=V1_0,
    changes=("cv19：「念」與「唸」在臺灣皆為通行寫法，新增「念」為可接受答案；v1.0 會把「念」判為錯誤。其餘 299 句不變。",),
)
DATASETS = {d.version: d for d in (V1_0, V1_1)}

COVERAGE_DIR = V1_0.directory
SOURCE = V1_0.source
ITEMS = V1_0.items_file
MANIFEST = V1_0.manifest_file


def read_source(path: Path = SOURCE) -> list[CoverageItem]:
    return SourceParser().parse(path)


def load_items(path: Path = ITEMS) -> list[CoverageItem]:
    return read_items(path)


def validate(items: Sequence[CoverageItem]) -> list[str]:
    return ReadingValidator().issues(items)


def _hash(path: Path) -> str:
    return file_hash(path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.coverage.dataset")
    parser.add_argument("command", choices=("validate", "build", "verify"))
    parser.add_argument("--version", default="1.1", choices=sorted(DATASETS))
    args = parser.parse_args(argv)
    dataset = DATASETS[args.version]
    if args.command == "validate":
        problems = ReadingValidator().issues(dataset.read_source())
        print("\n".join(problems) if problems else "ok")
        return 1 if problems else 0
    if args.command == "verify":
        changed = dataset.verify()
        print("\n".join(changed) if changed else "ok")
        return 1 if changed else 0
    try:
        manifest = dataset.build()
    except BuildError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(json.dumps({k: v for k, v in manifest.items() if k != "leakage"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
