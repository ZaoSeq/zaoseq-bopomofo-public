from __future__ import annotations

import pytest

from zaoseq_bopomofo.phonetics.keyboard import StandardKeyboardLayout, SymbolKey, ToneKey
from zaoseq_bopomofo.phonetics.parser import (
    ComposeStatus,
    InvalidBopomofoError,
    SyllableComposer,
    parse_reading,
    parse_syllable,
)
from zaoseq_bopomofo.phonetics.symbol import Tone


def test_single_syllable_without_tone_mark_is_first_tone() -> None:
    syllable = parse_syllable("ㄓㄨㄥ")
    assert (syllable.initial, syllable.medial, syllable.final, syllable.tone) == ("ㄓ", "ㄨ", "ㄥ", Tone.FIRST)
    assert syllable.text() == "ㄓㄨㄥ"


@pytest.mark.parametrize(
    ("text", "tone", "canonical"),
    [
        ("ㄗㄞˋ", Tone.FOURTH, "ㄗㄞˋ"),
        ("ㄇㄚˊ", Tone.SECOND, "ㄇㄚˊ"),
        ("ㄋㄧˇ", Tone.THIRD, "ㄋㄧˇ"),
        ("˙ㄌㄜ", Tone.NEUTRAL, "ㄌㄜ˙"),
        ("ㄌㄜ˙", Tone.NEUTRAL, "ㄌㄜ˙"),
        ("ㄇㄚˉ", Tone.FIRST, "ㄇㄚ"),
    ],
)
def test_tones(text: str, tone: Tone, canonical: str) -> None:
    syllable = parse_syllable(text)
    assert syllable.tone is tone
    assert syllable.text() == canonical


@pytest.mark.parametrize("text", ["", "ˋ", "ㄗA", "ㄞㄗ", "ㄅㄆ", "ㄧㄨ", "˙ㄌㄜˋ"])
def test_invalid_syllables(text: str) -> None:
    with pytest.raises(InvalidBopomofoError):
        parse_syllable(text)


def test_inventory_rejects_unknown_combination() -> None:
    with pytest.raises(InvalidBopomofoError):
        parse_syllable("ㄅㄩ", inventory={"ㄅㄚ"})


def test_multiple_syllables() -> None:
    readings = parse_reading("ㄐㄧㄣ ㄊㄧㄢ ㄊㄧㄢ-ㄑㄧˋㄏㄣˇㄏㄠˇ")
    assert [s.text() for s in readings] == ["ㄐㄧㄣ", "ㄊㄧㄢ", "ㄊㄧㄢ", "ㄑㄧˋ", "ㄏㄣˇ", "ㄏㄠˇ"]


def test_composer_incomplete_then_complete() -> None:
    composer = SyllableComposer()
    assert composer.push_symbol("ㄗ").status is ComposeStatus.ACCEPTED
    assert composer.push_symbol("ㄞ").status is ComposeStatus.ACCEPTED
    assert not composer.current.is_complete
    assert composer.current.tone is None
    result = composer.push_tone(Tone.FOURTH)
    assert result.status is ComposeStatus.COMPLETED
    assert result.syllable.text() == "ㄗㄞˋ"
    assert composer.current.is_empty


def test_composer_replaces_same_slot() -> None:
    composer = SyllableComposer()
    composer.push_symbol("ㄅ")
    composer.push_symbol("ㄆ")
    assert composer.current.initial == "ㄆ"


def test_composer_rejects_tone_without_body_and_invalid_symbol() -> None:
    composer = SyllableComposer()
    assert composer.push_tone(Tone.THIRD).status is ComposeStatus.REJECTED
    assert composer.push_symbol("A").status is ComposeStatus.REJECTED


def test_composer_inventory_rejection_keeps_state() -> None:
    composer = SyllableComposer(inventory={"ㄅㄚ"})
    composer.push_symbol("ㄅ")
    composer.push_symbol("ㄩ")
    result = composer.push_tone(Tone.FIRST)
    assert result.status is ComposeStatus.REJECTED
    assert composer.current.body == "ㄅㄩ"


def test_backspace_removes_right_to_left() -> None:
    composer = SyllableComposer()
    for symbol in ("ㄓ", "ㄨ", "ㄥ"):
        composer.push_symbol(symbol)
    assert composer.backspace()
    assert composer.current.body == "ㄓㄨ"
    assert composer.backspace()
    assert composer.backspace()
    assert composer.current.is_empty
    assert composer.backspace() is False


def test_standard_keyboard_layout() -> None:
    layout = StandardKeyboardLayout()
    assert layout.map_key("s") == SymbolKey("ㄋ")
    assert layout.map_key("U") == SymbolKey("ㄧ")
    assert layout.map_key("3") == ToneKey(Tone.THIRD)
    assert layout.map_key(" ") == ToneKey(Tone.FIRST)
    assert layout.map_key("Enter") is None
