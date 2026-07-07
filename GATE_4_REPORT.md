# Gate 4 Report — Karaoke Segmenter

## Status

PASS

## Summary

Gate 4 adds a deterministic karaoke line segmenter that flattens timed words from a validated `KaraokeDocument`, splits them into shorter readable `KaraokeLine` objects using configurable max-words, max-chars, max-duration, pause, and punctuation rules, and returns a newly validated document without mutating the input.

## Files Created

- `karaoke_engine/segmenter.py`
- `tests/test_segmenter.py`
- `GATE_4_REPORT.md`

## Files Modified

- `karaoke_engine/__init__.py`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* SegmentOptions dataclass
* Segment option validation
* segment_document()
* Max words splitting
* Max chars splitting
* Max duration splitting
* Pause splitting
* Punctuation-aware splitting
* Input validation
* Output validation
* Source format handling
* Public exports
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* High-level Engine API
* FFmpeg
* SRT parser
* VTT parser
* Web UI
* Frappe integration
* OpenAI API calls
* Local Whisper
* Local LLM

## Test Result

```
python -m pytest -q
...................................................................      [100%]
67 passed in 0.10s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/segmenter.py`

```python
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
```

* any modified root `karaoke_engine/__init__.py`

```python
"""Lightweight server-friendly karaoke subtitle engine."""

from karaoke_engine.errors import (
    AssGenerationError,
    KaraokeEngineError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)
from karaoke_engine.ass import AssWriter, KaraokeStyle, escape_ass_text
from karaoke_engine.models import (
    KaraokeDocument,
    KaraokeLine,
    ValidationReport,
    ValidationWarning,
    Word,
)
from karaoke_engine.parsers import load_whisper_json, parse_whisper_json
from karaoke_engine.segmenter import SegmentOptions, segment_document

__all__ = [
    "AssGenerationError",
    "AssWriter",
    "KaraokeDocument",
    "KaraokeEngineError",
    "KaraokeLine",
    "KaraokeStyle",
    "SegmentOptions",
    "TranscriptValidationError",
    "UnsupportedTranscriptFormatError",
    "ValidationReport",
    "ValidationWarning",
    "Word",
    "escape_ass_text",
    "load_whisper_json",
    "parse_whisper_json",
    "segment_document",
]

__version__ = "0.1.0"
```

## Example Input

```
KaraokeDocument(
  lines=(
    KaraokeLine(
      words=(
        Word(text='Aku', start=0.0, end=0.4),
        Word(text='sangat', start=0.4, end=0.8),
        Word(text='cinta', start=0.8, end=1.2),
        Word(text='padamu', start=1.2, end=1.6),
        Word(text='selamanya', start=1.6, end=2.0),
        Word(text='dan', start=2.0, end=2.2),
        Word(text='akan', start=2.2, end=2.5),
        Word(text='setia!', start=2.5, end=3.2),
      ),
      start=0.0,
      end=3.2,
    ),
  ),
  source_format='whisper_json',
)
```

## Example Segmented Output

With `SegmentOptions(max_words_per_line=3, max_chars_per_line=20, pause_break_seconds=100.0)`:

```
KaraokeDocument(
  lines=(
    KaraokeLine(
      words=(
        Word(text='Aku', start=0.0, end=0.4),
        Word(text='sangat', start=0.4, end=0.8),
        Word(text='cinta', start=0.8, end=1.2),
      ),
      start=0.0,
      end=1.2,
    ),
    KaraokeLine(
      words=(
        Word(text='padamu', start=1.2, end=1.6),
        Word(text='selamanya', start=1.6, end=2.0),
        Word(text='dan', start=2.0, end=2.2),
      ),
      start=1.2,
      end=2.2,
    ),
    KaraokeLine(
      words=(
        Word(text='akan', start=2.2, end=2.5),
        Word(text='setia!', start=2.5, end=3.2),
      ),
      start=2.2,
      end=3.2,
    ),
  ),
  source_format='whisper_json',
)
```

## Design Decisions

- **Single-pass greedy segmentation**: Words are processed in stable flattened order with fixed before/after break checks for deterministic output.
- **Before-add break priority**: Pause, max-words, max-chars, and max-duration are evaluated before appending the next word; punctuation breaks are evaluated after adding a word.
- **Oversized single words**: Words exceeding char or duration limits are kept on their own line rather than failing, since words cannot be split.
- **Char counting includes spaces**: Inter-word spaces count toward `max_chars_per_line` to match on-screen subtitle width.
- **Punctuation gating**: Punctuation breaks require `min_line_duration` and a remaining next word, avoiding forced breaks on the final word or very short clauses.
- **Immutable pipeline**: Input documents are never mutated; output is a new `KaraokeDocument` validated through existing Gate 1 rules.
- **Source format control**: `preserve_source_format=True` by default; `False` sets `source_format` to `"segmented"`.

## Risks / Questions

- **Rule interaction**: When multiple break conditions apply at the same boundary, the fixed evaluation order may not match all human editorial preferences.
- **Pause vs punctuation**: A pause before the next word takes precedence over keeping a punctuation-terminated clause together on one line.
- **No orphan avoidance**: The segmenter does not rebalance very short trailing lines (e.g. one-word remainder) beyond what the rules produce.
- **Flattening only**: Multi-line Gate 3 input is flattened before segmentation; original line boundaries are not preserved unless they happen to align with break rules.

## Gatekeeper Review Request

Please review Gate 4 and tell me whether it is APPROVED or BLOCKED.
