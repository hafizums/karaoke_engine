# Gate 7 Report — SRT/VTT Fallback Parsers

## Status

PASS

## Summary

Gate 7 adds lightweight SRT and WebVTT fallback parsers that convert line-level subtitle cues into normalized `KaraokeDocument` objects with **approximate** per-word timing. Each cue's duration is evenly distributed across its words. The engine routes `.json`, `.srt`, and `.vtt` transcripts automatically, preserves `source_format` metadata (`whisper_json`, `srt_approx`, `vtt_approx`), and leaves existing Whisper JSON behavior unchanged.

## Files Created

- `karaoke_engine/parsers/cue_utils.py`
- `karaoke_engine/parsers/srt.py`
- `karaoke_engine/parsers/vtt.py`
- `tests/test_srt.py`
- `tests/test_vtt.py`
- `tests/test_engine_srt_vtt.py`
- `GATE_7_REPORT.md`

## Files Modified

- `karaoke_engine/parsers/__init__.py`
- `karaoke_engine/engine.py`
- `karaoke_engine/__init__.py`
- `README.md`
- `tests/test_engine.py`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* SRT parser
* VTT parser
* Approximate word timing
* SRT loader
* VTT loader
* Engine extension routing
* Source format metadata
* Public parser exports
* README update
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* True word-level timing from SRT/VTT
* OpenAI API calls
* Local Whisper
* Local LLM
* Web UI
* Frappe integration
* Browser rendering
* Bundled FFmpeg

## Test Result

```
python -m pytest -q
........................................................................ [ 50%]
......................................................................   [100%]
142 passed in 0.31s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/parsers/srt.py`

```python
"""SRT subtitle parser with approximate word timing."""

from __future__ import annotations

import re
from pathlib import Path

from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine
from karaoke_engine.parsers.cue_utils import build_karaoke_line
from karaoke_engine.validators import ensure_valid_document

_SOURCE_FORMAT = "srt_approx"
_TIMING_LINE_PATTERN = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
)


def parse_srt_text(text: str) -> KaraokeDocument:
    """Parse SRT subtitle text into a validated ``KaraokeDocument``."""
    blocks = _split_srt_blocks(text)
    lines: list[KaraokeLine] = []

    for block_index, block in enumerate(blocks):
        line = _parse_srt_block(block, block_index=block_index)
        if line is not None:
            lines.append(line)

    if not lines:
        raise TranscriptValidationError("SRT transcript is empty")

    document = KaraokeDocument(lines=tuple(lines), source_format=_SOURCE_FORMAT)
    ensure_valid_document(document)
    return document


def load_srt(path: str | Path) -> KaraokeDocument:
    """Load and parse an SRT subtitle file from disk."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Cannot read SRT file {file_path}: {exc}"
        ) from exc
    return parse_srt_text(text)


def _split_srt_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    return [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]


def _parse_srt_block(block: str, *, block_index: int) -> KaraokeLine | None:
    block_lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not block_lines:
        return None

    line_index = 0
    if block_lines[0].isdigit():
        line_index = 1

    if line_index >= len(block_lines):
        raise UnsupportedTranscriptFormatError(
            f"SRT block {block_index} is missing a timing line"
        )

    timing_line = block_lines[line_index]
    text_lines = block_lines[line_index + 1 :]
    if not text_lines:
        return None

    start, end = _parse_srt_timing_line(timing_line, block_index=block_index)
    cue_text = " ".join(text_lines)
    return build_karaoke_line(cue_text, start, end)


def _parse_srt_timing_line(timing_line: str, *, block_index: int) -> tuple[float, float]:
    match = _TIMING_LINE_PATTERN.match(timing_line.strip())
    if not match:
        raise UnsupportedTranscriptFormatError(
            f"Malformed SRT timing line in block {block_index}: {timing_line!r}"
        )

    start = _srt_timestamp_to_seconds(match.group(1, 2, 3, 4))
    end = _srt_timestamp_to_seconds(match.group(5, 6, 7, 8))
    if end <= start:
        raise UnsupportedTranscriptFormatError(
            f"SRT cue end time must be greater than start time in block {block_index}"
        )
    return start, end


def _srt_timestamp_to_seconds(parts: tuple[str, str, str, str]) -> float:
    hours, minutes, seconds, milliseconds = (int(part) for part in parts)
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
```

* `karaoke_engine/parsers/vtt.py`

