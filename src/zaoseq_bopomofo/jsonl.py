from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path


def iter_jsonl(path: Path) -> Iterator[dict]:  # type: ignore[type-arg]
    """只以 \n 分行：文字中可能含 U+2028、U+0085 等字元，str.splitlines() 會把它們當成換行而切壞 JSON。"""
    with path.open(encoding="utf-8", newline="\n") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def read_jsonl(path: Path) -> list[dict]:  # type: ignore[type-arg]
    return list(iter_jsonl(path))
