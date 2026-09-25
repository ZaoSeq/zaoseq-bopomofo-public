from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

HAN = re.compile(r"[㐀-䶿一-鿿\U00020000-\U0002ffff]")
PARTICLES = "嗎呢吧啊啦喔耶嘛欸"
MANUAL_SANITY = ("我想要再去台北玩", "你要去西門町嗎", "你今天要幹嘛", "我等等再回你", "你有吃飯嗎")
OUTPUT = PROJECT_ROOT / "benchmarks" / "results" / "daily_round3_corpus_compare.json"


def han_only(text: str) -> str:
    return "".join(HAN.findall(unicodedata.normalize("NFC", text)))


@dataclass(frozen=True)
class CorpusProfile:
    """一份語料（train split）的聚合統計；只保留計數，不保留原文。"""

    name: str
    sentences: int
    han_tokens: int
    char_types: frozenset[str]
    bigram_types: int
    trigrams: frozenset[str]
    mean_han_length: float
    question_share: float
    particles_per_1k: dict[str, float]
    joined: str

    @classmethod
    def of(cls, name: str, texts: Sequence[str]) -> CorpusProfile:
        hans = [han_only(t) for t in texts]
        chars: Counter[str] = Counter()
        bigrams: set[str] = set()
        trigrams: set[str] = set()
        for h in hans:
            chars.update(h)
            bigrams.update(h[i : i + 2] for i in range(len(h) - 1))
            trigrams.update(h[i : i + 3] for i in range(len(h) - 2))
        tokens = sum(chars.values())
        n = max(len(texts), 1)
        return cls(
            name=name,
            sentences=len(texts),
            han_tokens=tokens,
            char_types=frozenset(chars),
            bigram_types=len(bigrams),
            trigrams=frozenset(trigrams),
            mean_han_length=round(tokens / n, 2),
            question_share=round(sum(t.rstrip().endswith(("？", "?")) for t in texts) / n, 4),
            particles_per_1k={p: round(1000 * sum(h.endswith(p) for h in hans) / n, 1) for p in PARTICLES},
            joined="\n".join(hans),
        )

    def summary(self) -> dict[str, object]:
        return {
            "train_sentences": self.sentences,
            "han_tokens": self.han_tokens,
            "char_types": len(self.char_types),
            "bigram_types": self.bigram_types,
            "bigram_types_per_1k_tokens": round(1000 * self.bigram_types / max(self.han_tokens, 1), 1),
            "trigram_types": len(self.trigrams),
            "mean_han_length": self.mean_han_length,
            "question_share": self.question_share,
            "sentence_final_particles_per_1k_sentences": self.particles_per_1k,
        }


class EvaluationCoverage:
    """Coverage-DEV v1.1 的 gold 字元 trigram 與多字詞，在一份語料中出現的比例（只看 train split）。"""

    def __init__(self, items: Iterable[object]) -> None:
        texts = [han_only("".join(w.text for w in item.words)) for item in items]  # type: ignore[attr-defined]
        self._trigrams = [t[i : i + 3] for t in texts for i in range(len(t) - 2)]
        self._words = sorted({w.text for item in items for w in item.words if len(han_only(w.text)) >= 2})  # type: ignore[attr-defined]

    def measure(self, profile: CorpusProfile) -> dict[str, object]:
        return {
            "gold_trigram_tokens": len(self._trigrams),
            "gold_trigram_coverage": round(sum(t in profile.trigrams for t in self._trigrams) / max(len(self._trigrams), 1), 4),
            "gold_multichar_words": len(self._words),
            "gold_word_coverage": round(sum(w in profile.joined for w in self._words) / max(len(self._words), 1), 4),
        }

    def words_only_in(self, profile: CorpusProfile, other: CorpusProfile) -> int:
        return sum(w in profile.joined and w not in other.joined for w in self._words)


class CorpusComparison:
    """Common Voice 與 Tatoeba（以及合併）的規模、多樣性、重疊、評估涵蓋與洩漏統計。"""

    def __init__(self, sentences: Sequence[object], evaluation: EvaluationCoverage, government_texts: set[str]) -> None:
        self._sentences = sentences
        self._evaluation = evaluation
        self._government = government_texts

    def _train(self, source_ids: set[str]) -> list[str]:
        return [s.text for s in self._sentences if s.source_id in source_ids and s.split == "train"]  # type: ignore[attr-defined]

    def run(self, tatoeba: str, common_voice: str, manifest: dict[str, object]) -> dict[str, object]:
        profiles = {
            "tatoeba": CorpusProfile.of("tatoeba", self._train({tatoeba})),
            "common_voice": CorpusProfile.of("common_voice", self._train({common_voice})),
            "pooled": CorpusProfile.of("pooled", self._train({tatoeba, common_voice})),
        }
        t, c = profiles["tatoeba"], profiles["common_voice"]
        quality = manifest["quality"]  # type: ignore[index]
        all_cv = {unicodedata.normalize("NFC", s.text) for s in self._sentences if s.source_id == common_voice}  # type: ignore[attr-defined]
        return {
            "profiles": {name: p.summary() for name, p in profiles.items()},
            "overlap": {
                "char_types_shared": len(t.char_types & c.char_types),
                "char_types_only_common_voice": len(c.char_types - t.char_types),
                "char_types_only_tatoeba": len(t.char_types - c.char_types),
                "char_jaccard": round(len(t.char_types & c.char_types) / len(t.char_types | c.char_types), 4),
                "trigram_jaccard": round(len(t.trigrams & c.trigrams) / len(t.trigrams | c.trigrams), 4),
            },
            "coverage_dev_v1_1": {name: self._evaluation.measure(p) for name, p in profiles.items()},
            "gold_words_only_in_common_voice": self._evaluation.words_only_in(c, t),
            "gold_words_only_in_tatoeba": self._evaluation.words_only_in(t, c),
            "leakage": {
                "excluded_by_reference": {k: quality[k]["eval_overlap_by_reference"] for k in (tatoeba, common_voice)},  # type: ignore[index]
                "common_voice_exact_in_government_corpus": sum(s in self._government for s in all_cv),
                "manual_sanity_in_corpus": {s: {n: s in p.joined for n, p in profiles.items() if n != "pooled"} for s in MANUAL_SANITY},
            },
            "quality": {k: {f: quality[k][f] for f in ("documents", "sentences_seen", "sentences_kept", "sentences_dropped", "splits", "length_han_chars")} for k in (tatoeba, common_voice)},  # type: ignore[index]
        }


def government_texts() -> set[str]:
    texts: set[str] = set()
    for path in sorted((PROJECT_ROOT / "data" / "corpus").glob("*/sentences.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            texts.add(unicodedata.normalize("NFC", json.loads(line)["text"]))
    return texts


def main(output: str | None = None) -> int:
    from zaoseq_bopomofo.coverage.dataset import V1_1
    from zaoseq_bopomofo.daily.corpus import CORPUS_DIR, load_sentences
    from zaoseq_bopomofo.daily.corpus_ablation import COMMON_VOICE, TATOEBA

    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    report = CorpusComparison(load_sentences(), EvaluationCoverage(V1_1.load()), government_texts()).run(TATOEBA, COMMON_VOICE, manifest)
    path = Path(output) if output else OUTPUT
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0
