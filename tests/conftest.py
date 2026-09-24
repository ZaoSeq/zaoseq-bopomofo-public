"""共用測試工具：假 backend 與小型合成詞庫，不需要 GPU、網路或 Laya 權重。"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping

import pytest

from zaoseq_bopomofo.decoding.candidate import Candidate
from zaoseq_bopomofo.lexicon.entry import EntrySource, LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon
from zaoseq_bopomofo.ranking.base import RankingContext
from zaoseq_bopomofo.ranking.contextual import ChoiceDistribution, ChoiceRequest

Responder = Callable[[ChoiceRequest], Mapping[str, object]]


class FakeBackend:
    def __init__(
        self,
        responder: Responder | None = None,
        confidence: object = 0.5,
        error: Exception | None = None,
        block: threading.Event | None = None,
    ) -> None:
        self._responder = responder
        self._confidence = confidence
        self._error = error
        self._block = block
        self.requests: list[ChoiceRequest] = []

    @property
    def model_name(self) -> str:
        return "fake-model"

    def decide(self, request: ChoiceRequest) -> ChoiceDistribution:
        self.requests.append(request)
        if self._block is not None:
            self._block.wait(timeout=5.0)
        if self._error is not None:
            raise self._error
        probabilities = dict(self._responder(request)) if self._responder else {}
        return ChoiceDistribution("fake-model", probabilities, self._confidence)  # type: ignore[arg-type]


def prefer(text: str, top: float = 0.7) -> Responder:
    """把 `text` 設為最高機率，其餘平分。"""

    def responder(request: ChoiceRequest) -> Mapping[str, object]:
        others = [o for o in request.options if o.text != text]
        rest = (1.0 - top) / len(others) if others else 0.0
        return {o.candidate_id: top if o.text == text else rest for o in request.options}

    return responder


def make_candidates(texts: list[str], scores: list[float] | None = None) -> tuple[Candidate, ...]:
    values = scores or [-1.0 - 0.5 * i for i in range(len(texts))]
    return tuple(
        Candidate(text=t, readings=("ㄗㄞˋ",), baseline_score=s, baseline_rank=i)
        for i, (t, s) in enumerate(zip(texts, values))
    )


CONTEXT = RankingContext(left_context="我明天會", readings=("ㄗㄞˋ",))


@pytest.fixture
def zai() -> tuple[Candidate, ...]:
    return make_candidates(["在", "再", "載"], [-2.0, -2.7, -3.3])


def entry(text: str, readings: str, frequency: float, source: EntrySource = EntrySource.BUILTIN) -> LexiconEntry:
    return LexiconEntry(text=text, readings=tuple(readings.split()), frequency=frequency, source=source)


@pytest.fixture
def small_lexicon() -> Lexicon:
    return Lexicon(
        [
            entry("在", "ㄗㄞˋ", 1000),
            entry("再", "ㄗㄞˋ", 200),
            entry("載", "ㄗㄞˋ", 50),
            entry("載", "ㄗㄞˇ", 10),
            entry("去", "ㄑㄩˋ", 1000),
            entry("趣", "ㄑㄩˋ", 50),
            entry("天", "ㄊㄧㄢ", 1000),
            entry("氣", "ㄑㄧˋ", 200),
            entry("器", "ㄑㄧˋ", 50),
            entry("天氣", "ㄊㄧㄢ ㄑㄧˋ", 200),
            entry("公式", "ㄍㄨㄥ ㄕˋ", 50),
            entry("公事", "ㄍㄨㄥ ㄕˋ", 50),
            entry("攻勢", "ㄍㄨㄥ ㄕˋ", 10),
            entry("嗯", "ㄣ", 3),
        ]
    )
