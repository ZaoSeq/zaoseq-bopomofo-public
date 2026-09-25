from __future__ import annotations

import bz2
import gzip
import hashlib
import json
import tarfile
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from zaoseq_bopomofo.daily.sources import LicenseError, LicenseGate, Purpose, RawFiles, SourceRegistry


@dataclass(frozen=True)
class DailyDocument:
    """`text` 是來源原文（未正規化）；正規化與品質檢查在建置語料時進行。"""

    source_id: str
    doc_id: str
    text: str
    contributor: str = ""


class DailyImporter(ABC):
    """每個來源一個 importer；`documents()` 先依用途經過 LicenseGate 與 SHA-256 檢查才讀檔。"""

    source_id: str

    def __init__(
        self,
        registry: SourceRegistry,
        gate: LicenseGate | None = None,
        raw: RawFiles | None = None,
        purpose: Purpose = Purpose.DEV_EXPERIMENT,
    ) -> None:
        self._source = registry[self.source_id]
        self._gate = gate or LicenseGate()
        self._raw = raw or RawFiles()
        self._purpose = purpose

    def documents(self) -> Iterator[DailyDocument]:
        self._gate.require(self._source, self._purpose)
        yield from self._read(self._raw.verify(self._source))

    @abstractmethod
    def _read(self, files: dict[str, Path]) -> Iterator[DailyDocument]: ...


class TatoebaImporter(DailyImporter):
    """Tatoeba 為每個 cmn 句子提供另一字體的自動轉寫；轉寫為 Hans 表示原句是繁體。
    轉寫文字本身從不使用。"""

    source_id = "tatoeba_cmn_hant"

    def _read(self, files: dict[str, Path]) -> Iterator[DailyDocument]:
        hant_originals: set[str] = set()
        with bz2.open(files["cmn_transcriptions.tsv.bz2"], "rt", encoding="utf-8") as handle:
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3 and parts[2] == "Hans":
                    hant_originals.add(parts[0])
        with bz2.open(files["cmn_sentences_detailed.tsv.bz2"], "rt", encoding="utf-8") as handle:
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4 or parts[1] != "cmn" or parts[0] not in hant_originals:
                    continue
                user = "" if parts[3] == "\\N" else parts[3]
                yield DailyDocument(self.source_id, parts[0], parts[2], user)


class OasstPrompterImporter(DailyImporter):
    source_id = "oasst1_zh_prompter"

    def _read(self, files: dict[str, Path]) -> Iterator[DailyDocument]:
        with gzip.open(files["2023-04-12_oasst_ready.messages.jsonl.gz"], "rt", encoding="utf-8") as handle:
            for line in handle:
                message = json.loads(line)
                if (
                    message.get("lang") != "zh"
                    or message.get("role") != "prompter"
                    or message.get("deleted")
                    or message.get("synthetic")
                    or message.get("review_result") is not True
                ):
                    continue
                user = hashlib.sha1(str(message.get("user_id", "")).encode("utf-8")).hexdigest()[:12]
                yield DailyDocument(self.source_id, str(message["message_tree_id"]), message["text"], user)


class CommonVoiceSentenceTable(ABC):
    """Common Voice 某個 locale 的句子表。只取 sentence_id 與 sentence 兩欄；
    client_id、人口統計欄位與 clip path 在解析時就丟掉，音檔從不讀取。"""

    PRIMARY = "validated_sentences.tsv"
    FALLBACK = "validated.tsv"
    ID_COLUMN = "sentence_id"
    TEXT_COLUMN = "sentence"

    def __init__(self, origin: Path) -> None:
        self._origin = origin
        self.table = ""

    def rows(self) -> Iterator[tuple[str, str]]:
        for table in (self.PRIMARY, self.FALLBACK):
            lines = self._lines(table)
            if lines is not None:
                self.table = table
                yield from self._parse(lines)
                return
        raise LicenseError(f"{self._origin.name}: 沒有 {self._where()}{self.PRIMARY} 或 {self.FALLBACK}")

    @abstractmethod
    def _lines(self, table: str) -> list[str] | None: ...

    def _where(self) -> str:
        return ""

    def _parse(self, lines: Iterable[str]) -> Iterator[tuple[str, str]]:
        iterator = iter(lines)
        header = next(iterator, "").rstrip("\r\n").split("\t")
        if self.ID_COLUMN not in header or self.TEXT_COLUMN not in header:
            raise LicenseError(f"{self._origin.name}: 句子表缺少 {self.ID_COLUMN} / {self.TEXT_COLUMN} 欄")
        id_at, text_at = header.index(self.ID_COLUMN), header.index(self.TEXT_COLUMN)
        width = max(id_at, text_at)
        for line in iterator:
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) > width and parts[id_at] and parts[text_at]:
                yield parts[id_at], parts[text_at]


class ArchiveSentenceTable(CommonVoiceSentenceTable):
    """直接串流讀 MDC 官方 .tar.gz，不解壓到磁碟。"""

    def __init__(self, archive: Path, locale: str) -> None:
        super().__init__(archive)
        self._locale = locale

    def _where(self) -> str:
        return f"{self._locale}/"

    def _lines(self, table: str) -> list[str] | None:
        suffix = f"/{self._locale}/{table}"
        with tarfile.open(self._origin, "r|gz") as archive:
            for member in archive:
                if member.isfile() and ("/" + member.name).endswith(suffix):
                    handle = archive.extractfile(member)
                    return None if handle is None else [line.decode("utf-8") for line in handle]
        return None


class ExtractedSentenceTable(CommonVoiceSentenceTable):
    """讀已解壓的 locale 目錄；只接受 manifest 記錄且 SHA-256 已驗證的句子表。"""

    def __init__(self, files: dict[str, Path]) -> None:
        super().__init__(next(iter(files.values())).parent)
        self._files = files

    def _lines(self, table: str) -> list[str] | None:
        path = self._files.get(table)
        return None if path is None else path.read_text(encoding="utf-8").splitlines()


class CommonVoiceImporter(DailyImporter):
    """Common Voice 27.0 zh-TW（MDC 官方版本）。manifest 有官方 archive 時直接讀 archive，否則讀已驗證的解壓句子表。
    一個 sentence id 一筆，再依 NFC 全文去重；同一句的多段錄音只算一次。不記錄任何貢獻者資訊。"""

    source_id = "mdc_common_voice_zh_tw_27_0"
    locale = "zh-TW"
    table = ""
    duplicate_ids = 0
    duplicate_texts = 0

    def _read(self, files: dict[str, Path]) -> Iterator[DailyDocument]:
        archives = [path for name, path in files.items() if name.endswith(".tar.gz")]
        table = ArchiveSentenceTable(archives[0], self.locale) if archives else ExtractedSentenceTable(files)
        self.duplicate_ids = self.duplicate_texts = 0
        ids: set[str] = set()
        texts: set[str] = set()
        for sentence_id, text in table.rows():
            if sentence_id in ids:
                self.duplicate_ids += 1
                continue
            ids.add(sentence_id)
            normalized = unicodedata.normalize("NFC", text)
            if normalized in texts:
                self.duplicate_texts += 1
                continue
            texts.add(normalized)
            yield DailyDocument(self.source_id, sentence_id, text)
        self.table = table.table


IMPORTERS: tuple[type[DailyImporter], ...] = (TatoebaImporter, CommonVoiceImporter, OasstPrompterImporter)
