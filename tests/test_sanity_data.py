from __future__ import annotations

from pathlib import Path

from zaoseq_bopomofo.decoding.generator import CandidateGenerator
from zaoseq_bopomofo.evaluation.dataset import build_cases, load_scenarios
from zaoseq_bopomofo.lexicon.loader import load_lexicon

ROOT = Path(__file__).resolve().parents[1]


def test_sanity_cases_exist_in_decoder_output() -> None:
    """sanity 句子必須能由 decoder 產生；這裡只驗資料與詞庫，不涉及模型。"""
    scenarios = load_scenarios(ROOT / "benchmarks" / "sanity" / "seeds.jsonl")
    categories = {tag for s in scenarios for tag in s.tags}
    assert len(scenarios) >= 21
    assert {"在再", "的得地", "他她它", "做作", "台臺", "多音字", "分詞"} <= categories
    built = build_cases(scenarios, CandidateGenerator(load_lexicon().lexicon))
    assert built.excluded == ()


def test_spec_sanity_case_is_present() -> None:
    scenarios = {s.case_id: s for s in load_scenarios(ROOT / "benchmarks" / "sanity" / "seeds.jsonl")}
    case = scenarios["s001"]
    assert (case.context, case.target + case.suffix) == ("我明天會", "再去台北")
    assert case.target_readings + case.suffix_readings == ("ㄗㄞˋ", "ㄑㄩˋ", "ㄊㄞˊ", "ㄅㄟˇ")
