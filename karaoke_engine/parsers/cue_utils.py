"""Shared helpers for cue-based subtitle parsers."""

from __future__ import annotations

import re

from karaoke_engine.models import KaraokeLine, Word

_TAG_PATTERN = re.compile(r"<[^>]+>")


def strip_markup(text: str) -> str:
    """Remove simple HTML/VTT-like tags from cue text."""
    return _TAG_PATTERN.sub("", text).strip()


def split_cue_words(text: str) -> list[str]:
    """Split cue text into words after markup removal."""
    cleaned = strip_markup(text)
    if not cleaned:
        return []
    return cleaned.split()


def build_approximate_words(text: str, start: float, end: float) -> tuple[Word, ...]:
    """Distribute cue duration evenly across words."""
    word_texts = split_cue_words(text)
    if not word_texts:
        return ()

    word_count = len(word_texts)
    duration_per_word = (end - start) / word_count
    words: list[Word] = []
    for index, word_text in enumerate(word_texts):
        word_start = start + index * duration_per_word
        word_end = end if index == word_count - 1 else start + (index + 1) * duration_per_word
        words.append(Word(text=word_text, start=word_start, end=word_end))
    return tuple(words)


def build_karaoke_line(text: str, start: float, end: float) -> KaraokeLine | None:
    """Build a karaoke line from cue text and approximate word timings."""
    words = build_approximate_words(text, start, end)
    if not words:
        return None
    return KaraokeLine(words=words, start=start, end=end)
