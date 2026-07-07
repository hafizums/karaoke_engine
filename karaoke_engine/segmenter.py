"""Karaoke line segmentation for readable subtitle display."""

from __future__ import annotations

from dataclasses import dataclass

from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.validators import ensure_valid_document


@dataclass(frozen=True, slots=True)
class SegmentOptions:
    """Configurable rules for splitting words into karaoke lines."""

    max_words_per_line: int = 6
    max_chars_per_line: int = 38
    max_line_duration: float = 5.0
    min_line_duration: float = 0.8
    pause_break_seconds: float = 0.65
    punctuation_break_chars: str = ".!?。！？"
    preserve_source_format: bool = True

    def __post_init__(self) -> None:
        if self.max_words_per_line < 1:
            raise ValueError("max_words_per_line must be >= 1")
        if self.max_chars_per_line < 1:
            raise ValueError("max_chars_per_line must be >= 1")
        if self.max_line_duration <= 0:
            raise ValueError("max_line_duration must be > 0")
        if self.min_line_duration < 0:
            raise ValueError("min_line_duration must be >= 0")
        if self.max_line_duration < self.min_line_duration:
            raise ValueError("max_line_duration must be >= min_line_duration")
        if self.pause_break_seconds < 0:
            raise ValueError("pause_break_seconds must be >= 0")


def segment_document(
    document: KaraokeDocument,
    options: SegmentOptions | None = None,
) -> KaraokeDocument:
    """Segment a validated document into shorter readable karaoke lines."""
    segment_options = options or SegmentOptions()
    ensure_valid_document(document)

    words = _flatten_words(document)
    if not words:
        raise TranscriptValidationError("Document has no words to segment")

    segmented_lines = _segment_words(words, segment_options)
    source_format = (
        document.source_format
        if segment_options.preserve_source_format
        else "segmented"
    )
    segmented = KaraokeDocument(
        lines=tuple(segmented_lines),
        source_format=source_format,
    )
    ensure_valid_document(segmented)
    return segmented


def _flatten_words(document: KaraokeDocument) -> tuple[Word, ...]:
    words: list[Word] = []
    for line in document.lines:
        words.extend(line.words)
    return tuple(words)


def _segment_words(
    words: tuple[Word, ...],
    options: SegmentOptions,
) -> list[KaraokeLine]:
    lines: list[KaraokeLine] = []
    current: list[Word] = []

    for index, word in enumerate(words):
        if current and _should_break_before(word, current, options):
            lines.append(_build_line(current))
            current = []

        current.append(word)

        has_more_words = index < len(words) - 1
        if current and _should_break_after_punctuation(
            current,
            options,
            has_more_words=has_more_words,
        ):
            lines.append(_build_line(current))
            current = []

    if current:
        lines.append(_build_line(current))

    return lines


def _should_break_before(
    word: Word,
    current: list[Word],
    options: SegmentOptions,
) -> bool:
    previous = current[-1]
    pause_gap = word.start - previous.end
    if pause_gap >= options.pause_break_seconds:
        return True
    if len(current) + 1 > options.max_words_per_line:
        return True
    if _char_count_with_word(current, word) > options.max_chars_per_line:
        return True
    if _duration_with_word(current, word) > options.max_line_duration:
        return True
    return False


def _should_break_after_punctuation(
    current: list[Word],
    options: SegmentOptions,
    *,
    has_more_words: bool,
) -> bool:
    if not has_more_words:
        return False

    last_word = current[-1]
    if not last_word.text:
        return False
    if last_word.text[-1] not in options.punctuation_break_chars:
        return False

    line_duration = last_word.end - current[0].start
    return line_duration >= options.min_line_duration


def _char_count_with_word(current: list[Word], word: Word) -> int:
    return _line_char_count([*current, word])


def _line_char_count(words: list[Word]) -> int:
    if not words:
        return 0
    return sum(len(item.text) for item in words) + len(words) - 1


def _duration_with_word(current: list[Word], word: Word) -> float:
    return word.end - current[0].start


def _build_line(words: list[Word]) -> KaraokeLine:
    return KaraokeLine(
        words=tuple(words),
        start=words[0].start,
        end=words[-1].end,
    )