```python
"""WebVTT subtitle parser with approximate word timing."""

from __future__ import annotations

import re
from pathlib import Path

from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine
from karaoke_engine.parsers.cue_utils import build_karaoke_line
from karaoke_engine.validators import ensure_valid_document

_SOURCE_FORMAT = "vtt_approx"
_TIMING_LINE_PATTERN = re.compile(
    r"^(.+?)\s*-->\s*(.+?)(?:\s+.*)?$"
)
_FULL_TIMESTAMP_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")
_SHORT_TIMESTAMP_PATTERN = re.compile(r"^(\d{2}):(\d{2})\.(\d{3})$")


def parse_vtt_text(text: str) -> KaraokeDocument:
    """Parse WebVTT subtitle text into a validated ``KaraokeDocument``."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.lstrip("\ufeff").startswith("WEBVTT"):
        raise UnsupportedTranscriptFormatError("VTT file must begin with WEBVTT")

    lines = normalized.split("\n")
    cue_blocks = _extract_vtt_cue_blocks(lines)
    karaoke_lines: list[KaraokeLine] = []

    for block_index, block in enumerate(cue_blocks):
        line = _parse_vtt_block(block, block_index=block_index)
        if line is not None:
            karaoke_lines.append(line)

    if not karaoke_lines:
        raise TranscriptValidationError("VTT transcript is empty")

    document = KaraokeDocument(lines=tuple(karaoke_lines), source_format=_SOURCE_FORMAT)
    ensure_valid_document(document)
    return document


def load_vtt(path: str | Path) -> KaraokeDocument:
    """Load and parse a WebVTT subtitle file from disk."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Cannot read VTT file {file_path}: {exc}"
        ) from exc
    return parse_vtt_text(text)


def _extract_vtt_cue_blocks(lines: list[str]) -> list[list[str]]:
    index = 0
    if index < len(lines) and lines[index].strip().lstrip("\ufeff").startswith("WEBVTT"):
        index += 1

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            break
        if "-->" in line:
            break
        index += 1

    blocks: list[list[str]] = []
    current_block: list[str] = []
    in_note_block = False

    while index < len(lines):
        line = lines[index].strip()
        index += 1

        if line.upper().startswith("NOTE"):
            if current_block:
                blocks.append(current_block)
                current_block = []
            in_note_block = True
            continue

        if in_note_block:
            if not line:
                in_note_block = False
            continue

        if not line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue

        current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return blocks


def _parse_vtt_block(block: list[str], *, block_index: int) -> KaraokeLine | None:
    if not block:
        return None

    timing_index = _find_timing_line_index(block)
    if timing_index is None:
        raise UnsupportedTranscriptFormatError(
            f"VTT block {block_index} is missing a timing line"
        )

    timing_line = block[timing_index]
    text_lines = block[timing_index + 1 :]
    if not text_lines:
        return None

    start, end = _parse_vtt_timing_line(timing_line, block_index=block_index)
    cue_text = " ".join(text_lines)
    return build_karaoke_line(cue_text, start, end)


def _find_timing_line_index(block: list[str]) -> int | None:
    for index, line in enumerate(block):
        if "-->" in line:
            return index
    return None


def _parse_vtt_timing_line(timing_line: str, *, block_index: int) -> tuple[float, float]:
    match = _TIMING_LINE_PATTERN.match(timing_line.strip())
    if not match:
        raise UnsupportedTranscriptFormatError(
            f"Malformed VTT timing line in block {block_index}: {timing_line!r}"
        )

    start = _parse_vtt_timestamp(match.group(1).strip(), block_index=block_index)
    end = _parse_vtt_timestamp(match.group(2).strip(), block_index=block_index)
    if end <= start:
        raise UnsupportedTranscriptFormatError(
            f"VTT cue end time must be greater than start time in block {block_index}"
        )
    return start, end


def _parse_vtt_timestamp(timestamp: str, *, block_index: int) -> float:
    full_match = _FULL_TIMESTAMP_PATTERN.match(timestamp)
    if full_match:
        hours, minutes, seconds, milliseconds = (int(part) for part in full_match.groups())
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

    short_match = _SHORT_TIMESTAMP_PATTERN.match(timestamp)
    if short_match:
        minutes, seconds, milliseconds = (int(part) for part in short_match.groups())
        return minutes * 60 + seconds + milliseconds / 1000.0

    raise UnsupportedTranscriptFormatError(
        f"Malformed VTT timestamp in block {block_index}: {timestamp!r}"
    )
```

* modified `karaoke_engine/parsers/__init__.py`

