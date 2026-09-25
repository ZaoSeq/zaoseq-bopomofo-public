from __future__ import annotations

import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from zaoseq_bopomofo.corpus.normalize import is_han

# 單字本身在繁體中也合法（Big5 / CNS 1–2 字面內），但這些詞形只出現在簡體文字中。
SIMPLIFIED_WORDS = (
    "什么", "怎么", "那么", "多么", "要么", "么么",
    "以后", "然后", "后来", "最后", "之后", "背后", "后面", "前后", "先后", "往后", "今后", "后天", "后悔", "落后",
    "里面", "这里", "那里", "哪里", "家里", "心里", "手里", "城里", "夜里", "屋里",
    "干净", "干吗", "干嘛", "干什么", "干活",
    "面条", "方便面", "吃面",
    "准备", "标准", "批准", "准确", "准时",
    "范围", "模范", "制造", "冲突", "放松", "轻松", "出租车", "只有一只", "一只",
    "台湾", "台风",
)


class ScriptLabel(Enum):
    TRADITIONAL = "traditional"
    SIMPLIFIED = "simplified"
    NON_STANDARD = "non_standard"
    NO_HAN = "no_han"


@dataclass(frozen=True)
class ScriptVerdict:
    label: ScriptLabel
    han: int
    standard: int
    simplified_chars: tuple[str, ...]
    other_chars: tuple[str, ...]
    simplified_words: tuple[str, ...]

    @property
    def traditional_ratio(self) -> float:
        return self.standard / self.han if self.han else 0.0


def read_simplified_characters(unihan_zip: Path) -> frozenset[str]:
    """Unihan 中 kTraditionalVariant 指向其他字的字；只用來標記，不做任何轉換。"""
    with zipfile.ZipFile(unihan_zip) as archive:
        text = archive.read("Unihan_Variants.txt").decode("utf-8")
    found: set[str] = set()
    for line in text.splitlines():
        if line.startswith("#") or "\tkTraditionalVariant\t" not in line:
            continue
        code, _, targets = line.split("\t")
        char = chr(int(code[2:], 16))
        if any(chr(int(t[2:], 16)) != char for t in targets.split()):
            found.add(char)
    return frozenset(found)


class ScriptClassifier:
    """臺灣標準字集 = CNS 11643 第 1、2 字面。句子只有在每個漢字都屬於標準字集、
    且不含簡體詞形時才算繁體；其餘整句排除，不轉換。"""

    def __init__(
        self,
        standard: Iterable[str],
        simplified_characters: Iterable[str] = (),
        simplified_words: Iterable[str] = SIMPLIFIED_WORDS,
    ) -> None:
        self._standard = frozenset(standard)
        self._simplified = frozenset(simplified_characters) - self._standard
        self._words = tuple(sorted(set(simplified_words)))

    def classify(self, text: str) -> ScriptVerdict:
        han = [c for c in text if is_han(c)]
        outside = [c for c in han if c not in self._standard]
        simplified_chars = tuple(sorted({c for c in outside if c in self._simplified}))
        other = tuple(sorted({c for c in outside if c not in self._simplified}))
        words = tuple(w for w in self._words if w in text)
        if not han:
            label = ScriptLabel.NO_HAN
        elif simplified_chars or words:
            label = ScriptLabel.SIMPLIFIED
        elif other:
            label = ScriptLabel.NON_STANDARD
        else:
            label = ScriptLabel.TRADITIONAL
        return ScriptVerdict(label, len(han), len(han) - len(outside), simplified_chars, other, words)
