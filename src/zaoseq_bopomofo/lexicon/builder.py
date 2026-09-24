"""CNS11643 匯入與詞庫組建。

    python -m zaoseq_bopomofo.lexicon.builder data/raw/cns11643 data/cns11643/cns_char_readings.tsv
"""

from __future__ import annotations

import io
import itertools
import sys
import zipfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from zaoseq_bopomofo.lexicon.entry import CharReading, EntrySource, LexiconEntry
from zaoseq_bopomofo.lexicon.lexicon import Lexicon
from zaoseq_bopomofo.phonetics.parser import InvalidBopomofoError, parse_syllable

_PHONETIC_MEMBER = "CNS_phonetic.txt"
# 第 15 字面對照表指向 Unicode 私用區，不是可攜的標準字元，因此不匯入。
_UNICODE_MEMBERS = (
    "Unicode/CNS2UNICODE_Unicode BMP.txt",
    "Unicode/CNS2UNICODE_Unicode 2.txt",
    "Unicode/CNS2UNICODE_Unicode 3.txt",
)

CHAR_READINGS_HEADER = (
    "# Derived from CNS11643 全字庫 (Ministry of Digital Affairs, Taiwan),\n"
    "# licensed under the Open Government Data License, version 1.0.\n"
    "# https://data.gov.tw/dataset/5961\n"
    "# columns: char\treading\tcns_code\n"
)


@dataclass(frozen=True)
class ImportReport:
    rows: tuple[CharReading, ...]
    unmapped_codes: int
    invalid_readings: tuple[str, ...]


def import_cns(properties_zip: Path, mapping_zip: Path) -> ImportReport:
    code_to_char = _read_unicode_map(mapping_zip)
    rows: set[CharReading] = set()
    unmapped = 0
    invalid: list[str] = []
    with zipfile.ZipFile(properties_zip) as archive:
        text = archive.read(_PHONETIC_MEMBER).decode("utf-8-sig")
    for line in text.splitlines():
        if not line.strip():
            continue
        code, raw_reading = line.split("\t")
        char = code_to_char.get(code)
        if char is None:
            unmapped += 1
            continue
        try:
            reading = parse_syllable(raw_reading).text()
        except InvalidBopomofoError:
            invalid.append(f"{code}\t{raw_reading}")
            continue
        rows.add(CharReading(char=char, reading=reading, cns_code=code))
    ordered = tuple(sorted(rows, key=lambda r: (r.plane, r.cns_code, r.reading)))
    return ImportReport(rows=ordered, unmapped_codes=unmapped, invalid_readings=tuple(invalid))


