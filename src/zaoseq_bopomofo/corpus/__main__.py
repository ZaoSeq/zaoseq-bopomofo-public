"""語料建置 CLI。

    python -m zaoseq_bopomofo.corpus check      # 列出每個來源能否進 production 與原因
    python -m zaoseq_bopomofo.corpus build      # 驗證 sha256 → 正規化 → 斷句 → 去重 → 切分 → n-gram
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from zaoseq_bopomofo.corpus.importer import RAW_DIR, iter_documents
from zaoseq_bopomofo.corpus.normalize import is_han, normalize_text
from zaoseq_bopomofo.corpus.sentences import Sentence, Split, build_sentences
from zaoseq_bopomofo.corpus.source import REGISTRY_PATH, Domain, SourceKind, load_registry
from zaoseq_bopomofo.corpus.statistics import count_ngrams, count_words, save_counts

CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"
PROSE_KINDS = (SourceKind.LAW_XML, SourceKind.FAQ_CSV, SourceKind.PRESS_JSON, SourceKind.TABULAR)
LF = chr(10)


def _cmd_check(args: argparse.Namespace) -> int:
    registry = load_registry(args.registry)
    for record in registry.sources:
        issues = record.production_issues()
        print(f"{record.id:28s} {'OK' if not issues else 'BLOCKED: ' + '; '.join(issues)}")
    for rejected in registry.rejected_sources:
        print(f"{rejected['id']:28s} REJECTED: {rejected['reason']}")
    return 0


# 去重保留第一次出現的句子；非法律領域先處理，讓共用句子歸在一般領域，而不是被法律語料吸收。
DOMAIN_ORDER = (
    Domain.GOVERNMENT_FAQ,
    Domain.PUBLIC_SERVICE,
    Domain.PRESS_RELEASE,
    Domain.OTHER_FORMAL,
    Domain.LEGAL,
)
DOMAIN_CAP = 20_000


def _cmd_build(args: argparse.Namespace) -> int:
    from zaoseq_bopomofo.corpus.domains import GENERAL_WEIGHTS, cap_by_domain
    from zaoseq_bopomofo.corpus.statistics import tokenize

    registry = load_registry(args.registry)
    blocked = [r.id for r in registry.sources if not r.production_ready]
    if blocked:
        print(f"[skip] 授權未通過，不匯入：{blocked}", file=sys.stderr)

    seen: set[str] = set()
    per_source: dict[str, dict[str, object]] = {}
    train: list[tuple[Domain, str]] = []
    prose = sorted(
        registry.production_sources(PROSE_KINDS),
        key=lambda r: (DOMAIN_ORDER.index(r.domain) if r.domain in DOMAIN_ORDER else len(DOMAIN_ORDER), r.id),
    )
    for record in prose:
        documents = list(iter_documents(record, args.raw_dir))
        sentences = list(build_sentences(documents, seen))
        out_dir = args.corpus_dir / record.id
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "sentences.jsonl").open("w", encoding="utf-8", newline=LF) as handle:
            for s in sentences:
                handle.write(json.dumps(_sentence_json(s, record.domain), ensure_ascii=False) + LF)
        splits = Counter(s.split.value for s in sentences)
        train_sentences = [s.text for s in sentences if s.split is Split.TRAIN]
        per_source[record.id] = {
            "domain": record.domain.value,
            "provider": record.provider,
            "documents": len({d.doc_id for d in documents}),
            "sentence_count": len(sentences),
            "sentences_by_split": dict(sorted(splits.items())),
            "token_count": sum(len(tokenize(t)) for t in (s.text for s in sentences)),
            "train_token_count": sum(len(tokenize(t)) for t in train_sentences),
            "sha256": record.sha256,
        }
        train.extend((record.domain, t) for t in train_sentences)
        print(f"{record.id} [{record.domain.value}]: {len(sentences)} sentences {dict(splits)}")

    terms: set[str] = set()
    for record in registry.production_sources((SourceKind.TERM_CSV,)):
        before = len(terms)
        for document in iter_documents(record, args.raw_dir):
            term = normalize_text(document.text)
            if term and all(is_han(ch) for ch in term) and len(term) >= 2:
                terms.add(term)
        per_source[record.id] = {"domain": record.domain.value, "provider": record.provider,
                                 "terms_added": len(terms) - before, "sha256": record.sha256}

    from zaoseq_bopomofo.lexicon.loader import load_lexicon

    lexicon_words = load_lexicon().lexicon.words()
    vocabulary = frozenset(terms | {w for w in lexicon_words if len(w) >= 2})
    max_word = max(len(w) for w in vocabulary)
    lm_dir = args.corpus_dir / "lm"
    domain_tokens: Counter[str] = Counter()
    for domain, text in train:
        domain_tokens[domain.value] += len(tokenize(text))

    configurations = {
        "raw": [t for _, t in train],
        "capped": cap_by_domain(train, DOMAIN_CAP),
    }
    for domain in DOMAIN_ORDER:
        texts = [t for d, t in train if d is domain]
        if texts:
            configurations[f"domain/{domain.value}"] = texts
    summaries: dict[str, dict[str, object]] = {}
    for name, texts in configurations.items():
        counts = count_ngrams(texts, min_trigram_count=args.min_trigram_count)
        words = count_words(texts, vocabulary, max_length=max_word) if name == "raw" else {}
        summary = {
            "train_sentences": len(texts),
            "char_tokens": counts.total_tokens,
            "char_vocabulary": len(counts.unigrams),
            "char_bigrams": len(counts.bigrams),
            "char_trigrams_kept": len(counts.trigrams),
        }
        save_counts(counts, words, lm_dir / name, {"schema": "zaoseq-bopomofo/corpus-lm/v2", "configuration": name, **summary})
        summaries[name] = summary

    for info in per_source.values():
        domain = info["domain"]
        weight = GENERAL_WEIGHTS.weights.get(Domain(domain), 0.0)
        share = info.get("train_token_count", 0) / domain_tokens[domain] if domain_tokens[domain] else 0.0  # type: ignore[operator]
        # 來源在 general 插值模型中的有效權重 = 領域權重 × 該來源在領域 train token 中的佔比。
        info["domain_weight"] = weight
        info["weight"] = round(weight * share, 6)
    manifest = {
        "schema": "zaoseq-bopomofo/corpus/v2",
        "sources": per_source,
        "domains": {
            d.value: {
                "train_tokens": domain_tokens[d.value],
                "train_sentences": sum(1 for dd, _ in train if dd is d),
                "general_weight": GENERAL_WEIGHTS.weights.get(d, 0.0),
            }
            for d in DOMAIN_ORDER
        },
        "configurations": summaries,
        "domain_cap_sentences": DOMAIN_CAP,
        "min_trigram_count": args.min_trigram_count,
        "word_vocabulary": len(vocabulary),
        "segmentation": "longest match over builtin lexicon + NAER terms; unvalidated, word bigram not built",
        "duplicate_policy": "global exact dedupe on Han-only key; non-legal domains processed first",
    }
    (args.corpus_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + LF, encoding="utf-8")
    print(json.dumps({"domains": manifest["domains"], "configurations": summaries}, ensure_ascii=False, indent=2))
    return 0


def _sentence_json(sentence: Sentence, domain: Domain) -> dict[str, str]:
    return {
        "source_id": sentence.source_id,
        "domain": domain.value,
        "doc_id": sentence.doc_id,
        "split": sentence.split.value,
        "text": sentence.text,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m zaoseq_bopomofo.corpus")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    parser.add_argument("--min-trigram-count", type=int, default=2)
    parser.add_argument("command", choices=("check", "build"))
    args = parser.parse_args(argv)
    commands = {"check": _cmd_check, "build": _cmd_build}
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
