"""讀音 → 封閉候選集合，並給出 baseline 順序。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from zaoseq_bopomofo.decoding.candidate import Candidate, CandidateKind, Segment
from zaoseq_bopomofo.decoding.decoder import Decoder
from zaoseq_bopomofo.lexicon.lexicon import Lexicon


@dataclass(frozen=True)
class _Scored:
    text: str
    score: float
    kind: CandidateKind
    segments: tuple[Segment, ...]


_KIND_ORDER = {CandidateKind.WORD: 0, CandidateKind.COMPOSITION: 1}


@runtime_checkable
class CandidateSource(Protocol):
    """讀音 → 依 baseline 排序的封閉候選集合。`left_context` 只能是已確認送出的文字。"""

    def candidates_for(self, readings: tuple[str, ...], left_context: str = "") -> tuple[Candidate, ...]: ...


class CandidateGenerator:
    """候選序列 = 讀音完全吻合的詞條 +（多音節時）decoder 的前幾名分詞組合。

    每個候選都覆蓋整段 composition，讓 contextual ranker 比較的是完整序列而不是單字。
    baseline 順序為 (-baseline_score, WORD 優先, 文字 code point)；這一層不看前文。
    """

    def __init__(self, lexicon: Lexicon, decoder: Decoder | None = None, max_compositions: int = 8) -> None:
        self._lexicon = lexicon
        self._decoder = decoder or Decoder(lexicon)
        self._max_compositions = max_compositions

    def candidates_for(self, readings: tuple[str, ...], left_context: str = "") -> tuple[Candidate, ...]:
        """空 tuple 表示確定沒有候選，不是錯誤；由上層決定是否保留組字狀態。
        這個 lexicon-only generator 不看前文，`left_context` 只為了符合 CandidateSource 介面。"""
        if not readings:
            return ()
        scored: dict[str, _Scored] = {}
        for entry in self._lexicon.lookup(readings):
            # 詞庫以 (text, readings) 為唯一鍵，同讀音下文字不會重複，這裡直接寫入。
            scored[entry.text] = _Scored(
                entry.text,
                self._lexicon.log10_probability(entry),
                CandidateKind.WORD,
                (Segment(entry.text, entry.readings),),
            )

        if len(readings) > 1:
            added = 0
            for composition in self._decoder.decode(readings):
                if added >= self._max_compositions:
                    break
                # 單段組合就是整詞本身，已在上面加入。
                if len(composition.segments) == 1 or composition.text in scored:
                    continue
                scored[composition.text] = _Scored(
                    composition.text,
                    composition.log10_probability,
                    CandidateKind.COMPOSITION,
                    tuple(Segment(e.text, e.readings) for e in composition.segments),
                )
                added += 1

        ordered = sorted(scored.values(), key=lambda s: (-s.score, _KIND_ORDER[s.kind], s.text))
        return tuple(
            Candidate(
                text=s.text,
                readings=readings,
                baseline_score=s.score,
                baseline_rank=rank,
                kind=s.kind,
                segments=s.segments,
            )
            for rank, s in enumerate(ordered)
        )
