from __future__ import annotations

import json
import math
import struct
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from zaoseq_bopomofo.lexicon.entry import EntrySource, LexiconEntry

MAGIC = b"ZSLEX001"
SOURCES = tuple(EntrySource)
NO_PROVENANCE = 0


@dataclass(frozen=True)
class LexiconSnapshot:
    """詞庫的完整內容，順序與 frozen Lexicon 內部相同（依讀音分組，組內 (-frequency, text)）。"""

    groups: tuple[tuple[tuple[str, ...], tuple[LexiconEntry, ...]], ...]
    total_frequency: float

    @classmethod
    def of(cls, lexicon: object) -> LexiconSnapshot:
        # frozen Lexicon 沒有列舉 API；只讀取它已排序的內部索引與分母，確保完全相同。
        by_reading: Mapping[tuple[str, ...], tuple[LexiconEntry, ...]] = lexicon._by_reading  # type: ignore[attr-defined]  # noqa: SLF001
        groups = tuple(sorted(by_reading.items()))
        return cls(groups, lexicon._total_frequency)  # type: ignore[attr-defined]  # noqa: SLF001


class CompactLexiconWriter:
    """二進位格式：magic、header 長度、JSON header、再依序存放各 little-endian 陣列。相同輸入產生逐位元組相同的檔案。

    執行期只存整數 provenance id；id → 來源的對照表寫在另一個 JSON（不在執行期載入）。"""

    def write(self, snapshot: LexiconSnapshot, path: Path, provenance: Mapping[str, int] | None = None) -> None:
        provenance = provenance or {}
        syllables = sorted({s for reading, _ in snapshot.groups for s in reading})
        syllable_id = {s: i for i, s in enumerate(syllables)}
        key_syllables: list[int] = []
        key_offsets = [0]
        entry_offsets = [0]
        text_blob = bytearray()
        text_offsets = [0]
        frequencies: list[float] = []
        sources: list[int] = []
        provenance_ids: list[int] = []
        for reading, entries in snapshot.groups:
            key_syllables.extend(syllable_id[s] for s in reading)
            key_offsets.append(len(key_syllables))
            for entry in entries:
                text_blob += entry.text.encode("utf-8")
                text_offsets.append(len(text_blob))
                frequencies.append(entry.frequency)
                sources.append(SOURCES.index(entry.source))
                provenance_ids.append(provenance.get(entry.text, NO_PROVENANCE) if entry.source is EntrySource.BUILTIN else NO_PROVENANCE)
            entry_offsets.append(len(frequencies))
        arrays = {
            "key_syllables": np.asarray(key_syllables, dtype="<u2"),
            "key_offsets": np.asarray(key_offsets, dtype="<u4"),
            "entry_offsets": np.asarray(entry_offsets, dtype="<u4"),
            "text_offsets": np.asarray(text_offsets, dtype="<u4"),
            "text_blob": np.frombuffer(bytes(text_blob), dtype="u1"),
            "frequencies": np.asarray(frequencies, dtype="<f8"),
            "sources": np.asarray(sources, dtype="u1"),
            "provenance": np.asarray(provenance_ids, dtype="<u4"),
        }
        header = {
            "format": "zaoseq-compact-lexicon/1",
            "syllables": syllables,
            "total_frequency": snapshot.total_frequency.hex(),
            "sources": [s.value for s in SOURCES],
            "arrays": {name: [str(a.dtype), int(a.size)] for name, a in arrays.items()},
        }
        encoded = json.dumps(header, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        with path.open("wb") as handle:
            handle.write(MAGIC)
            handle.write(struct.pack("<I", len(encoded)))
            handle.write(encoded)
            for name in sorted(arrays):
                handle.write(arrays[name].tobytes())


class CompactLexicon:
    """與 frozen Lexicon 相同介面與相同結果的精簡表示：文字、讀音與權重存在 numpy 陣列，
    `lookup` 才建立 LexiconEntry，並以有上限的 LRU 快取保存。"""

    def __init__(self, path: Path, cache_size: int = 8192) -> None:
        data = path.read_bytes()
        if data[:8] != MAGIC:
            raise ValueError(f"{path} 不是 compact lexicon")
        (size,) = struct.unpack("<I", data[8:12])
        header = json.loads(data[12 : 12 + size].decode("utf-8"))
        offset = 12 + size
        arrays: dict[str, np.ndarray] = {}
        for name, (dtype, count) in header["arrays"].items():
            dt = np.dtype(dtype)
            arrays[name] = np.frombuffer(data, dtype=dt, count=count, offset=offset)
            offset += dt.itemsize * count
        self._syllables = tuple(header["syllables"])
        self._total = float.fromhex(header["total_frequency"])
        self._sources = tuple(EntrySource(s) for s in header["sources"])
        self._key_syllables = arrays["key_syllables"]
        self._key_offsets = arrays["key_offsets"]
        self._entry_offsets = arrays["entry_offsets"]
        self._text_offsets = arrays["text_offsets"]
        self._text_blob = arrays["text_blob"].tobytes()
        self._frequencies = arrays["frequencies"]
        self._source_ids = arrays["sources"]
        self._provenance = arrays["provenance"]
        syllable_id = {s: i for i, s in enumerate(self._syllables)}
        self._syllable_id = syllable_id
        ks, ko = self._key_syllables, self._key_offsets
        self._index = {ks[ko[k] : ko[k + 1]].tobytes(): k for k in range(len(ko) - 1)}
        lengths = np.diff(ko)
        self._max_length = int(lengths.max()) if lengths.size else 0
        self._cache: OrderedDict[tuple[str, ...], tuple[LexiconEntry, ...]] = OrderedDict()
        self._cache_size = cache_size

    def __len__(self) -> int:
        return int(self._frequencies.size)

    @property
    def syllables(self) -> frozenset[str]:
        used = np.unique(self._key_syllables)
        return frozenset(self._syllables[i] for i in used)

    @property
    def max_word_length(self) -> int:
        return self._max_length

    def words(self) -> frozenset[str]:
        return frozenset(self._text(i) for i in range(len(self)))

    def _text(self, index: int) -> str:
        return self._text_blob[self._text_offsets[index] : self._text_offsets[index + 1]].decode("utf-8")

    def _key(self, readings: tuple[str, ...]) -> bytes | None:
        ids = []
        for syllable in readings:
            sid = self._syllable_id.get(syllable)
            if sid is None:
                return None
            ids.append(sid)
        return np.asarray(ids, dtype="<u2").tobytes()

    def lookup(self, readings: tuple[str, ...]) -> tuple[LexiconEntry, ...]:
        cached = self._cache.get(readings)
        if cached is not None:
            self._cache.move_to_end(readings)
            return cached
        key = self._key(readings)
        group = self._index.get(key) if key is not None else None
        if group is None:
            entries: tuple[LexiconEntry, ...] = ()
        else:
            start, end = int(self._entry_offsets[group]), int(self._entry_offsets[group + 1])
            entries = tuple(
                LexiconEntry(self._text(i), readings, float(self._frequencies[i]), self._sources[self._source_ids[i]]) for i in range(start, end)
            )
        self._cache[readings] = entries
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return entries

    def log10_probability(self, entry: LexiconEntry) -> float:
        return math.log10(entry.frequency / self._total)

    def provenance_ids(self, readings: tuple[str, ...]) -> tuple[int, ...]:
        key = self._key(readings)
        group = self._index.get(key) if key is not None else None
        if group is None:
            return ()
        return tuple(int(x) for x in self._provenance[self._entry_offsets[group] : self._entry_offsets[group + 1]])


class ProvenanceTable:
    """衍生詞 → 整數 id（從 1 開始，依文字排序）；id 0 表示 CNS / builtin。"""

    def __init__(self, entries: Sequence[object]) -> None:
        self.rows = sorted(entries, key=lambda e: e.text)  # type: ignore[attr-defined]
        self.ids = {e.text: i + 1 for i, e in enumerate(self.rows)}  # type: ignore[attr-defined]

    def write(self, path: Path) -> None:
        records = [{"id": self.ids[e.text], **e.to_json()} for e in self.rows]  # type: ignore[attr-defined]
        path.write_text(json.dumps(records, ensure_ascii=False, indent=0) + "\n", encoding="utf-8", newline="\n")

    @staticmethod
    def read(path: Path) -> dict[int, dict[str, object]]:
        return {row["id"]: row for row in json.loads(path.read_text(encoding="utf-8"))}
