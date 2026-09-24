"""Untouched TEST：TEST-GOV、TEST-EVERYDAY、TEST-TYPO 的建立、封存與存取閘門。

    python -m zaoseq_bopomofo.evaluation.testsets review     # 人工檢查注音（不跑 decoder）
    python -m zaoseq_bopomofo.evaluation.testsets build      # 產生三份 TEST 與 MANIFEST.json（只做一次）
    python -m zaoseq_bopomofo.evaluation.testsets check      # 格式、雜湊與讀音合法性；不計算任何準確率

TEST 在最終設定 freeze 之前不得拿來評估：`load_sealed()` 會要求一份 FINAL freeze 紀錄，
且紀錄中的檔案雜湊都必須與現況一致。模型選擇只能用 TRAIN + DEV。

語料 split 的評估角色：
- corpus split "test"：第四輪 domain benchmark 已用它做決策，降級為 GOV-DEV。
- corpus split "dev"：從未被任何評估讀過，封存為 TEST-GOV。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

TEST_DIR = PROJECT_ROOT / "benchmarks" / "test"
MANIFEST = TEST_DIR / "MANIFEST.json"
EVERYDAY_SOURCE = TEST_DIR / "everyday_source.tsv"
EVERYDAY_FILE = TEST_DIR / "everyday.jsonl"
GOV_FILE = TEST_DIR / "gov.jsonl"
TYPO_FILE = TEST_DIR / "typo.jsonl"
FINAL_RECORD = PROJECT_ROOT / "benchmarks" / "frozen" / "FINAL.json"

GOV_DEV_SPLIT = "test"
TEST_GOV_SPLIT = "dev"
GOV_DOMAINS = ("legal", "government_faq", "public_service", "press_release")
GOV_PER_DOMAIN = 200
NEAR_DUP_THRESHOLD = 0.6
# 全句一致的替換：沒有性別線索時「你／妳」都正確，「週／周」在臺灣通行；其餘寫法變體由 CandidateFamily 處理。
GLOBAL_ALTERNATIVES = (("你", "妳"), ("週", "周"))
_HAN_RUN = re.compile(r"[㐀-䶿一-鿿]+")


class SealedTestError(RuntimeError):
    pass


@dataclass(frozen=True)
class TestItem:
    item_id: str
    group: str
    left_context: str
    text: str
    readings: tuple[str, ...]
    acceptable: tuple[str, ...]
    category: str = ""
    source_id: str = ""
    doc_id: str = ""
    noisy_readings: tuple[str, ...] = ()
    noise_kind: str = ""
    noise_position: int = -1

    def to_json(self) -> dict[str, object]:
        row = asdict(self)
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in row.items() if v not in ("", (), -1)}

    @classmethod
    def from_json(cls, row: Mapping[str, object]) -> TestItem:
        values = dict(row)
        values.setdefault("left_context", "")
        for key in ("readings", "acceptable", "noisy_readings"):
            if key in values:
                values[key] = tuple(values[key])  # type: ignore[arg-type]
        return cls(**values)  # type: ignore[arg-type]


# ---------------------------------------------------------------- everyday


def _alternatives(text: str, manual: Iterable[str]) -> tuple[str, ...]:
    options = [text]
    for old, new in GLOBAL_ALTERNATIVES:
        options += [o.replace(old, new) for o in options if old in o]
    options += [m for m in manual if m]
    return tuple(dict.fromkeys(options))


def read_everyday_source(path: Path = EVERYDAY_SOURCE) -> list[TestItem]:
    items: list[TestItem] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            raise ValueError(f"{path}:{number} 欄位不足")
        item_id, category, context, text, readings = parts[:5]
        manual = parts[5].split("|") if len(parts) > 5 else []
        items.append(
            TestItem(
                item_id=f"everyday:{item_id}",
                group="test-everyday",
                category=category,
                left_context=context,
                text=text,
                readings=tuple(readings.split()),
                acceptable=_alternatives(text, manual),
            )
        )
    ids = Counter(i.item_id for i in items)
    duplicated = [k for k, v in ids.items() if v > 1]
    if duplicated:
        raise ValueError(f"重複 id：{duplicated}")
    return items


def reading_issues(item: TestItem, cns: Mapping[str, set[str]]) -> list[str]:
    """字數與音節數一致、每個音節可解析、且 (字, 讀音) 存在於 CNS11643。"""
    from zaoseq_bopomofo.phonetics.parser import InvalidBopomofoError, parse_reading

    issues: list[str] = []
    if not _HAN_RUN.fullmatch(item.text):
        issues.append("text 含非漢字")
    if len(item.text) != len(item.readings):
        return issues + [f"字數 {len(item.text)} ≠ 音節數 {len(item.readings)}"]
    for char, reading in zip(item.text, item.readings):
        try:
            parse_reading(reading)
        except InvalidBopomofoError:
            issues.append(f"{char} {reading}: 無法解析")
            continue
        if reading not in cns.get(char, set()):
            issues.append(f"{char} {reading}: CNS 讀音為 {sorted(cns.get(char, set()))}")
    for alternative in item.acceptable:
        if len(alternative) != len(item.text):
            issues.append(f"alternative {alternative} 長度不同")
    return issues


def _cns_readings() -> dict[str, set[str]]:
    from zaoseq_bopomofo.lexicon.builder import read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_CHAR_READINGS

    cns: dict[str, set[str]] = {}
    for row in read_char_readings(DEFAULT_CHAR_READINGS):
        cns.setdefault(row.char, set()).add(row.reading)
    return cns


def _annotator():  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.corpus.annotate import ReadingAnnotator
    from zaoseq_bopomofo.lexicon.builder import read_builtin, read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_BUILTIN, DEFAULT_CHAR_READINGS

    return ReadingAnnotator(read_char_readings(DEFAULT_CHAR_READINGS), read_builtin(DEFAULT_BUILTIN))


def review_everyday(items: Sequence[TestItem]) -> list[str]:
    """人工檢查用的清單：CNS 不合法的讀音，以及與規則標注器（不是 decoder）不一致的讀音。"""
    cns = _cns_readings()
    annotator = _annotator()
    lines: list[str] = []
    for item in items:
        for issue in reading_issues(item, cns):
            lines.append(f"ILLEGAL {item.item_id} {item.text}: {issue}")
        annotation = annotator.annotate(item.text)
        if hasattr(annotation, "readings") and tuple(annotation.readings) != item.readings:
            diffs = [
                f"{c} {mine}≠{rule}" for c, mine, rule in zip(item.text, item.readings, annotation.readings) if mine != rule
            ]
            lines.append(f"DIFF {item.item_id} {item.text}: {'、'.join(diffs)}")
    return lines


# ---------------------------------------------------------------- leakage


def _corpus_rows(corpus_dir: Path) -> Iterable[dict[str, str]]:
    for path in sorted(corpus_dir.glob("*/sentences.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            yield json.loads(line)


def _hand_dev_sentences() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for name in ("dev", "sanity"):
        path = PROJECT_ROOT / "benchmarks" / name / "seeds.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            seed = json.loads(line)
            rows.append((f"{name}:{seed['id']}", seed["context"] + seed["target"] + seed["suffix"]))
    return rows


def leakage_index(corpus_dir: Path, splits: Sequence[str], extra: Iterable[tuple[str, str]] = ()):  # type: ignore[no-untyped-def]
    from zaoseq_bopomofo.corpus.neardup import NearDuplicateIndex

    index = NearDuplicateIndex(threshold=NEAR_DUP_THRESHOLD)
    for row in _corpus_rows(corpus_dir):
        if row["split"] in splits:
            index.add(f"{row['split']}:{row['source_id']}:{row['doc_id']}", row["text"])
    index.add_all(extra)
    return index


# ---------------------------------------------------------------- gov


def build_gov(corpus_dir: Path, annotator: object, index: object, per_domain: int = GOV_PER_DOMAIN) -> tuple[list[TestItem], dict[str, Counter[str]]]:
    """TEST-GOV：從未被評估讀過的 corpus split，文件層級隔離；與 TRAIN / GOV-DEV / 人工 DEV 近重複的句子排除。"""
    pools: dict[str, list[tuple[str, TestItem]]] = {d: [] for d in GOV_DOMAINS}
    stats: dict[str, Counter[str]] = {d: Counter() for d in GOV_DOMAINS}
    for row in _corpus_rows(corpus_dir):
        domain = row.get("domain", "")
        if row["split"] != TEST_GOV_SPLIT or domain not in pools:
            continue
        stats[domain]["sentences"] += 1
        if index.is_duplicate(row["text"]):  # type: ignore[attr-defined]
            stats[domain]["near_duplicate"] += 1
            continue
        for match in _HAN_RUN.finditer(row["text"]):
            clause = match.group()
            if not 4 <= len(clause) <= 12:
                continue
            result = annotator.annotate(clause)  # type: ignore[attr-defined]
            if not hasattr(result, "readings"):
                stats[domain][f"rejected_{result.reason.value}"] += 1
                continue
            key = hashlib.sha256(f"{row['source_id']}\x00{row['doc_id']}\x00{clause}".encode()).hexdigest()
            pools[domain].append(
                (
                    key,
                    TestItem(
                        item_id=f"gov:{row['source_id']}:{key[:12]}",
                        group="test-gov",
                        category=domain,
                        left_context=row["text"][: match.start()],
                        text=clause,
                        readings=tuple(result.readings),
                        acceptable=(clause,),
                        source_id=row["source_id"],
                        doc_id=row["doc_id"],
                    ),
                )
            )
    items: list[TestItem] = []
    for domain, pool in pools.items():
        chosen: list[TestItem] = []
        per_doc: Counter[tuple[str, str]] = Counter()
        # 每份文件最多 3 個片段，避免少數長文件主導；依 sha256 排序，結果 deterministic。
        for _, item in sorted(pool, key=lambda p: p[0]):
            doc = (item.source_id, item.doc_id)
            if per_doc[doc] >= 3:
                continue
            per_doc[doc] += 1
            chosen.append(item)
            if len(chosen) == per_domain:
                break
        stats[domain]["selected"] = len(chosen)
        stats[domain]["documents"] = len(per_doc)
        items.extend(chosen)
    return items, stats


# ---------------------------------------------------------------- typo


def build_typo(everyday: Sequence[TestItem]) -> list[TestItem]:
    """每個 TEST-EVERYDAY 句子 × 六種錯誤各一筆；亂數種子由 id 與錯誤類型決定。"""
    from zaoseq_bopomofo.decoding.errors import ErrorKind
    from zaoseq_bopomofo.evaluation.decoding import inject_noise
    from zaoseq_bopomofo.lexicon.loader import load_lexicon
    from zaoseq_bopomofo.phonetics.keyboard import StandardKeyboardLayout

    inventory = frozenset(load_lexicon().syllables)
    layout = StandardKeyboardLayout()
    kinds = (
        ErrorKind.TONE_MISSING,
        ErrorKind.TONE_WRONG,
        ErrorKind.ADJACENT_KEY,
        ErrorKind.SUBSTITUTION,
        ErrorKind.DELETION,
        ErrorKind.INSERTION,
    )
    items: list[TestItem] = []
    for item in everyday:
        for kind in kinds:
            seed = int(hashlib.sha256(f"{item.item_id}\x00{kind.value}".encode()).hexdigest()[:16], 16)
            noisy = inject_noise(item.readings, kind, random.Random(seed), inventory, layout)
            if noisy is None:
                continue
            readings, position = noisy
            items.append(
                TestItem(
                    item_id=f"typo:{item.item_id.split(':', 1)[1]}:{kind.value}",
                    group="test-typo",
                    category=item.category,
                    left_context=item.left_context,
                    text=item.text,
                    readings=item.readings,
                    acceptable=item.acceptable,
                    noisy_readings=readings,
                    noise_kind=kind.value,
                    noise_position=position,
                )
            )
    return items


# ---------------------------------------------------------------- files


def _write_jsonl(path: Path, items: Sequence[TestItem], header: str) -> None:
    lines = [f"# {header}"] + [json.dumps(i.to_json(), ensure_ascii=False) for i in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _read_jsonl(path: Path) -> list[TestItem]:
    return [
        TestItem.from_json(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@dataclass
class Manifest:
    created_at: str
    files: dict[str, dict[str, object]] = field(default_factory=dict)
    policy: dict[str, object] = field(default_factory=dict)
    leakage: dict[str, object] = field(default_factory=dict)


def write_manifest(manifest: Manifest) -> None:
    MANIFEST.write_text(json.dumps(asdict(manifest), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def verify_manifest() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems: list[str] = []
    for rel, meta in manifest["files"].items():
        path = PROJECT_ROOT / rel
        if not path.exists():
            problems.append(f"missing: {rel}")
        elif file_hash(path) != meta["sha256"]:
            problems.append(f"changed: {rel}")
    return problems


def load_sealed(group: str, final_record: Path = FINAL_RECORD) -> list[TestItem]:
    """唯一的 TEST 讀取入口。沒有 FINAL freeze 紀錄、或紀錄 / TEST 檔案被改過時一律拒絕。"""
    from zaoseq_bopomofo.evaluation.freeze import verify

    if not final_record.exists():
        raise SealedTestError(f"找不到 {final_record}：模型與 Hybrid 設定 freeze 之前不得評估 TEST")
    record = json.loads(final_record.read_text(encoding="utf-8"))
    if not record.get("test_unlocked"):
        raise SealedTestError("FINAL freeze 紀錄未開放 TEST")
    drift = verify(final_record)
    if drift["changed"] or drift["missing"]:
        raise SealedTestError(f"freeze 之後檔案有變動：{drift}")
    problems = verify_manifest()
    if problems:
        raise SealedTestError(f"TEST 與 MANIFEST 不一致：{problems}")
    path = {"test-everyday": EVERYDAY_FILE, "test-gov": GOV_FILE, "test-typo": TYPO_FILE}[group]
    return _read_jsonl(path)


def check() -> list[str]:
    """不計算任何準確率：只驗證 schema、雜湊與讀音合法性。"""
    problems = verify_manifest()
    cns = _cns_readings()
    for path in (EVERYDAY_FILE, GOV_FILE, TYPO_FILE):
        for item in _read_jsonl(path):
            problems += [f"{item.item_id}: {issue}" for issue in reading_issues(item, cns)]
            if item.group == "test-typo":
                if len(item.noisy_readings) != len(item.readings) or item.noisy_readings == item.readings:
                    problems.append(f"{item.item_id}: noisy_readings 不合法")
    return problems


# ---------------------------------------------------------------- cli


def _cmd_build() -> int:
    if MANIFEST.exists():
        print("MANIFEST.json 已存在：TEST 已封存，不重建。", file=sys.stderr)
        return 1
    everyday = read_everyday_source()
    issues = review_everyday(everyday)
    illegal = [line for line in issues if line.startswith("ILLEGAL")]
    if illegal:
        print("\n".join(illegal), file=sys.stderr)
        return 1

    corpus_dir = PROJECT_ROOT / "data" / "corpus"
    # TEST-EVERYDAY 不得與人工 DEV / sanity 或任何語料句子近重複。
    everyday_index = leakage_index(corpus_dir, ("train", GOV_DEV_SPLIT, TEST_GOV_SPLIT), _hand_dev_sentences())
    leaked = [i.item_id for i in everyday if everyday_index.is_duplicate(i.left_context + i.text)]
    if leaked:
        print(f"TEST-EVERYDAY 與既有資料近重複：{leaked}", file=sys.stderr)
        return 1
    gov_index = leakage_index(
        corpus_dir,
        ("train", GOV_DEV_SPLIT),
        [*_hand_dev_sentences(), *((i.item_id, i.left_context + i.text) for i in everyday)],
    )
    gov, gov_stats = build_gov(corpus_dir, _annotator(), gov_index)
    typo = build_typo(everyday)

    _write_jsonl(EVERYDAY_FILE, everyday, "造序注音 TEST-EVERYDAY（sealed）：由 everyday_source.tsv 產生，不得修改")
    _write_jsonl(GOV_FILE, gov, f"造序注音 TEST-GOV（sealed）：corpus split '{TEST_GOV_SPLIT}'，文件層級隔離，不得修改")
    _write_jsonl(TYPO_FILE, typo, "造序注音 TEST-TYPO（sealed）：由 TEST-EVERYDAY gold readings deterministic 產生，不得修改")

    def describe(path: Path, items: Sequence[TestItem], by: str) -> dict[str, object]:
        return {
            "sha256": file_hash(path),
            "items": len(items),
            "by_" + by: dict(sorted(Counter(getattr(i, by) for i in items).items())),
        }

    manifest = Manifest(
        created_at="2026-09-23",
        files={
            "benchmarks/test/everyday_source.tsv": {"sha256": file_hash(EVERYDAY_SOURCE)},
            "benchmarks/test/everyday.jsonl": describe(EVERYDAY_FILE, everyday, "category"),
            "benchmarks/test/gov.jsonl": describe(GOV_FILE, gov, "category"),
            "benchmarks/test/typo.jsonl": describe(TYPO_FILE, typo, "noise_kind"),
        },
        policy={
            "sealed": True,
            "rule": (
                "TEST is not evaluated during fine-tuning or hyperparameter selection. It is run once, after the model "
                "checkpoint, training config, inference mode and Hybrid config are frozen in benchmarks/frozen/FINAL.json. "
                "If anything is changed after seeing TEST results, this TEST becomes a DEV set and a new TEST must be built."
            ),
            "test_gov_split": TEST_GOV_SPLIT,
            "gov_dev_split": GOV_DEV_SPLIT,
            "everyday_authoring": "hand-written 2026-09-23 without consulting decoder output or DEV failure cases",
            "typo_correction_default": "off; TEST-TYPO is for future evaluation only, not for tuning thresholds",
        },
        leakage={
            "near_duplicate": f"char 4-gram MinHash LSH, Jaccard >= {NEAR_DUP_THRESHOLD} on Han-only normalized text",
            "everyday_checked_against": ["corpus train/dev/test splits", "benchmarks/dev", "benchmarks/sanity"],
            "gov_checked_against": ["corpus train split", "GOV-DEV split", "benchmarks/dev", "benchmarks/sanity", "TEST-EVERYDAY"],
            "gov_stats": {d: dict(c) for d, c in gov_stats.items()},
        },
    )
    write_manifest(manifest)
    print(json.dumps(asdict(manifest), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.evaluation.testsets")
    parser.add_argument("command", choices=("review", "build", "check"))
    args = parser.parse_args(argv)
    if args.command == "review":
        lines = review_everyday(read_everyday_source())
        print("\n".join(lines) if lines else "no issues")
        return 0
    if args.command == "build":
        return _cmd_build()
    problems = check()
    print("\n".join(problems) if problems else "TEST ok: schema, hashes and reading legality")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