def _read_unicode_map(mapping_zip: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with zipfile.ZipFile(mapping_zip) as archive:
        for member in _UNICODE_MEMBERS:
            with archive.open(member) as handle:
                for line in io.TextIOWrapper(handle, encoding="utf-8-sig"):
                    parts = line.split()
                    if len(parts) == 2:
                        mapping[parts[0]] = chr(int(parts[1], 16))
    return mapping


def write_char_readings(rows: Iterable[CharReading], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(CHAR_READINGS_HEADER)
        for row in rows:
            handle.write(f"{row.char}\t{row.reading}\t{row.cns_code}\n")


def read_char_readings(path: Path) -> tuple[CharReading, ...]:
    rows: list[CharReading] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        char, reading, code = line.split("\t")
        rows.append(CharReading(char=char, reading=reading, cns_code=code))
    return tuple(rows)


@dataclass(frozen=True)
class BuiltinRow:
    """人工維護詞表的一列。`readings` 為 None 時由 CNS 單字讀音推導。"""

    text: str
    tier: int
    readings: tuple[str, ...] | None
    line_number: int


def read_builtin(path: Path) -> tuple[BuiltinRow, ...]:
    rows: list[BuiltinRow] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("\t")
        if len(parts) not in (2, 3):
            raise ValueError(f"{path}:{number}: 欄位數應為 2 或 3")
        readings = None
        if len(parts) == 3 and parts[2].strip():
            readings = tuple(parse_syllable(s).text() for s in parts[2].split())
        rows.append(BuiltinRow(text=parts[0], tier=int(parts[1]), readings=readings, line_number=number))
    return tuple(rows)


@dataclass(frozen=True)
class FrequencyConfig:
    """人工等級與 CNS 字面到相對權重的換算。

    builtin 等級是人工判斷的常用程度，不是語料統計；CNS 字面 1、2 大致對應常用字與次常用字，
    只作為沒有人工等級時的弱先驗，所以權重刻意低於 builtin 最低等級。
    """

    tier_weights: Mapping[int, float] = field(
        default_factory=lambda: {5: 1000.0, 4: 200.0, 3: 50.0, 2: 10.0, 1: 3.0}
    )
    plane_weights: Mapping[int, float] = field(default_factory=lambda: {1: 1.0, 2: 0.1})


@dataclass(frozen=True)
class BuildReport:
    lexicon: Lexicon
    errors: tuple[str, ...]


def build_lexicon(
    char_readings: Sequence[CharReading],
    builtin: Sequence[BuiltinRow],
    config: FrequencyConfig | None = None,
) -> BuildReport:
    """合併 CNS 單字與 builtin 詞表。

    有問題的 builtin 列會記在 errors 而不是默默略過，呼叫端應把非空的 errors 視為建置失敗。
    """
    cfg = config or FrequencyConfig()
    readings_by_char: dict[str, list[str]] = {}
    weights: dict[tuple[str, tuple[str, ...]], tuple[float, EntrySource]] = {}
    for row in char_readings:
        plane_weight = cfg.plane_weights.get(row.plane)
        known = readings_by_char.setdefault(row.char, [])
        if row.reading not in known:
            known.append(row.reading)
        if plane_weight is None:
            continue
        key = (row.char, (row.reading,))
        # 同一字在多個 CNS 碼位出現時取較高權重，避免字面順序影響結果。
        previous = weights.get(key)
        if previous is None or plane_weight > previous[0]:
            weights[key] = (plane_weight, EntrySource.CNS11643)

    errors: list[str] = []
    for row in builtin:
        weight = cfg.tier_weights.get(row.tier)
        if weight is None:
            errors.append(f"line {row.line_number}: {row.text} 的等級 {row.tier} 未定義")
            continue
        resolved = _resolve_readings(row, readings_by_char)
        if isinstance(resolved, str):
            errors.append(f"line {row.line_number}: {resolved}")
            continue
        key = (row.text, resolved)
        if key in weights and weights[key][1] is EntrySource.BUILTIN:
            errors.append(f"line {row.line_number}: {row.text} {' '.join(resolved)} 重複")
            continue
        weights[key] = (weight, EntrySource.BUILTIN)

    entries = [
        LexiconEntry(text=text, readings=readings, frequency=weight, source=source)
        for (text, readings), (weight, source) in weights.items()
    ]
    return BuildReport(lexicon=Lexicon(entries), errors=tuple(errors))


def _resolve_readings(row: BuiltinRow, readings_by_char: Mapping[str, list[str]]) -> tuple[str, ...] | str:
    """回傳讀音，或錯誤訊息字串。"""
    options: list[list[str]] = []
    for char in row.text:
        known = readings_by_char.get(char)
        if not known:
            return f"{row.text}：「{char}」沒有 CNS11643 讀音"
        options.append(known)

    if row.readings is not None:
        if len(row.readings) != len(row.text):
            return f"{row.text}：讀音數與字數不一致"
        for char, reading, known in zip(row.text, row.readings, options):
            if reading not in known:
                return f"{row.text}：「{char}」的讀音 {reading} 不在 CNS11643（{'、'.join(known)}）"
        return row.readings

    combinations = list(itertools.islice(itertools.product(*options), 2))
    if len(combinations) > 1:
        ambiguous = [f"{c}={'/'.join(k)}" for c, k in zip(row.text, options) if len(k) > 1]
        return f"{row.text}：多音字需指定讀音（{'，'.join(ambiguous)}）"
    return tuple(combinations[0])


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    raw_dir, output = Path(argv[0]), Path(argv[1])
    report = import_cns(raw_dir / "Properties.zip", raw_dir / "MapingTables.zip")
    write_char_readings(report.rows, output)
    print(f"{len(report.rows)} char readings -> {output}")
    print(f"skipped: {report.unmapped_codes} codes without standard Unicode mapping, "
          f"{len(report.invalid_readings)} invalid readings")
    for item in report.invalid_readings:
        print(f"  invalid: {item}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
