from __future__ import annotations

import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.daily.experiments import RESULTS
from zaoseq_bopomofo.daily.lexicon import LEXICON_DIR
from zaoseq_bopomofo.daily.round2 import LexiconArtifacts, Round2Config, Round2Runner, winner
from zaoseq_bopomofo.daily.sources import sha256_file
from zaoseq_bopomofo.lexicon.loader import PROJECT_ROOT

ADDENDUM = PROJECT_ROOT / "benchmarks" / "frozen" / "v0.2_round3_addendum.json"
ARTIFACT_DIR = LEXICON_DIR / "round3"
TATOEBA = "tatoeba_cmn_hant"
COMMON_VOICE = "mdc_common_voice_zh_tw_27_0"


@dataclass(frozen=True)
class CorpusCandidate:
    """一個 stage-5 候選：日常 LM 名稱與詞庫統計使用的日常來源。"""

    name: str
    daily_lm: str
    sources: tuple[str, ...]


CANDIDATES = (
    CorpusCandidate("S5_tatoeba", TATOEBA, (TATOEBA,)),
    CorpusCandidate("S5_common_voice", COMMON_VOICE, (COMMON_VOICE,)),
    CorpusCandidate("S5_tatoeba_common_voice", "daily_production", (TATOEBA, COMMON_VOICE)),
)


def available_candidates(production_sources: set[str], lm_sources: Callable[[str], set[str]]) -> list[CorpusCandidate]:
    """只保留來源都已核准 production、且 LM 恰好由這些來源建成的候選；CV 未核准時只剩 S5_tatoeba。"""
    return [c for c in CANDIDATES if set(c.sources) <= production_sources and lm_sources(c.daily_lm) == set(c.sources)]


def lm_sources(name: str) -> set[str]:
    from zaoseq_bopomofo.daily.corpus import LM_DIR

    manifest = LM_DIR / name / "manifest.json"
    return set(json.loads(manifest.read_text(encoding="utf-8"))["sources"]) if manifest.exists() else set()


class CorpusAblationRunner(Round2Runner):
    """Round 2 的評估流程；每個候選各自用自己的日常來源重建詞庫統計與 artifact。"""

    def __init__(self, log: Callable[[str], None], candidates: Sequence[CorpusCandidate]) -> None:
        super().__init__(log)
        self._default_artifacts = self.artifacts
        self.candidate_artifacts: dict[str, LexiconArtifacts] = {
            c.name: self.lexicon_artifacts(self.candidate_statistics(set(c.sources)), ARTIFACT_DIR / c.name) for c in candidates
        }

    def run(self, config: Round2Config):  # type: ignore[no-untyped-def]
        self.artifacts = self.candidate_artifacts.get(config.name, self._default_artifacts)
        try:
            return super().run(config)
        finally:
            self.artifacts = self._default_artifacts


class GoldWordRanks:
    """Coverage-DEV gold 多字詞在同讀音同長度詞之間的名次（詞庫順序即先驗大小），比較各候選詞庫。"""

    def __init__(self, cases: Sequence[object]) -> None:
        self._spans = [
            (case.readings[start:end], word.text)  # type: ignore[attr-defined]
            for case in cases
            if case.item is not None  # type: ignore[attr-defined]
            for start, end, word in case.item.word_spans()  # type: ignore[attr-defined]
            if end - start >= 2
        ]

    def ranks(self, lexicon: object) -> dict[str, int]:
        out: dict[str, int] = {}
        for readings, gold in self._spans:
            texts = [e.text for e in lexicon.lookup(readings) if len(e.text) == len(gold)]  # type: ignore[attr-defined]
            if gold in texts and len(texts) > 1:
                out[f"{gold}|{' '.join(readings)}"] = texts.index(gold) + 1
        return out

    def compare(self, lexicons: dict[str, object], baseline: str) -> dict[str, object]:
        ranks = {name: self.ranks(lexicon) for name, lexicon in lexicons.items()}
        summary = {
            name: {"contested_gold_words": len(r), "gold_ranked_first": sum(v == 1 for v in r.values()), "mean_rank": round(sum(r.values()) / len(r), 4) if r else 0.0}
            for name, r in ranks.items()
        }
        changes: dict[str, dict[str, list[str]]] = {}
        for name, r in ranks.items():
            if name == baseline:
                continue
            base = ranks[baseline]
            shared = set(r) & set(base)
            changes[name] = {
                "better_than_baseline": sorted(k for k in shared if r[k] < base[k]),
                "worse_than_baseline": sorted(k for k in shared if r[k] > base[k]),
            }
        return {"baseline": baseline, "summary": summary, "changes": changes}


def reproduces_round2(runner: CorpusAblationRunner, recipe: object) -> dict[str, object]:
    """S5_tatoeba 的 artifact 應與 Round 2 winner 的 artifact 位元相同（語料未變時）。"""
    from zaoseq_bopomofo.daily.round2 import ARTIFACT_DIR as ROUND2_DIR

    artifacts = runner.candidate_artifacts.get("S5_tatoeba")
    if artifacts is None:
        return {"checked": False}
    round2 = ROUND2_DIR / f"{LexiconArtifacts.slug(recipe)}.bin"  # type: ignore[arg-type]
    current = artifacts.path(recipe)  # type: ignore[arg-type]
    return {"checked": True, "round2_sha256": sha256_file(round2), "s5_tatoeba_sha256": sha256_file(current), "identical": sha256_file(round2) == sha256_file(current)}


def main(output: str | None = None) -> int:
    from zaoseq_bopomofo.daily.clean_lexicon import DailyOnlyPrior, DocumentFrequencyFilter, KnownWordReadings, LexiconRecipe
    from zaoseq_bopomofo.daily.corpus import production_source_ids
    from zaoseq_bopomofo.evaluation.freeze import content_hash

    def log(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    weight = float(addendum["stage5_corpus_ablation"]["stage4_weight"])
    production = production_source_ids()
    candidates = available_candidates(production, lm_sources)
    runner = CorpusAblationRunner(log, candidates)
    recipe = LexiconRecipe(KnownWordReadings(runner.evidence), DocumentFrequencyFilter(), DailyOnlyPrior())
    reference = Round2Config("A_v0", "reference", None, 0.0, None, True)
    runner.run(reference)
    configs = [Round2Config(c.name, "5_corpus_ablation", c.daily_lm, weight, recipe, True) for c in candidates]
    for config in configs:
        runner.run(config)
    selection = runner.select([c.name for c in configs])
    log(f"[select] stage 5 -> {winner(selection)}")
    lexicons = {c.name: runner.candidate_artifacts[c.name].get(recipe)[0] for c in candidates}
    report = {
        "addendum_sha256": content_hash(ADDENDUM),
        "plan_sha256": runner.plan.sha256,
        "production_daily_sources": sorted(production),
        "candidates": [{"name": c.name, "daily_lm": c.daily_lm, "sources": list(c.sources)} for c in candidates],
        "skipped": [c.name for c in CANDIDATES if c not in candidates],
        "recipe": recipe.name,
        "daily_weight": weight,
        "selection": selection,
        "round2_reproduction": reproduces_round2(runner, recipe),
        "gold_word_ranks": GoldWordRanks(runner.evaluator.sets["coverage_dev"]).compare(lexicons, "S5_tatoeba"),
        "lexicons": {name: artifacts.get(recipe)[1] for name, artifacts in runner.candidate_artifacts.items()},
        "results": runner.results,
    }
    path = Path(output) if output else RESULTS / "daily_round3_stage5_raw.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    log(f"[written] {path}")
    return 0
