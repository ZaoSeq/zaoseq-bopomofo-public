from __future__ import annotations

import pytest

from conftest import entry
from zaoseq_bopomofo.lexicon.builder import BuiltinRow, build_lexicon
from zaoseq_bopomofo.lexicon.entry import CharReading, EntrySource, LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import DuplicateEntryError, Lexicon

CHARS = (
    CharReading("載", "ㄗㄞˋ", "1-6725"),
    CharReading("載", "ㄗㄞˇ", "1-6725"),
    CharReading("在", "ㄗㄞˋ", "1-4763"),
    CharReading("貨", "ㄏㄨㄛˋ", "1-5A6F"),
    CharReading("罕", "ㄏㄢˇ", "3-2121"),
)


def test_polyphonic_char_has_one_entry_per_reading() -> None:
    report = build_lexicon(CHARS, ())
    assert [e.text for e in report.lexicon.lookup(("ㄗㄞˋ",))] == ["在", "載"]
    assert [e.text for e in report.lexicon.lookup(("ㄗㄞˇ",))] == ["載"]


def test_missing_reading_is_empty_tuple() -> None:
    assert build_lexicon(CHARS, ()).lexicon.lookup(("ㄅㄚ",)) == ()


def test_rare_plane_excluded_by_default() -> None:
    assert build_lexicon(CHARS, ()).lexicon.lookup(("ㄏㄢˇ",)) == ()


def test_duplicate_entry_rejected() -> None:
    with pytest.raises(DuplicateEntryError):
        Lexicon([entry("在", "ㄗㄞˋ", 1), entry("在", "ㄗㄞˋ", 2)])


def test_duplicate_builtin_row_reported() -> None:
    rows = (BuiltinRow("在", 5, ("ㄗㄞˋ",), 1), BuiltinRow("在", 4, ("ㄗㄞˋ",), 2))
    assert any("重複" in e for e in build_lexicon(CHARS, rows).errors)


def test_builtin_overrides_cns_weight() -> None:
    report = build_lexicon(CHARS, (BuiltinRow("載", 5, ("ㄗㄞˋ",), 1),))
    top = report.lexicon.lookup(("ㄗㄞˋ",))[0]
    assert (top.text, top.source) == ("載", EntrySource.BUILTIN)


def test_ambiguous_word_requires_explicit_reading() -> None:
    report = build_lexicon(CHARS, (BuiltinRow("載貨", 3, None, 7),))
    assert report.errors and "多音字" in report.errors[0]
    ok = build_lexicon(CHARS, (BuiltinRow("載貨", 3, ("ㄗㄞˋ", "ㄏㄨㄛˋ"), 7),))
    assert ok.errors == ()
    assert ok.lexicon.lookup(("ㄗㄞˋ", "ㄏㄨㄛˋ"))[0].text == "載貨"


def test_reading_not_in_cns_is_error() -> None:
    report = build_lexicon(CHARS, (BuiltinRow("在", 3, ("ㄗㄞˇ",), 1),))
    assert "不在 CNS11643" in report.errors[0]


def test_deterministic_order_ties_by_code_point() -> None:
    lexicon = Lexicon([entry("乙", "ㄧˇ", 5), entry("以", "ㄧˇ", 5), entry("已", "ㄧˇ", 9)])
    assert [e.text for e in lexicon.lookup(("ㄧˇ",))] == ["已", "乙", "以"]


def test_entry_validation() -> None:
    with pytest.raises(ValueError):
        LexiconEntry("天氣", ("ㄊㄧㄢ",), 1.0, EntrySource.BUILTIN)
    with pytest.raises(ValueError):
        LexiconEntry("天", ("ㄊㄧㄢ",), 0.0, EntrySource.BUILTIN)
