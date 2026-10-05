from __future__ import annotations

import itertools
import zipfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from zaoseq_bopomofo.daily.script import SIMPLIFIED_WORDS

MAX_SUBSTITUTIONS = 2
MIN_GRAM, MAX_GRAM = 2, 4
MIN_SOURCE_COUNT = 5
MAX_FORM_SHARE = 0.05
MIN_EVIDENCE = 3


def read_simplified_variants(unihan_zip: Path) -> dict[str, frozenset[str]]:
    """Unihan kSimplifiedVariant：繁體字 → 其簡體寫法（排除指向自己的項目）。"""
    with zipfile.ZipFile(unihan_zip) as archive:
        text = archive.read("Unihan_Variants.txt").decode("utf-8")
    out: dict[str, set[str]] = {}
    for line in text.splitlines():
        if line.startswith("#") or "\tkSimplifiedVariant\t" not in line:
            continue
        code, _, targets = line.split("\t")
        char = chr(int(code[2:], 16))
        for target in targets.split():
            simplified = chr(int(target.split("<")[0][2:], 16))
            if simplified != char:
                out.setdefault(char, set()).add(simplified)
    return {k: frozenset(v) for k, v in out.items()}


def count_grams(texts: Sequence[str], alphabet: frozenset[str], wanted: frozenset[str] | None = None) -> Counter[str]:
    """2–4 字、至少含一個 `alphabet` 字元的片段次數；`wanted` 不為 None 時只計這些片段。"""
    counts: Counter[str] = Counter()
    for text in texts:
        starts = {s for i, c in enumerate(text) if c in alphabet for s in range(max(0, i - MAX_GRAM + 1), i + 1)}
        for start in starts:
            for length in range(MIN_GRAM, MAX_GRAM + 1):
                gram = text[start : start + length]
                if len(gram) == length and any(c in alphabet for c in gram) and (wanted is None or gram in wanted):
                    counts[gram] += 1
    return counts


class ScriptGuard:
    """判斷文字是否含有簡體字元或簡體詞形。

    簡體字元：Unihan 標為簡體、且不在臺灣標準字集（CNS 11643 第 1、2 字面）的字。
    簡體詞形：合法繁體語料中常見片段（≥ MIN_SOURCE_COUNT 次）的字換成本身也是標準字的簡體寫法後得到，
    且在同一批語料中出現次數不到原片段 MAX_FORM_SHARE 的形式（例如 這裡 → 這里）。
    被替換的字若在文字中能和前後字組成語料中常見（≥ MIN_EVIDENCE 次）且不屬於簡體詞形的片段
    （馬德里、征服），就是合法用法而不算違規。CandidateFamily 字形表中的同字異體（台／臺等）不視為簡體。
    """

    def __init__(self, simplified_chars: Iterable[str], forms: Mapping[str, tuple[int, ...]], evidence: Iterable[str] = ()) -> None:
        self._chars = frozenset(simplified_chars)
        self._forms = dict(forms)
        self._evidence = frozenset(evidence)
        self._max_form = max((len(f) for f in self._forms), default=0)

    @classmethod
    def build(
        cls,
        standard: Iterable[str],
        variants: Mapping[str, frozenset[str]],
        texts: Sequence[str],
        accepted_pairs: Iterable[tuple[str, str]] = (),
        extra_forms: Iterable[str] = SIMPLIFIED_WORDS,
    ) -> ScriptGuard:
        standard_set = frozenset(standard)
        simplified_chars = {s for targets in variants.values() for s in targets} - standard_set
        accepted = {frozenset(pair) for pair in accepted_pairs}
        swaps = {t: sorted(s for s in targets if s in standard_set and frozenset((t, s)) not in accepted) for t, targets in variants.items() if t in standard_set}
        swaps = {t: s for t, s in swaps.items() if s}
        targets = frozenset(x for v in swaps.values() for x in v)
        sources = {g: c for g, c in count_grams(texts, frozenset(swaps)).items() if c >= MIN_SOURCE_COUNT}
        generated: Counter[str] = Counter()
        positions_of: dict[str, set[int]] = {}
        for gram, count in sources.items():
            positions = [i for i, ch in enumerate(gram) if ch in swaps]
            for size in range(1, min(MAX_SUBSTITUTIONS, len(positions)) + 1):
                for chosen in itertools.combinations(positions, size):
                    for replacement in itertools.product(*(swaps[gram[i]] for i in chosen)):
                        chars = list(gram)
                        for i, s in zip(chosen, replacement):
                            chars[i] = s
                        form = "".join(chars)
                        generated[form] += count
                        positions_of.setdefault(form, set()).update(chosen)
        seen = count_grams(texts, targets)
        forms = {f: tuple(sorted(positions_of[f])) for f, source in generated.items() if seen.get(f, 0) < MAX_FORM_SHARE * source}
        for word in extra_forms:
            forms.setdefault(word, tuple(i for i, ch in enumerate(word) if ch in targets) or tuple(range(len(word))))
        evidence = {g for g, c in seen.items() if c >= MIN_EVIDENCE and g not in forms}
        return cls(simplified_chars, forms, evidence)

    @property
    def forms(self) -> frozenset[str]:
        return frozenset(self._forms)

    def violates(self, text: str, start: int = 0, final: bool = False) -> bool:
        """`text[start:]` 是新加入的部分。被替換字的佐證可能來自後面的字，所以離結尾不到 MAX_GRAM 個字的位置
        先不判定，`final=True`（完整候選）時才全部判定。"""
        for end in range(max(start - MAX_GRAM, 0) + 1, len(text) + 1):
            if end > start and text[end - 1] in self._chars:
                return True
            for length in range(2, min(self._max_form, end) + 1):
                form = text[end - length : end]
                swapped = self._forms.get(form)
                if swapped is None:
                    continue
                for offset in swapped:
                    position = end - length + offset
                    if not final and position > len(text) - MAX_GRAM:
                        continue
                    if not self._supported(text, position):
                        return True
        return False

    def _supported(self, text: str, position: int) -> bool:
        for i in range(max(0, position - MAX_GRAM + 1), position + 1):
            for j in range(max(i + MIN_GRAM, position + 1), min(len(text), i + MAX_GRAM) + 1):
                if text[i:j] in self._evidence:
                    return True
        return False


def training_texts() -> list[str]:
    import json

    from zaoseq_bopomofo.daily.corpus_v2 import CorpusV2
    from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

    texts = [s.text for s in CorpusV2().sentences() if s.split == "train"]
    for path in sorted((PROJECT_ROOT / "data" / "corpus").glob("*/sentences.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["split"] == "train":
                texts.append(row["text"])
    return texts


def default_guard() -> ScriptGuard:
    from zaoseq_bopomofo.daily.sources import LicenseGate, RawFiles, SourceRegistry
    from zaoseq_bopomofo.lexicon.builder import read_char_readings
    from zaoseq_bopomofo.lexicon.loader import DEFAULT_CHAR_READINGS, PROJECT_ROOT

    unihan = SourceRegistry.load()["unihan_variants"]
    LicenseGate().require(unihan)
    variants = read_simplified_variants(RawFiles().verify(unihan)["Unihan.zip"])
    standard = {r.char for r in read_char_readings(DEFAULT_CHAR_READINGS) if r.plane in (1, 2)}
    table = PROJECT_ROOT / "data" / "builtin" / "variants.tsv"
    pairs = [tuple(line.split("	")[:2]) for line in table.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    return ScriptGuard.build(standard, variants, training_texts(), pairs)  # type: ignore[arg-type]
