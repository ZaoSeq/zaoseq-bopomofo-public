from __future__ import annotations

import json
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from zaoseq_bopomofo.corpus.neardup import NearDuplicateIndex
from zaoseq_bopomofo.corpus.sentences import Split, assign_split, dedupe_key, split_sentences
from zaoseq_bopomofo.corpus.statistics import count_ngrams, save_counts
from zaoseq_bopomofo.daily.guard import EvaluationGuard
from zaoseq_bopomofo.daily.importers import DailyImporter
from zaoseq_bopomofo.daily.quality import Drop, SentenceInspector, SourceQuality, document_problems
from zaoseq_bopomofo.daily.sources import DAILY_DIR, ApprovalScope, SourceRegistry, sha256_file

CORPUS_DIR = DAILY_DIR / "corpus"
ATTRIBUTION_DIR = DAILY_DIR / "attribution"
LM_DIR = DAILY_DIR / "lm"
ALL_DAILY = "daily_all"
PRODUCTION_DAILY = "daily_production"
MIN_TRIGRAM_COUNT = 2
CROSS_SPLIT_THRESHOLD = 0.6


@dataclass(frozen=True)
class DailySentence:
    source_id: str
    doc_id: str
    text: str
    split: str
    contributor: str = ""


class DailyCorpusBuilder:
    """匯入 → 文件層級檢查 → 斷句 → 單句檢查 → 去重 → 評估集排除 → 文件層級切分 → 跨 split 近重複排除。"""

    def __init__(
        self,
        importers: Sequence[DailyImporter],
        inspector: SentenceInspector,
        guard: EvaluationGuard,
        splitter: Callable[[str, str], Split] = assign_split,
    ) -> None:
        self._importers = importers
        self._inspector = inspector
        self._guard = guard
        self._splitter = splitter

    def build(self) -> tuple[list[DailySentence], dict[str, SourceQuality]]:
        seen: dict[str, str] = {}
        kept: list[DailySentence] = []
        stats: dict[str, SourceQuality] = {}
        for importer in self._importers:
            quality = stats.setdefault(importer.source_id, SourceQuality(importer.source_id))
            for document in importer.documents():
                kept += self._document(document.source_id, document.doc_id, document.text, document.contributor, quality, seen)
        kept = self._drop_cross_split(kept, stats)
        for sentence in kept:
            quality = stats[sentence.source_id]
            quality.splits[sentence.split] += 1
            self._inspector.record_kept(sentence.text, quality)
            if sentence.contributor:
                quality.contributors[sentence.contributor] += 1
        return kept, stats

    def _document(
        self, source_id: str, doc_id: str, raw: str, contributor: str, quality: SourceQuality, seen: dict[str, str]
    ) -> list[DailySentence]:
        quality.documents += 1
        text = unicodedata.normalize("NFC", raw)
        quality.nfc_changed_documents += text != raw
        problems = document_problems(text)
        if problems:
            quality.documents_dropped.update(p.value for p in problems)
            return []
        pieces = split_sentences(text)
        if not pieces:
            quality.documents_dropped[Drop.TOO_SHORT_OR_LOW_HAN.value] += 1
            return []
        split = self._splitter(source_id, doc_id).value
        out: list[DailySentence] = []
        for sentence in pieces:
            quality.sentences_seen += 1
            drop = self._inspector.inspect(sentence, quality)
            key = dedupe_key(sentence)
            if drop is None and key in seen:
                drop = Drop.DUPLICATE_IN_SOURCE if seen[key] == source_id else Drop.DUPLICATE_OTHER_DAILY
            if drop is None:
                overlap = self._guard.check(sentence)
                if overlap is not None:
                    quality.eval_overlap[f"{overlap.reference}:{overlap.kind}"] += 1
                    drop = Drop.EVAL_OVERLAP
            if drop is not None:
                quality.dropped[drop.value] += 1
                continue
            seen[key] = source_id
            out.append(DailySentence(source_id, doc_id, sentence, split, contributor))
        return out

    @staticmethod
    def _drop_cross_split(sentences: list[DailySentence], stats: dict[str, SourceQuality]) -> list[DailySentence]:
        index = NearDuplicateIndex(threshold=CROSS_SPLIT_THRESHOLD)
        index.add_all((f"{s.source_id}:{s.doc_id}", s.text) for s in sentences if s.split == Split.TRAIN.value)
        kept: list[DailySentence] = []
        for sentence in sentences:
            if sentence.split != Split.TRAIN.value and index.query(sentence.text):
                stats[sentence.source_id].dropped[Drop.CROSS_SPLIT_NEAR_DUP.value] += 1
                continue
            kept.append(sentence)
        return kept


