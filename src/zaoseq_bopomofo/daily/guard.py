from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from zaoseq_bopomofo.corpus.neardup import NearDuplicateIndex
from zaoseq_bopomofo.corpus.sentences import dedupe_key

CONTAINMENT_N = 8


@dataclass(frozen=True)
class ReferenceSet:
    name: str
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Overlap:
    reference: str
    key: str
    kind: str


class EvaluationGuard:
    """語料句子若與任何評估集近重複（MinHash Jaccard），或共用 `CONTAINMENT_N` 個連續漢字，就排除。
    v0.1 TEST 只作為這裡的排除參照，不用於任何選擇。"""

    def __init__(self, references: Sequence[ReferenceSet], threshold: float, containment_n: int = CONTAINMENT_N) -> None:
        self._index = NearDuplicateIndex(threshold=threshold)
        self._grams: dict[str, tuple[str, str]] = {}
        self._n = containment_n
        self.sizes = {r.name: len(r.rows) for r in references}
        for reference in references:
            for key, text in reference.rows:
                tagged = f"{reference.name}|{key}"
                self._index.add(tagged, text)
                han = dedupe_key(text)
                for i in range(len(han) - self._n + 1):
                    self._grams.setdefault(han[i : i + self._n], (reference.name, key))

    def check(self, text: str) -> Overlap | None:
        matches = self._index.query(text)
        if matches:
            name, _, key = matches[0].key.partition("|")
            return Overlap(name, key, "near_duplicate")
        han = dedupe_key(text)
        for i in range(len(han) - self._n + 1):
            hit = self._grams.get(han[i : i + self._n])
            if hit is not None:
                return Overlap(hit[0], hit[1], f"shared_{self._n}gram")
        return None


def default_references() -> list[ReferenceSet]:
    """Coverage-DEV v1.0 / v1.1、人工 DEV 與 sanity、GOV-DEV 與 TEST-GOV 所在的語料 split、v0.1 TEST 三個集合。"""
    import json

    from zaoseq_bopomofo.coverage.dataset import DATASETS
    from zaoseq_bopomofo.evaluation.testsets import (
        EVERYDAY_FILE,
        GOV_DEV_SPLIT,
        GOV_FILE,
        TEST_GOV_SPLIT,
        TYPO_FILE,
        _hand_dev_sentences,
        _read_jsonl,
    )
    from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

    def items(rows: Iterable[object]) -> tuple[tuple[str, str], ...]:
        return tuple((i.item_id, i.left_context + i.text) for i in rows)  # type: ignore[attr-defined]

    references = [ReferenceSet(f"coverage_dev_v{v}", items(d.load())) for v, d in DATASETS.items()]
    references.append(ReferenceSet("hand_dev_sanity", tuple(_hand_dev_sentences())))
    gov: dict[str, list[tuple[str, str]]] = {GOV_DEV_SPLIT: [], TEST_GOV_SPLIT: []}
    for path in sorted((PROJECT_ROOT / "data" / "corpus").glob("*/sentences.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["split"] in gov:
                gov[row["split"]].append((f"{row['source_id']}:{row['doc_id']}", row["text"]))
    references.append(ReferenceSet("gov_dev_corpus_split", tuple(gov[GOV_DEV_SPLIT])))
    references.append(ReferenceSet("reference_v0_1_test_gov_corpus_split", tuple(gov[TEST_GOV_SPLIT])))
    for name, path in (("everyday", EVERYDAY_FILE), ("gov", GOV_FILE), ("typo", TYPO_FILE)):
        references.append(ReferenceSet(f"reference_v0_1_test_{name}", items(_read_jsonl(path))))
    return references
