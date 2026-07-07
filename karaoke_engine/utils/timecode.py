"""ASS timecode conversion helpers."""

from __future__ import annotations


def seconds_to_centiseconds(seconds: float) -> int:
    """Convert seconds to whole centiseconds."""
    if seconds < 0:
        raise ValueError(f"Timestamp must not be negative: {seconds}")
    return int(round(seconds * 100))


def seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format ``H:MM:SS.cc``."""
    if seconds < 0:
        raise ValueError(f"Timestamp must not be negative: {seconds}")

    total_centiseconds = seconds_to_centiseconds(seconds)
    centiseconds = total_centiseconds % 100
    total_seconds = total_centiseconds // 100
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"
