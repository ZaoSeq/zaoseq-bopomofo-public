"""語料正規化：只做格式清理，不改寫字形，也不做簡轉繁。"""

from __future__ import annotations

import html
import re
import unicodedata

_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_SPACES = re.compile(r"[ \t　\xa0]+")
_BLOCK_TAGS = re.compile(r"</?(p|br|div|li|tr|h[1-6])\b[^>]*>", re.IGNORECASE)

# 中文標點統一為全形；半形英數字保持半形。只處理這張明確表，不使用 NFKC，
# 因為 NFKC 會把 CJK 相容字等字形一併改掉，改變來源原文。
_TO_FULLWIDTH_PUNCT = {
    ",": "，",
    "?": "？",
    "!": "！",
    ":": "：",
    ";": "；",
    "(": "（",
    ")": "）",
}
_HALFWIDTH_ASCII = {chr(c): chr(c - 0xFEE0) for c in range(0xFF10, 0xFF1A)}
_HALFWIDTH_ASCII.update({chr(c): chr(c - 0xFEE0) for c in range(0xFF21, 0xFF3B)})
_HALFWIDTH_ASCII.update({chr(c): chr(c - 0xFEE0) for c in range(0xFF41, 0xFF5B)})


def is_han(ch: str) -> bool:
    code = ord(ch)
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0x20000 <= code <= 0x3134F
        or 0xF900 <= code <= 0xFAFF
    )


def strip_markup(text: str) -> str:
    """HTML / XML 標記：區塊標籤轉成換行，其他標籤移除，再解開 entity（例如 &nbsp;）。"""
    text = _BLOCK_TAGS.sub("\n", text)
    text = _TAG.sub("", text)
    return html.unescape(text)


def normalize_text(text: str) -> str:
    """Unicode NFC、換行、markup、網址與 email、標點寬度。回傳可能含換行的文字，由斷句處理。"""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_markup(text)
    text = _URL.sub(" ", text)
    text = _EMAIL.sub(" ", text)
    text = "".join(_HALFWIDTH_ASCII.get(ch, ch) for ch in text)
    text = _fullwidth_punct_between_han(text)
    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _fullwidth_punct_between_han(text: str) -> str:
    # 只把「前一個字是漢字」的半形標點轉成全形，避免改到 "3:00"、"(A)" 這類英數內容。
    out: list[str] = []
    for i, ch in enumerate(text):
        replacement = _TO_FULLWIDTH_PUNCT.get(ch)
        if replacement is not None and i > 0 and is_han(text[i - 1]):
            out.append(replacement)
        else:
            out.append(ch)
    return "".join(out)


def han_ratio(text: str) -> float:
    visible = [ch for ch in text if not ch.isspace()]
    if not visible:
        return 0.0
    return sum(is_han(ch) for ch in visible) / len(visible)
