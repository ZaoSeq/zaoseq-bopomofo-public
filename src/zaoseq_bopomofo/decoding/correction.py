"""讀音修正的資料型別。只有資料，讓 candidate、error model 與 API 共用。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorSource(Enum):
    """錯誤來源分開記錄：發音混淆與鍵盤誤按的成因不同，成本與分析也不同。"""

    TONE = "tone"
    PRONUNCIATION = "pronunciation"
    KEYBOARD = "keyboard"


class ErrorKind(Enum):
    TONE_MISSING = "tone_missing"
    TONE_WRONG = "tone_wrong"
    PHONETIC_CONFUSION = "phonetic_confusion"
    ADJACENT_KEY = "adjacent_key"
    SUBSTITUTION = "substitution"
    INSERTION = "insertion"
    DELETION = "deletion"
    TRANSPOSITION = "transposition"


@dataclass(frozen=True)
class ReadingEdit:
    """把使用者輸入的 `observed` 音節解讀為 `inferred`。

    INSERTION 表示使用者多按了一個符號（所以 inferred 少一個符號），DELETION 表示漏按。
    TRANSPOSITION 的 position 是兩個對調音節中較前面那個。
    """

    kind: ErrorKind
    source: ErrorSource
    position: int
    observed: str
    inferred: str
    cost: float


@dataclass(frozen=True)
class ReadingCorrection:
    original: tuple[str, ...]
    inferred: tuple[str, ...]
    operations: tuple[ReadingEdit, ...]
    cost: float
