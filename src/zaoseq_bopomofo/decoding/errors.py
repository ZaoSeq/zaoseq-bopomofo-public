"""ReadingErrorModel：列出一個觀察到的音節「可能其實是」哪些音節，以及對應的修正成本。"""

from __future__ import annotations

from collections.abc import Container
from dataclasses import dataclass, replace

from zaoseq_bopomofo.decoding.correction import ErrorKind, ErrorSource, ReadingEdit
from zaoseq_bopomofo.phonetics.keyboard import StandardKeyboardLayout
from zaoseq_bopomofo.phonetics.parser import InvalidBopomofoError, parse_syllable
from zaoseq_bopomofo.phonetics.symbol import FINALS, INITIALS, MEDIALS, Tone
from zaoseq_bopomofo.phonetics.syllable import BopomofoSyllable

# 台灣華語常見的發音混淆：捲舌／平舌、前後鼻音、ㄈㄏ、ㄌㄋ、ㄖㄌ。這是公開的語音常識，不是從任何詞庫取得。
PHONETIC_CONFUSIONS: tuple[tuple[str, str], ...] = (
    ("ㄓ", "ㄗ"),
    ("ㄔ", "ㄘ"),
    ("ㄕ", "ㄙ"),
    ("ㄣ", "ㄥ"),
    ("ㄢ", "ㄤ"),
    ("ㄈ", "ㄏ"),
    ("ㄌ", "ㄋ"),
    ("ㄖ", "ㄌ"),
)
_SLOTS = ("initial", "medial", "final")
_SLOT_SYMBOLS = {"initial": INITIALS, "medial": MEDIALS, "final": FINALS}


@dataclass(frozen=True)
class ErrorCosts:
    """log10 尺度的懲罰；事前選定，不依個別案例調整。
    數值越大代表越不可能：漏標聲調最常見，任意替換最罕見。"""

    tone_missing: float = 1.0
    tone_wrong: float = 1.5
    phonetic_confusion: float = 1.5
    adjacent_key: float = 2.0
    insertion: float = 2.5
    deletion: float = 2.5
    substitution: float = 3.0
    transposition: float = 2.0


@dataclass(frozen=True)
class SyllableAlternative:
    reading: str
    edit: ReadingEdit


class ReadingErrorModel:
    """只產生 edit distance 1（單一音節內一個操作）的替代讀音，且結果必須是 inventory 中的音節。

    同一個替代讀音可由多種操作得到時（例如相鄰鍵剛好也是發音混淆），保留成本最低的解釋。
    """

    def __init__(
        self,
        inventory: Container[str],
        costs: ErrorCosts | None = None,
        layout: StandardKeyboardLayout | None = None,
    ) -> None:
        self._inventory = inventory
        self._costs = costs or ErrorCosts()
        self._layout = layout or StandardKeyboardLayout()
        confusion: dict[str, set[str]] = {}
        for a, b in PHONETIC_CONFUSIONS:
            confusion.setdefault(a, set()).add(b)
            confusion.setdefault(b, set()).add(a)
        self._confusion = confusion
        self._cache: dict[tuple[str, int], tuple[SyllableAlternative, ...]] = {}

    @property
    def costs(self) -> ErrorCosts:
        return self._costs

    def alternatives(self, observed: str, position: int) -> tuple[SyllableAlternative, ...]:
        key = (observed, position)
        if key not in self._cache:
            self._cache[key] = self._compute(observed, position)
        return self._cache[key]

    def _compute(self, observed: str, position: int) -> tuple[SyllableAlternative, ...]:
        try:
            syllable = parse_syllable(observed)
        except InvalidBopomofoError:
            return ()
        best: dict[str, ReadingEdit] = {}

        def offer(candidate: BopomofoSyllable, kind: ErrorKind, source: ErrorSource, cost: float) -> None:
            if not candidate.has_body or candidate.tone is None:
                return
            text = candidate.text()
            if text == observed or text not in self._inventory:
                return
            current = best.get(text)
            if current is None or cost < current.cost:
                best[text] = ReadingEdit(kind, source, position, observed, text, cost)

        c = self._costs
        for tone in Tone:
            if tone is syllable.tone:
                continue
            if syllable.tone is Tone.FIRST:
                offer(replace(syllable, tone=tone), ErrorKind.TONE_MISSING, ErrorSource.TONE, c.tone_missing)
            else:
                offer(replace(syllable, tone=tone), ErrorKind.TONE_WRONG, ErrorSource.TONE, c.tone_wrong)

        for slot in _SLOTS:
            current = getattr(syllable, slot)
            if current is None:
                # 漏按：這一格原本應該有符號。
                for symbol in _SLOT_SYMBOLS[slot]:
                    offer(replace(syllable, **{slot: symbol}), ErrorKind.DELETION, ErrorSource.KEYBOARD, c.deletion)
                continue
            # 多按：這一格的符號其實不該存在。
            offer(replace(syllable, **{slot: None}), ErrorKind.INSERTION, ErrorSource.KEYBOARD, c.insertion)
            for symbol in self._confusion.get(current, ()):
                if symbol in _SLOT_SYMBOLS[slot]:
                    offer(
                        replace(syllable, **{slot: symbol}),
                        ErrorKind.PHONETIC_CONFUSION,
                        ErrorSource.PRONUNCIATION,
                        c.phonetic_confusion,
                    )
            for symbol in self._layout.adjacent_symbols(current):
                target_slot = next(s for s in _SLOTS if symbol in _SLOT_SYMBOLS[s])
                if target_slot == slot:
                    changed = replace(syllable, **{slot: symbol})
                elif getattr(syllable, target_slot) is None:
                    # 按到相鄰但不同類的鍵：原本的符號沒按到，錯按的符號落在另一格。
                    changed = replace(syllable, **{slot: None, target_slot: symbol})
                else:
                    continue
                offer(changed, ErrorKind.ADJACENT_KEY, ErrorSource.KEYBOARD, c.adjacent_key)
            for symbol in _SLOT_SYMBOLS[slot]:
                if symbol != current:
                    offer(replace(syllable, **{slot: symbol}), ErrorKind.SUBSTITUTION, ErrorSource.KEYBOARD, c.substitution)

        return tuple(
            SyllableAlternative(reading, edit)
            for reading, edit in sorted(best.items(), key=lambda item: (item[1].cost, item[0]))
        )

    def transposition(self, observed: tuple[str, ...], position: int) -> tuple[str, str, ReadingEdit] | None:
        """相鄰兩音節的聲調對調（例如 ㄋㄧˋ ㄏㄠˇ ← ㄋㄧˇ ㄏㄠˋ）；聲調相同或結果不合法時回傳 None。"""
        try:
            a, b = parse_syllable(observed[position]), parse_syllable(observed[position + 1])
        except (InvalidBopomofoError, IndexError):
            return None
        if a.tone is b.tone:
            return None
        first, second = replace(a, tone=b.tone).text(), replace(b, tone=a.tone).text()
        if first not in self._inventory or second not in self._inventory:
            return None
        edit = ReadingEdit(
            ErrorKind.TRANSPOSITION,
            ErrorSource.KEYBOARD,
            position,
            f"{observed[position]} {observed[position + 1]}",
            f"{first} {second}",
            self._costs.transposition,
        )
        return first, second, edit
