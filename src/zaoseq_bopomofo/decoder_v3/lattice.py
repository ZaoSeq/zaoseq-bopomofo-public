from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from zaoseq_bopomofo.coverage.lattice import Generation, GenerationConfig, Timing, Trace
from zaoseq_bopomofo.decoding.candidate import Candidate, CandidateKind, Segment
from zaoseq_bopomofo.decoding.scoring import LinearScorer, ScoreBreakdown
from zaoseq_bopomofo.decoder_v3.script_guard import ScriptGuard


@dataclass(frozen=True)
class _Hyp:
    total: float
    corpus: float
    lexical: float
    text: str
    history: str
    segments: tuple[Segment, ...]


class GuardedLattice:
    """與 CoverageLattice 相同的 beam 搜尋，另有兩點：
    history 由語言模型自己的 initial_history 決定（高階模型能看到更長的前文）；
    任何擴展只要組出簡體字元或簡體詞形（含跨詞邊界）就直接丟棄，不進 beam；需要後文佐證的位置在完整候選時再判定。"""

    def __init__(self, lexicon: object, language_model: object, scorer: LinearScorer, guard: ScriptGuard | None, config: GenerationConfig | None = None) -> None:
        self._lexicon = lexicon
        self._lm = language_model
        self._scorer = scorer
        self._guard = guard
        self.config = config or GenerationConfig()
        self.rejected = 0

    def generate(
        self,
        readings: Sequence[str],
        left_context: str = "",
        gold_keys: Callable[[str], bool] | None = None,
        gold_prefix: Callable[[int, Iterable[str]], bool] | None = None,
    ) -> Generation:
        cfg = self.config
        observed = tuple(readings)
        n = len(observed)
        trace = Trace() if gold_prefix is not None else None
        if n == 0:
            return Generation((), trace, Timing())
        start = _Hyp(0.0, 0.0, 0.0, "", self._lm.initial_history(left_context), ())  # type: ignore[attr-defined]
        beams: list[dict[str, _Hyp]] = [dict() for _ in range(n + 1)]
        beams[0][""] = start
        max_len = max(1, self._lexicon.max_word_length)  # type: ignore[attr-defined]
        for position in range(n):
            pool = beams[position].values()
            frontier = sorted(pool, key=lambda h: (-h.total, h.text))[: cfg.beam]
            if trace is not None:
                trace.generated.append(gold_prefix(position, beams[position].keys()))  # type: ignore[misc]
                trace.kept.append(gold_prefix(position, (h.text for h in frontier)))  # type: ignore[misc]
            for hypothesis in frontier:
                for length in range(1, min(max_len, n - position) + 1):
                    span = observed[position : position + length]
                    self._extend(beams[position + length], hypothesis, span, self._lexicon.lookup(span))  # type: ignore[attr-defined]
        ordered = sorted(beams[n].values(), key=lambda h: (-h.total, h.text))
        if self._guard is not None:
            kept = [h for h in ordered if not self._guard.violates(h.text, 0, final=True)]
            self.rejected += len(ordered) - len(kept)
            ordered = kept
        candidates = tuple(
            Candidate(
                text=h.text,
                readings=observed,
                baseline_score=h.total,
                baseline_rank=rank,
                kind=CandidateKind.WORD if len(h.segments) == 1 else CandidateKind.COMPOSITION,
                segments=h.segments,
                breakdown=ScoreBreakdown(0.0, h.lexical, h.corpus),
            )
            for rank, h in enumerate(ordered[: cfg.nbest])
        )
        if trace is not None:
            trace.complete_hypotheses = len(ordered)
            trace.generated.append(gold_prefix(n, beams[n].keys()))  # type: ignore[misc]
            trace.kept.append(trace.generated[-1])
            if gold_keys is not None:
                trace.final_rank = next((i for i, h in enumerate(ordered) if gold_keys(h.text)), None)
        return Generation(candidates, trace, Timing())

    def _extend(self, target: dict[str, _Hyp], hypothesis: _Hyp, span: tuple[str, ...], entries: Sequence[object]) -> None:
        for entry in entries:
            text = hypothesis.text + entry.text  # type: ignore[attr-defined]
            if self._guard is not None and self._guard.violates(text, len(hypothesis.text)):
                self.rejected += 1
                continue
            corpus, history = hypothesis.corpus, hypothesis.history
            for char in entry.text:  # type: ignore[attr-defined]
                delta, history = self._lm.extend(history, char)  # type: ignore[attr-defined]
                corpus += delta
            lexical = hypothesis.lexical + self._lexicon.log10_probability(entry)  # type: ignore[attr-defined]
            candidate = _Hyp(self._scorer.total(ScoreBreakdown(-0.0, lexical, corpus)), corpus, lexical, text, history, hypothesis.segments + (Segment(entry.text, span),))  # type: ignore[attr-defined]
            existing = target.get(text)
            if existing is None or (candidate.total, candidate.text) > (existing.total, existing.text):
                target[text] = candidate
