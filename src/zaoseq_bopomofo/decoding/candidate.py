"""候選序列資料型別。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from zaoseq_bopomofo.decoding.correction import ReadingCorrection
from zaoseq_bopomofo.decoding.scoring import ScoreBreakdown


class CandidateKind(Enum):
    # 詞庫中讀音完全吻合的單一詞條。
    WORD = "word"
    # decoder 拼出的多段序列，例如「再」+「去」+「台北」。
    COMPOSITION = "composition"


@dataclass(frozen=True)
class Segment:
    text: str
    readings: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    """覆蓋整段 composition 讀音的一個候選序列。

    `baseline_score` 是 unigram log10 機率，WORD 與 COMPOSITION 在同一尺度上可比較；
    `baseline_rank` 為 0-based，是所有排序 tiebreak 的最終依據。
    `segments` 為空 tuple 表示分段未知（例如 benchmark 只保存了文字）。
    `breakdown` 為 None 表示候選來自不拆分數的舊 generator；`correction` 為 None 表示照原輸入解讀，
    不為 None 時 `readings` 是推論出的讀音，原始輸入保存在 correction.original。
    """

    text: str
    readings: tuple[str, ...]
    baseline_score: float
    baseline_rank: int
    kind: CandidateKind = CandidateKind.WORD
    segments: tuple[Segment, ...] = ()
    breakdown: ScoreBreakdown | None = None
    correction: ReadingCorrection | None = None

    @property
    def candidate_id(self) -> str:
        return f"c{self.baseline_rank}"
