from __future__ import annotations

import re
import unicodedata

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def visual_width(text: str) -> int:
    # Normalize to NFC so decomposed sequences (e.g. NFD Hangul) are measured accurately.
    clean_text = unicodedata.normalize("NFC", strip_ansi(text))
    width = 0
    for char in clean_text:
        if unicodedata.east_asian_width(char) in ("W", "F", "A"):
            width += 2
        else:
            width += 1
    return width


def split_cjk_and_words(text: str) -> list[str]:
    sub_chunks = []
    current_word = []
    for char in unicodedata.normalize("NFC", text):
        if unicodedata.east_asian_width(char) in ("W", "F", "A"):
            if current_word:
                sub_chunks.append("".join(current_word))
                current_word = []
            sub_chunks.append(char)
        else:
            current_word.append(char)
    if current_word:
        sub_chunks.append("".join(current_word))
    return sub_chunks


def _hard_split(text: str, width: int) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    current_width = 0

    for chunk in split_cjk_and_words(text):
        units = chunk if visual_width(chunk) > width else (chunk,)
        for unit in units:
            unit_width = visual_width(unit)
            if current and current_width + unit_width > width:
                parts.append("".join(current))
                current = []
                current_width = 0
            if unit_width > width:
                if current:
                    parts.append("".join(current))
                    current = []
                    current_width = 0
                parts.append(unit)
            else:
                current.append(unit)
                current_width += unit_width

    if current:
        parts.append("".join(current))
    return parts


def visual_wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        raise ValueError("width must be positive")

    chunks = re.split(r"(\s+)", text)
    chunks = [c for c in chunks if c]

    lines: list[str] = []
    current_line: list[str] = []
    current_width = 0

    for chunk in chunks:
        chunk_width = visual_width(chunk)

        if current_width + chunk_width <= width:
            current_line.append(chunk)
            current_width += chunk_width
        else:
            if chunk.isspace():
                if current_line:
                    lines.append("".join(current_line))
                    current_line = [chunk]
                    current_width = chunk_width
                else:
                    current_line.append(chunk)
                    current_width += chunk_width
            else:
                if current_line:
                    lines.append("".join(current_line))
                    current_line = []
                    current_width = 0

                for sub_chunk in _hard_split(chunk, width):
                    sub_width = visual_width(sub_chunk)
                    if current_width + sub_width <= width:
                        current_line.append(sub_chunk)
                        current_width += sub_width
                    else:
                        if current_line:
                            lines.append("".join(current_line))
                        current_line = [sub_chunk]
                        current_width = sub_width

    if current_line:
        lines.append("".join(current_line))

    return lines