```python
"""Transcript parsers."""

from karaoke_engine.parsers.srt import load_srt, parse_srt_text
from karaoke_engine.parsers.vtt import load_vtt, parse_vtt_text
from karaoke_engine.parsers.whisper_json import load_whisper_json, parse_whisper_json

__all__ = [
    "load_srt",
    "load_vtt",
    "load_whisper_json",
    "parse_srt_text",
    "parse_vtt_text",
    "parse_whisper_json",
]
```

* modified `karaoke_engine/engine.py`

```python
"""High-level karaoke engine API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.ass.writer import AssWriter
from karaoke_engine.errors import AssGenerationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument
from karaoke_engine.parsers.srt import load_srt
from karaoke_engine.parsers.vtt import load_vtt
from karaoke_engine.parsers.whisper_json import load_whisper_json
from karaoke_engine.render.ffmpeg import RenderOptions, render_ass_to_video
from karaoke_engine.render.probe import probe_video
from karaoke_engine.segmenter import SegmentOptions, segment_document

_SUPPORTED_TRANSCRIPT_SUFFIXES = {".json", ".srt", ".vtt"}
_DEFAULT_PLAY_RES_X = 1920
_DEFAULT_PLAY_RES_Y = 1080


@dataclass(frozen=True, slots=True)
class CreateAssResult:
    """Metadata returned after creating a karaoke ASS file."""

    ass_path: Path
    line_count: int
    word_count: int
    source_format: str
    segmented: bool


@dataclass(frozen=True, slots=True)
class RenderKaraokeVideoResult:
    """Metadata returned after rendering a karaoke video."""

    video_path: Path
    ass_path: Path
    output_path: Path
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
        """Load a transcript, optionally segment, and write a karaoke ASS file."""
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

    def render_video(
        self,
        *,
        video_path: str | Path,
        transcript_path: str | Path,
        output_path: str | Path,
        ass_output_path: str | Path | None = None,
        style: KaraokeStyle | None = None,
        segment_options: SegmentOptions | None = None,
        segment: bool = True,
        play_res_x: int | None = None,
        play_res_y: int | None = None,
        title: str = "Karaoke",
        render_options: RenderOptions | None = None,
        auto_probe_resolution: bool = True,
    ) -> RenderKaraokeVideoResult:
        """Create ASS subtitles and burn them into an output video with FFmpeg."""
        source_video = Path(video_path)
        rendered_output = Path(output_path)
        subtitle_output = (
            Path(ass_output_path)
            if ass_output_path is not None
            else rendered_output.with_suffix(".ass")
        )

        resolved_play_res_x, resolved_play_res_y = _resolve_play_resolution(
            source_video=source_video,
            play_res_x=play_res_x,
            play_res_y=play_res_y,
            auto_probe_resolution=auto_probe_resolution,
        )

        ass_result = self.create_ass(
            transcript_path=transcript_path,
            output_path=subtitle_output,
            style=style,
            segment_options=segment_options,
            segment=segment,
            play_res_x=resolved_play_res_x,
            play_res_y=resolved_play_res_y,
            title=title,
        )

        render_ass_to_video(
            video_path=source_video,
            ass_path=ass_result.ass_path,
            output_path=rendered_output,
            options=render_options,
        )

        return RenderKaraokeVideoResult(
            video_path=source_video,
            ass_path=ass_result.ass_path,
            output_path=rendered_output,
            line_count=ass_result.line_count,
            word_count=ass_result.word_count,
            source_format=ass_result.source_format,
            segmented=ass_result.segmented,
        )


def _load_transcript(path: Path) -> KaraokeDocument:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_whisper_json(path)
    if suffix == ".srt":
        return load_srt(path)
    if suffix == ".vtt":
        return load_vtt(path)
    raise UnsupportedTranscriptFormatError(
        f"Unsupported transcript format {path.suffix!r}: "
        "supported formats are .json, .srt, and .vtt"
    )


def _count_words(document: KaraokeDocument) -> int:
    return sum(len(line.words) for line in document.lines)


def _ensure_output_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_play_resolution(
    *,
    source_video: Path,
    play_res_x: int | None,
    play_res_y: int | None,
    auto_probe_resolution: bool,
) -> tuple[int, int]:
    resolved_play_res_x = play_res_x
    resolved_play_res_y = play_res_y

    if auto_probe_resolution and (play_res_x is None or play_res_y is None):
        video_info = probe_video(source_video)
        if play_res_x is None:
            resolved_play_res_x = video_info.width
        if play_res_y is None:
            resolved_play_res_y = video_info.height

    if resolved_play_res_x is None:
        resolved_play_res_x = _DEFAULT_PLAY_RES_X
    if resolved_play_res_y is None:
        resolved_play_res_y = _DEFAULT_PLAY_RES_Y

    return resolved_play_res_x, resolved_play_res_y
```

