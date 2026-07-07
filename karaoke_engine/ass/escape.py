"""ASS text escaping helpers."""

from __future__ import annotations


def escape_ass_text(text: str) -> str:
    """Escape text for safe inclusion in ASS dialogue fields."""
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r\n", "\\N")
        .replace("\n", "\\N")
        .replace("\r", "\\N")
    )
