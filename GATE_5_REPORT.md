# Gate 5 Report — High-Level Engine API

## Status

PASS

## Summary

Gate 5 adds the high-level `KaraokeEngine` API that orchestrates Whisper JSON loading, optional segmentation, and ASS file generation in a single `create_ass()` call. It returns structured `CreateAssResult` metadata, creates parent output directories automatically, and exports the engine from the package root. The README was updated to reflect the current project capabilities and limitations.

## Files Created

- `karaoke_engine/engine.py`
- `tests/test_engine.py`
- `GATE_5_REPORT.md`

## Files Modified

- `karaoke_engine/__init__.py`
- `README.md`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* CreateAssResult dataclass
* KaraokeEngine class
* create_ass()
* Whisper JSON loading by extension
* Optional segmentation
* ASS writer integration
* Output parent directory creation
* Result metadata
* Public exports
* README update
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* FFmpeg
* Video rendering
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
........................................................................ [ 86%]
...........                                                              [100%]
83 passed in 0.31s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/engine.py`

```python
"""High-level karaoke engine API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.ass.writer import AssWriter
from karaoke_engine.errors import AssGenerationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument
from karaoke_engine.parsers.whisper_json import load_whisper_json
from karaoke_engine.segmenter import SegmentOptions, segment_document

_SUPPORTED_TRANSCRIPT_SUFFIXES = {".json"}


@dataclass(frozen=True, slots=True)
class CreateAssResult:
    """Metadata returned after creating a karaoke ASS file."""

    ass_path: Path
    line_count: int
    word_count: int
    source_format: str
    segmented: bool


class KaraokeEngine:
    """Orchestrates Whisper JSON parsing, segmentation, and ASS generation."""

    def create_ass(
        self,
        *,
        transcript_path: str | Path,
        output_path: str | Path,
        style: KaraokeStyle | None = None,
        segment_options: SegmentOptions | None = None,
        segment: bool = True,
        play_res_x: int = 1920,
        play_res_y: int = 1080,
        title: str = "Karaoke",
    ) -> CreateAssResult:
        """Load Whisper JSON, optionally segment, and write a karaoke ASS file."""
        parsed = _load_transcript(Path(transcript_path))
        final_document = (
            segment_document(parsed, segment_options)
            if segment
            else parsed
        )

        ass_path = Path(output_path)
        _ensure_output_parent(ass_path)

        writer = AssWriter(
            style=style,
            play_res_x=play_res_x,
            play_res_y=play_res_y,
            title=title,
        )
        try:
            writer.write_to_file(final_document, ass_path)
        except OSError as exc:
            raise AssGenerationError(
                f"Failed to write ASS file to {ass_path}: {exc}"
            ) from exc

        return CreateAssResult(
            ass_path=ass_path,
            line_count=len(final_document.lines),
            word_count=_count_words(final_document),
            source_format=final_document.source_format,
            segmented=segment,
        )


def _load_transcript(path: Path) -> KaraokeDocument:
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_TRANSCRIPT_SUFFIXES:
        raise UnsupportedTranscriptFormatError(
            f"Unsupported transcript format {path.suffix!r}: only .json is supported"
        )
    return load_whisper_json(path)


def _count_words(document: KaraokeDocument) -> int:
    return sum(len(line.words) for line in document.lines)


def _ensure_output_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
from karaoke_engine.engine import CreateAssResult, KaraokeEngine
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
    "CreateAssResult",
    "KaraokeDocument",
    "KaraokeEngine",
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

* updated `README.md`

```markdown
# karaoke_engine

Lightweight, server-friendly karaoke subtitle engine for Python 3.10+.

## What it does

`karaoke_engine` converts **OpenAI Whisper `verbose_json` transcripts** (with word-level timestamps) into **karaoke `.ass` subtitle files**:

1. Parse Whisper JSON
2. Optionally segment long lines into readable karaoke lines
3. Write ASS with `\kf` karaoke timing

## What it does not do

- It does **not** transcribe audio.
- It does **not** call OpenAI or any external API.
- It does **not** require PyTorch, CUDA, or local Whisper.
- **FFmpeg** and **video rendering** are not implemented yet.
- **SRT** and **VTT** parsers are not implemented yet.

## Supported input

Current supported input is **Whisper JSON with word timestamps** (root-level `words` or `segments[].words`).

## Install and development

```bash
pip install -e ".[dev]"
python -m pytest -q
```

## Basic usage

```python
from karaoke_engine import KaraokeEngine, KaraokeStyle, SegmentOptions

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="transcript.json",
    output_path="karaoke.ass",
    style=KaraokeStyle.default_1080p(),
    segment_options=SegmentOptions(max_words_per_line=5),
)
print(result.ass_path)
```

## Lower-level APIs

You can also use the components directly:

- `parse_whisper_json()` / `load_whisper_json()`
- `segment_document()`
- `AssWriter`
```

## Example Input

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

## Example Usage

```python
from karaoke_engine import KaraokeEngine, KaraokeStyle, SegmentOptions

engine = KaraokeEngine()
result = engine.create_ass(
    transcript_path="transcript.json",
    output_path="karaoke.ass",
    style=KaraokeStyle.default_1080p(),
    segment_options=SegmentOptions(max_words_per_line=5),
)
print(result.ass_path)
```

## Example Result

```
CreateAssResult(
  ass_path=Path('karaoke.ass'),
  line_count=1,
  word_count=3,
  source_format='whisper_json',
  segmented=True,
)
```

## Example ASS Snippet

```
[Script Info]
Title: Karaoke
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0.0,1,3,1,2,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.55,Karaoke,,0,0,0,,{\kf40}Aku {\kf35}cinta {\kf80}padamu
```

## Design Decisions

- **Thin orchestration layer**: `KaraokeEngine` delegates to existing parser, segmenter, and writer modules without duplicating validation or ASS logic.
- **Extension-based format routing**: Gate 5 accepts only `.json` transcripts via `_load_transcript()`, leaving room for future format handlers without changing the public API.
- **Optional segmentation default**: `segment=True` by default; `segment=False` writes the parsed document unchanged for debugging or pre-segmented input.
- **Immutable pipeline**: Parsed and segmented documents are separate objects; the engine never mutates intermediate results.
- **Output directory creation**: `_ensure_output_parent()` creates nested parent folders before writing ASS output.
- **Structured result**: `CreateAssResult` exposes path, counts, source format, and whether segmentation ran for logging and downstream automation.

## Risks / Questions

- **Single input format**: Only Whisper JSON is supported at the engine level; other formats require manual parsing before ASS writing.
- **No output path normalization**: `ass_path` in the result reflects the caller-supplied path, which may be relative or absolute depending on input.
- **Segment options passthrough**: `None` segment options use `SegmentOptions()` defaults inside `segment_document()`; callers cannot distinguish default vs explicit options in the result.
- **Write error handling**: `AssWriter.write_to_file()` already maps most I/O errors to `AssGenerationError`; the engine adds a secondary `OSError` guard for robustness.

## Gatekeeper Review Request

Please review Gate 5 and tell me whether it is APPROVED or BLOCKED.
