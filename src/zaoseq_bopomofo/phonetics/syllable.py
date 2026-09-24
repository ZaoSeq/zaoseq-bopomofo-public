"""結構化的注音音節。"""

from __future__ import annotations

from dataclasses import dataclass

from zaoseq_bopomofo.phonetics.symbol import Tone


@dataclass(frozen=True)
class BopomofoSyllable:
    """聲母、介音、韻母、聲調各佔一格。

    `tone is None` 表示使用者還沒輸入聲調（組字中）；`Tone.FIRST` 則是明確的一聲。
    """

    initial: str | None = None
    medial: str | None = None
    final: str | None = None
    tone: Tone | None = None

    @property
    def has_body(self) -> bool:
        return self.initial is not None or self.medial is not None or self.final is not None

    @property
    def is_empty(self) -> bool:
        return not self.has_body and self.tone is None

    @property
    def is_complete(self) -> bool:
        return self.has_body and self.tone is not None

    @property
    def body(self) -> str:
        return (self.initial or "") + (self.medial or "") + (self.final or "")

    def text(self) -> str:
        """規範寫法：調號一律放在最後，輕聲也是（`ㄌㄜ˙`），整個系統以此作為 reading key。"""
        return self.body + (self.tone.value if self.tone is not None else "")

    def __str__(self) -> str:
        return self.text()
