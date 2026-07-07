# Gate 3 Report — Whisper JSON Parser

## Status

PASS

## Summary

Gate 3 adds a production-grade parser for OpenAI Whisper `verbose_json` transcripts with word-level timestamps. The parser supports root-level `words` and segment-level `segments[].words`, prefers segment words when present, normalizes entries into `KaraokeDocument` / `KaraokeLine` / `Word` models, and validates the final document before returning.

## Files Created

- `karaoke_engine/parsers/__init__.py`
- `karaoke_engine/parsers/whisper_json.py`
- `tests/test_whisper_json.py`
- `GATE_3_REPORT.md`

## Files Modified

- `karaoke_engine/__init__.py`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* Whisper JSON parser
* Root-level words support
* Segment-level words support
* Segment-level preference
* Path loader
* Final document validation
* Public parser exports
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* Real segmenter
* FFmpeg
* SRT parser
* VTT parser
* Web UI
* Frappe integration
* OpenAI API calls
* Local Whisper

## Test Result

```
python -m pytest -q
..............................................                           [100%]
46 passed in 0.13s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/parsers/whisper_json.py`

```python
"""OpenAI Whisper verbose_json transcript parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.validators import ensure_valid_document

_SOURCE_FORMAT = "whisper_json"


def parse_whisper_json(data: dict[str, Any]) -> KaraokeDocument:
    """Parse Whisper verbose_json data into a validated ``KaraokeDocument``."""
    if not isinstance(data, dict):
        raise UnsupportedTranscriptFormatError("Whisper JSON root must be an object")

    if _has_segment_words(data):
        document = _parse_segment_words(data)
    elif _has_root_words(data):
        document = _parse_root_words(data)
    else:
        raise UnsupportedTranscriptFormatError(
            "Unsupported Whisper JSON shape: expected root-level 'words' or "
            "segment-level 'segments[].words' with word timestamps"
        )

    if not document.lines:
        raise TranscriptValidationError("Whisper transcript is empty")

    ensure_valid_document(document)
    return document


def load_whisper_json(path: str | Path) -> KaraokeDocument:
    """Load and parse a Whisper verbose_json file from disk."""
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Cannot read Whisper JSON file {file_path}: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Malformed JSON file {file_path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON root must be an object in {file_path}"
        )

    return parse_whisper_json(data)


def _has_segment_words(data: dict[str, Any]) -> bool:
    segments = data.get("segments")
    if not isinstance(segments, list):
        return False
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        words = segment.get("words")
        if isinstance(words, list) and words:
            return True
    return False


def _has_root_words(data: dict[str, Any]) -> bool:
    words = data.get("words")
    return isinstance(words, list) and bool(words)


def _parse_root_words(data: dict[str, Any]) -> KaraokeDocument:
    words_data = data.get("words")
    if not isinstance(words_data, list) or not words_data:
        raise UnsupportedTranscriptFormatError(
            "Whisper JSON is missing root-level 'words' with timestamps"
        )

    words = tuple(
        _parse_word_entry(entry, path=f"words[{index}]")
        for index, entry in enumerate(words_data)
    )
    line = _build_line(words)
    return KaraokeDocument(lines=(line,), source_format=_SOURCE_FORMAT)


def _parse_segment_words(data: dict[str, Any]) -> KaraokeDocument:
    segments = data.get("segments")
    if not isinstance(segments, list):
        raise UnsupportedTranscriptFormatError(
            "Whisper JSON 'segments' must be a list when segment words are used"
        )

    lines: list[KaraokeLine] = []
    for segment_index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise UnsupportedTranscriptFormatError(
                f"Whisper JSON segments[{segment_index}] must be an object"
            )

        words_data = segment.get("words")
        if not isinstance(words_data, list) or not words_data:
            continue

        words = tuple(
            _parse_word_entry(
                entry,
                path=f"segments[{segment_index}].words[{word_index}]",
            )
            for word_index, entry in enumerate(words_data)
        )
        lines.append(_build_line(words))

    return KaraokeDocument(lines=tuple(lines), source_format=_SOURCE_FORMAT)


def _parse_word_entry(entry: Any, *, path: str) -> Word:
    if not isinstance(entry, dict):
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} must be an object"
        )

    text = _extract_word_text(entry, path=path)
    start = _extract_timestamp(entry, field="start", path=path)
    end = _extract_timestamp(entry, field="end", path=path)

    return Word(text=text, start=start, end=end)


def _extract_word_text(entry: dict[str, Any], *, path: str) -> str:
    if "word" in entry:
        raw_text = entry["word"]
    elif "text" in entry:
        raw_text = entry["text"]
    else:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} is missing 'word' or 'text'"
        )

    if raw_text is None:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has empty text"
        )

    text = str(raw_text).strip()
    if not text:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has empty text after stripping"
        )

    return text


def _extract_timestamp(entry: dict[str, Any], *, field: str, path: str) -> float:
    if field not in entry:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} is missing '{field}' timestamp"
        )

    value = entry[field]
    if value is None:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has null '{field}' timestamp"
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has invalid '{field}' timestamp: {value!r}"
        ) from exc


def _build_line(words: tuple[Word, ...]) -> KaraokeLine:
    return KaraokeLine(
        words=words,
        start=words[0].start,
        end=words[-1].end,
    )
```

