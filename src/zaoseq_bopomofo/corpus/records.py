"""把 CSV / JSON / XML 開放資料讀成欄位 → 文字的紀錄。只做結構解析，不判斷授權或語意。"""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

Record = dict[str, str]

_ENCODINGS = ("utf-8-sig", "cp950", "big5hkscs")
_LF = chr(10)
_TAB = chr(9)


def decode(raw: bytes, preferred: str | None = None) -> str:
    """依序嘗試指定編碼、UTF-8、Big5；全部失敗時丟出錯誤，不用 replace 默默產生亂碼。"""
    tried = [preferred] if preferred else []
    for encoding in [*tried, *_ENCODINGS]:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise UnicodeDecodeError("unknown", raw[:20], 0, 1, f"無法以 {tried + list(_ENCODINGS)} 解碼")


def read_records(path: Path, fmt: str, encoding: str | None = None) -> Iterator[Record]:
    text = decode(path.read_bytes(), encoding)
    fmt = fmt.upper()
    if fmt == "CSV":
        # 有些資料集標示為 CSV 但實際以 tab 分隔；只看標題列判斷，避免把內文中的逗號當分隔。
        header = text.split(_LF, 1)[0]
        delimiter = _TAB if _TAB in header and "," not in header else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        yield from ({k.strip(): (v or "") for k, v in row.items() if k} for row in reader)
    elif fmt == "JSON":
        yield from _json_records(json.loads(text))
    elif fmt == "XML":
        yield from _xml_records(ET.fromstring(text.encode("utf-8")))
    else:
        raise ValueError(f"不支援的格式：{fmt}")


def _json_records(data: object) -> Iterator[Record]:
    """找出第一個「物件陣列」當作紀錄；巢狀值轉成字串，只保留純量欄位。"""
    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
        for item in data:
            yield {str(k).strip(): _scalar(v) for k, v in item.items() if _scalar(v) is not None}  # type: ignore[misc]
        return
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, (list, dict)):
                found = list(_json_records(value))
                if found:
                    yield from found
                    return


def _scalar(value: object) -> str | None:
    if isinstance(value, (str, int, float)):
        return str(value)
    return None


def _xml_records(root: ET.Element) -> Iterator[Record]:
    """紀錄 = 子元素全部是葉節點的元素；取出現次數最多的那一種 tag。"""
    counts: dict[str, int] = {}
    for element in root.iter():
        children = list(element)
        if children and all(len(list(c)) == 0 for c in children):
            counts[element.tag] = counts.get(element.tag, 0) + 1
    if not counts:
        return
    tag = max(sorted(counts), key=lambda t: counts[t])
    for element in root.iter(tag):
        yield {_local(child.tag): (child.text or "") for child in element}


def _local(tag: str) -> str:
    """去掉 XML namespace（`{https://...}問題` → `問題`）。"""
    return tag.rsplit("}", 1)[-1].strip()