* modified root `karaoke_engine/__init__.py`

```python
"""Lightweight server-friendly karaoke subtitle engine."""

from karaoke_engine.errors import (
    AssGenerationError,
    KaraokeEngineError,
    RenderError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)
from karaoke_engine.ass import AssWriter, KaraokeStyle, escape_ass_text
from karaoke_engine.engine import CreateAssResult, KaraokeEngine, RenderKaraokeVideoResult
from karaoke_engine.models import (
    KaraokeDocument,
    KaraokeLine,
    ValidationReport,
    ValidationWarning,
    Word,
)
from karaoke_engine.parsers import (
    load_srt,
    load_vtt,
    load_whisper_json,
    parse_srt_text,
    parse_vtt_text,
    parse_whisper_json,
)
from karaoke_engine.render import (
    RenderOptions,
    RenderVideoResult,
    VideoInfo,
    build_ffmpeg_ass_burn_command,
    build_ffprobe_command,
    probe_video,
    render_ass_to_video,
)
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
    "RenderError",
    "RenderKaraokeVideoResult",
    "RenderOptions",
    "RenderVideoResult",
    "SegmentOptions",
    "TranscriptValidationError",
    "UnsupportedTranscriptFormatError",
    "ValidationReport",
    "ValidationWarning",
    "VideoInfo",
    "Word",
    "build_ffmpeg_ass_burn_command",
    "build_ffprobe_command",
    "escape_ass_text",
    "load_srt",
    "load_vtt",
    "load_whisper_json",
    "parse_srt_text",
    "parse_vtt_text",
    "parse_whisper_json",
    "probe_video",
    "render_ass_to_video",
    "segment_document",
]

__version__ = "0.1.0"
```

* updated README supported-input section

```markdown
## Supported input

- **Whisper JSON with word timestamps** — best option; provides real per-word karaoke timing.
- **SRT** — supported with **approximate** word timing derived by evenly splitting each cue duration across its words. SRT files usually do not contain true word-level timestamps.
- **VTT (WebVTT)** — supported with **approximate** word timing using the same cue-duration split approach. VTT files usually do not contain true word-level timestamps.
```

## Example SRT Input

```
1
00:00:01,000 --> 00:00:03,500
Hello world!
```

## Example VTT Input

```
WEBVTT

00:00:01.000 --> 00:00:03.500
Hello world!
```

## Example Parsed Output

```
KaraokeDocument(
  lines=(
    KaraokeLine(
      words=(
        Word(text='Hello', start=1.0, end=2.25),
        Word(text='world!', start=2.25, end=3.5),
      ),
      start=1.0,
      end=3.5,
    ),
  ),
  source_format='srt_approx',
)
```

## Design Decisions

- **Approximate timing only**: SRT/VTT cues are split evenly across whitespace-separated words; `source_format` uses `_approx` suffix to signal non-Whisper timing.
- **Shared cue helpers**: `cue_utils.py` centralizes tag stripping, word splitting, and duration distribution for both parsers.
- **One KaraokeLine per cue**: Each subtitle cue becomes one line with approximate words, matching Gate 3's per-segment structure.
- **Engine extension routing**: `_load_transcript()` selects parser by lowercase file suffix without changing `create_ass()` or `render_video()` signatures.
- **Validation unchanged**: Parsed documents still pass through `ensure_valid_document()` before return.
- **Empty cue handling**: Cues with no text after tag stripping are ignored rather than producing empty lines.

## Risks / Questions

- **Not true karaoke timing**: Even word splits do not reflect actual sung syllable timing; Whisper JSON remains the recommended input.
- **Simple tag stripping**: Only basic `<tag>` removal is supported; complex VTT styling or entities may need future handling.
- **VTT cue settings**: Timing-line settings after `-->` are accepted but not interpreted.
- **Overlapping cues**: Overlapping SRT/VTT cues are preserved as separate lines without merge logic.
- **Single-word cues with punctuation-only text**: Empty cues after stripping are skipped; callers should ensure cues contain readable words.

## Gatekeeper Review Request

Please review Gate 7 and tell me whether it is APPROVED or BLOCKED.