class DailyCorpusWriter:
    """句子寫入 data/daily/corpus（不進 git）；manifest、品質報告與需要顯名來源的作者清單進 git。"""

    def __init__(
        self, registry: SourceRegistry, corpus_dir: Path = CORPUS_DIR, lm_dir: Path = LM_DIR, attribution_dir: Path = ATTRIBUTION_DIR
    ) -> None:
        self._registry = registry
        self._corpus_dir = corpus_dir
        self._lm_dir = lm_dir
        self._attribution_dir = attribution_dir

    def write(self, sentences: Sequence[DailySentence], stats: dict[str, SourceQuality], guard_sizes: dict[str, int]) -> dict[str, object]:
        by_source: dict[str, list[DailySentence]] = {}
        for sentence in sentences:
            by_source.setdefault(sentence.source_id, []).append(sentence)
        files: dict[str, str] = {}
        for source_id, rows in sorted(by_source.items()):
            directory = self._corpus_dir / source_id
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / "sentences.jsonl"
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(json.dumps({k: v for k, v in asdict(row).items() if k != "contributor"}, ensure_ascii=False) + "\n")
            files[path.relative_to(DAILY_DIR).as_posix()] = sha256_file(path)
            self._write_attribution(source_id, rows)
        lm = self._write_language_models(by_source)
        manifest = {
            "schema": "zaoseq-bopomofo/daily-corpus/v1",
            "sources": sorted(by_source),
            "approval_scope": {s: self._registry[s].approval_scope.value for s in sorted(by_source)},
            "split_policy": "document-level sha256 hash (5% test, 5% dev, 90% train); the daily test split is not used this round",
            "exclusion_references": guard_sizes,
            "quality": {source_id: q.summary() for source_id, q in sorted(stats.items())},
            "sentence_files_sha256": files,
            "language_models": lm,
        }
        self._corpus_dir.mkdir(parents=True, exist_ok=True)
        (self._corpus_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        return manifest

    def production_sources(self, source_ids: Iterable[str]) -> set[str]:
        return {s for s in source_ids if self._registry[s].approval_scope is ApprovalScope.PRODUCTION}

    def _write_attribution(self, source_id: str, rows: Sequence[DailySentence]) -> None:
        source = self._registry[source_id]
        authors = Counter(r.contributor for r in rows if r.contributor)
        if not authors or not any("attribution" in f for f in source.fields_used):
            return
        self._attribution_dir.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# {source.dataset_name} ({source.version})",
            f"# {source.license_name}: {source.license_url}",
            "# author\tsentences kept (all splits)",
            *(f"{name}\t{count}" for name, count in sorted(authors.items())),
        ]
        (self._attribution_dir / f"{source_id}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    def _write_language_models(self, by_source: dict[str, list[DailySentence]]) -> dict[str, object]:
        groups = {source_id: rows for source_id, rows in by_source.items()}
        groups[ALL_DAILY] = [s for rows in by_source.values() for s in rows]
        groups[PRODUCTION_DAILY] = [s for s in groups[ALL_DAILY] if s.source_id in self.production_sources(by_source)]
        out: dict[str, object] = {}
        for name, rows in sorted(groups.items()):
            train = [s.text for s in rows if s.split == Split.TRAIN.value]
            counts = count_ngrams(train, min_trigram_count=MIN_TRIGRAM_COUNT)
            info = {
                "train_sentences": len(train),
                "char_tokens": counts.total_tokens,
                "char_vocabulary": len(counts.unigrams),
                "char_bigrams": len(counts.bigrams),
                "char_trigrams_kept": len(counts.trigrams),
                "min_trigram_count": MIN_TRIGRAM_COUNT,
                "sources": sorted({s.source_id for s in rows}),
                "production_eligible": all(self._registry[s.source_id].approval_scope is ApprovalScope.PRODUCTION for s in rows),
            }
            save_counts(counts, {}, self._lm_dir / name, info)
            out[name] = info
        return out


def production_source_ids(registry: SourceRegistry | None = None) -> set[str]:
    registry = registry or SourceRegistry.load()
    return {s.source_id for s in registry if s.approval_scope is ApprovalScope.PRODUCTION}


def load_sentences(corpus_dir: Path = CORPUS_DIR, sources: Iterable[str] | None = None) -> list[DailySentence]:
    wanted = set(sources) if sources is not None else None
    rows: list[DailySentence] = []
    for path in sorted(corpus_dir.glob("*/sentences.jsonl")):
        if wanted is not None and path.parent.name not in wanted:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            rows.append(DailySentence(**json.loads(line)))
    return rows
