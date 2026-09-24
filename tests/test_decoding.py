from __future__ import annotations

from zaoseq_bopomofo.decoding.candidate import CandidateKind
from zaoseq_bopomofo.decoding.decoder import Decoder
from zaoseq_bopomofo.decoding.generator import CandidateGenerator
from zaoseq_bopomofo.lexicon.lexicon import Lexicon


def test_empty_readings_and_unknown_reading(small_lexicon: Lexicon) -> None:
    generator = CandidateGenerator(small_lexicon)
    assert generator.candidates_for(()) == ()
    assert generator.candidates_for(("ㄅㄚ",)) == ()


def test_single_candidate(small_lexicon: Lexicon) -> None:
    candidates = CandidateGenerator(small_lexicon).candidates_for(("ㄣ",))
    assert [c.text for c in candidates] == ["嗯"]


def test_same_pronunciation_multiple_chars_in_frequency_order(small_lexicon: Lexicon) -> None:
    candidates = CandidateGenerator(small_lexicon).candidates_for(("ㄗㄞˋ",))
    assert [c.text for c in candidates] == ["在", "再", "載"]
    assert [c.baseline_rank for c in candidates] == [0, 1, 2]
    assert candidates[0].baseline_score > candidates[1].baseline_score


def test_polyphonic_char_only_under_matching_reading(small_lexicon: Lexicon) -> None:
    generator = CandidateGenerator(small_lexicon)
    assert [c.text for c in generator.candidates_for(("ㄗㄞˇ",))] == ["載"]


def test_equal_frequency_words_tie_by_code_point(small_lexicon: Lexicon) -> None:
    texts = [c.text for c in CandidateGenerator(small_lexicon).candidates_for(("ㄍㄨㄥ", "ㄕˋ"))]
    assert texts[:2] == sorted(["公式", "公事"])


def test_compositions_when_no_whole_word(small_lexicon: Lexicon) -> None:
    candidates = CandidateGenerator(small_lexicon).candidates_for(("ㄗㄞˋ", "ㄑㄩˋ"))
    assert candidates[0].text == "在去"
    assert all(c.kind is CandidateKind.COMPOSITION for c in candidates)
    assert len({c.text for c in candidates}) == len(candidates)


def test_word_beats_split(small_lexicon: Lexicon) -> None:
    compositions = Decoder(small_lexicon).decode(("ㄊㄧㄢ", "ㄑㄧˋ"))
    assert compositions[0].text == "天氣"
    assert len(compositions[0].segments) == 1


def test_decoder_returns_empty_when_reading_not_coverable(small_lexicon: Lexicon) -> None:
    assert Decoder(small_lexicon).decode(("ㄗㄞˋ", "ㄅㄚ")) == ()
