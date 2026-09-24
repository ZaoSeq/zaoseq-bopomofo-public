"""從 repo 內的資料檔載入預設詞庫。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.lexicon.builder import (
    FrequencyConfig,
    build_lexicon,
    read_builtin,
    read_char_readings,
)
from zaoseq_bopomofo.lexicon.lexicon import Lexicon

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHAR_READINGS = PROJECT_ROOT / "data" / "cns11643" / "cns_char_readings.tsv"
DEFAULT_BUILTIN = PROJECT_ROOT / "data" / "builtin" / "lexicon.tsv"


class LexiconBuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadedLexicon:
    """`syllables` 是 CNS11643 所有讀音，比 `lexicon.syllables` 大：
    只存在於罕用字面的音節仍然是合法輸入，只是查不到預設候選。"""

    lexicon: Lexicon
    syllables: frozenset[str]


def load_lexicon(
    char_readings_path: Path = DEFAULT_CHAR_READINGS,
    builtin_path: Path = DEFAULT_BUILTIN,
    config: FrequencyConfig | None = None,
) -> LoadedLexicon:
    if not char_readings_path.exists():
        raise LexiconBuildError(
            f"找不到 {char_readings_path}；請先執行 "
            "`python -m zaoseq_bopomofo.lexicon.builder data/raw/cns11643 data/cns11643/cns_char_readings.tsv`"
        )
    char_readings = read_char_readings(char_readings_path)
    report = build_lexicon(char_readings, read_builtin(builtin_path), config)
    if report.errors:
        raise LexiconBuildError("builtin lexicon 有錯誤：\n" + "\n".join(report.errors))
    return LoadedLexicon(lexicon=report.lexicon, syllables=frozenset(r.reading for r in char_readings))