* `karaoke_engine/parsers/__init__.py`

```python
"""Transcript parsers."""

from karaoke_engine.parsers.whisper_json import load_whisper_json, parse_whisper_json

__all__ = ["load_whisper_json", "parse_whisper_json"]
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

__all__ = [
    "AssGenerationError",
    "AssWriter",
    "KaraokeDocument",
    "KaraokeEngineError",
    "KaraokeLine",
    "KaraokeStyle",
    "TranscriptValidationError",
    "UnsupportedTranscriptFormatError",
    "ValidationReport",
    "ValidationWarning",
    "Word",
    "escape_ass_text",
    "load_whisper_json",
    "parse_whisper_json",
]

__version__ = "0.1.0"
```

## Example Parsed Input

```json
{
  "text": "Aku cinta padamu",
  "words": [
    {"word": "Aku", "start": 0.0, "end": 0.4},
    {"word": "cinta", "start": 0.4, "end": 0.75},
    {"word": "padamu", "start": 0.75, "end": 1.55}
  ]
}
```

## Example Parsed Output

```
KaraokeDocument(
  lines=(
    KaraokeLine(
      words=(
        Word(text='Aku', start=0.0, end=0.4),
        Word(text='cinta', start=0.4, end=0.75),
        Word(text='padamu', start=0.75, end=1.55),
      ),
      start=0.0,
      end=1.55,
    ),
  ),
  source_format='whisper_json',
)
```

## Design Decisions

- **Segment-first routing**: If any segment contains a non-empty `words` list, segment mode is used and root-level `words` are ignored, matching Whisper `verbose_json` structure.
- **Gate 3 line rules only**: One `KaraokeLine` per segment in segment mode; one line containing all words in root mode. No pause, punctuation, duration, or max-word splitting.
- **Text key fallback**: Word text accepts `word` (preferred) or `text`, with leading/trailing whitespace stripped while punctuation is preserved.
- **Error layering**: `UnsupportedTranscriptFormatError` for structural/parse issues (missing fields, malformed JSON, unsupported shape); `TranscriptValidationError` for semantic validation failures via `ensure_valid_document()`.
- **Path-based loading**: `load_whisper_json()` reads UTF-8 files and delegates to `parse_whisper_json()` for a single validation path.
- **Empty segment handling**: Segments with missing or empty `words` are skipped rather than producing empty lines.

## Risks / Questions

- **Whisper variant differences**: Some Whisper outputs may attach words only at segment level or only at root; both are supported, but transcripts with neither are rejected.
- **Segment text ignored**: Segment-level `text` fields are not used for line content; only `words` drive output.
- **No cross-segment merging**: Long pauses within a single Whisper segment remain on one `KaraokeLine` until Gate 4 segmentation.
- **Strict empty check**: Whitespace-only word tokens are rejected at parse time, which matches validation rules but may drop some noisy Whisper tokens.

## Gatekeeper Review Request

Please review Gate 3 and tell me whether it is APPROVED or BLOCKED.
