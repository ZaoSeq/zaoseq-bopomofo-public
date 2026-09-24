"""候選的 semantic family：只因正字／異體寫法不同的候選屬於同一族。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.decoding.candidate import Candidate

DEFAULT_VARIANTS = Path(__file__).resolve().parents[3] / "data" / "builtin" / "variants.tsv"


@dataclass(frozen=True)
class VariantRule:
    canonical: str
    variant: str
    note: str


class VariantTable:
    """只使用明確列出的字形規則；不在表內的字一律視為不同字，不做任何推測。"""

    def __init__(self, rules: Sequence[VariantRule]) -> None:
        mapping: dict[str, str] = {}
        for rule in rules:
            if len(rule.canonical) != 1 or len(rule.variant) != 1 or rule.canonical == rule.variant:
                raise ValueError(f"字形規則必須是兩個不同的單字：{rule}")
            if rule.variant in mapping:
                raise ValueError(f"{rule.variant} 重複出現在字形規則中")
            mapping[rule.variant] = rule.canonical
        self._canonical = mapping

    @classmethod
    def load(cls, path: Path = DEFAULT_VARIANTS) -> VariantTable:
        rules = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            canonical, variant, note = line.split("\t")
            rules.append(VariantRule(canonical, variant, note))
        return cls(rules)

    def family_key(self, text: str) -> str:
        return "".join(self._canonical.get(ch, ch) for ch in text)


@dataclass(frozen=True)
class CandidateFamily:
    """`members` 依 baseline 順序排列；第一個成員是 family 的代表，只有它會進 contextual 視窗。
    family 之間的語義比較交給 contextual ranker，family 內的寫法偏好交給 baseline。"""

    key: str
    members: tuple[Candidate, ...]

    @property
    def representative(self) -> Candidate:
        return self.members[0]


def group_families(candidates: Sequence[Candidate], table: VariantTable | None) -> tuple[CandidateFamily, ...]:
    """沒有字形表時每個候選自成一族；family 順序由代表的 baseline 名次決定。"""
    order: list[str] = []
    members: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        key = table.family_key(candidate.text) if table is not None else candidate.text
        if key not in members:
            order.append(key)
            members[key] = []
        members[key].append(candidate)
    return tuple(CandidateFamily(key, tuple(members[key])) for key in order)
