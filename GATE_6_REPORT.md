# Gate 6 Report — FFmpeg Video Rendering

## Status

PASS

## Summary

Gate 6 adds optional FFmpeg video rendering to `karaoke_engine`. The new `render` package builds safe list-based FFmpeg/FFprobe commands, burns ASS subtitles into MP4 output, probes video resolution, and integrates with `KaraokeEngine.render_video()` for an end-to-end Whisper JSON → segmented ASS → burned-in video workflow. All subprocess usage avoids `shell=True`; tests mock external binaries.

## Files Created

- `karaoke_engine/render/__init__.py`
- `karaoke_engine/render/ffmpeg.py`
- `karaoke_engine/render/probe.py`
- `tests/test_ffmpeg.py`
- `tests/test_probe.py`
- `tests/test_engine_render.py`
- `GATE_6_REPORT.md`

## Files Modified

- `karaoke_engine/errors.py`
- `karaoke_engine/engine.py`
- `karaoke_engine/__init__.py`
- `README.md`
- `tests/test_engine.py`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* RenderOptions dataclass
* RenderVideoResult dataclass
* FFmpeg command builder
* FFmpeg runner
* FFprobe command builder
* FFprobe parser
* VideoInfo dataclass
* Engine render_video()
* Auto probe resolution
* Sidecar ASS path handling
* Public exports
* README update
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* SRT parser
* VTT parser
* Web UI
* Frappe integration
* OpenAI API calls
* Local Whisper
* Local LLM
* Bundled FFmpeg
* Browser rendering

## Test Result

```
python -m pytest -q
........................................................................ [ 67%]
...................................                                      [100%]
107 passed in 0.25s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/render/ffmpeg.py`

```python
"""FFmpeg ASS burn-in rendering."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from karaoke_engine.errors import RenderError

_FFMPEG_BINARY = "ffmpeg"


@dataclass(frozen=True, slots=True)
class RenderOptions:
    """FFmpeg encoding options for ASS burn-in rendering."""

    crf: int = 18
    preset: str = "veryfast"
    video_codec: str = "libx264"
    audio_codec: str = "copy"
    timeout_seconds: float = 1800.0
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.crf <= 51:
            raise ValueError("crf must be between 0 and 51")
        if not self.preset:
            raise ValueError("preset must be non-empty")
        if not self.video_codec:
            raise ValueError("video_codec must be non-empty")
        if not self.audio_codec:
            raise ValueError("audio_codec must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")


@dataclass(frozen=True, slots=True)
class RenderVideoResult:
    """Metadata returned after rendering ASS subtitles into a video."""

    video_path: Path
    ass_path: Path
    output_path: Path
    return_code: int
    stderr: str


def build_ffmpeg_ass_burn_command(
    *,
    video_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    options: RenderOptions | None = None,
) -> list[str]:
    """Build an FFmpeg command list for ASS subtitle burn-in."""
    render_options = options or RenderOptions()
    escaped_ass_path = _escape_ass_filter_path(Path(ass_path))
    command = [
        _FFMPEG_BINARY,
        "-y" if render_options.overwrite else "-n",
        "-i",
        str(video_path),
        "-vf",
        f"ass={escaped_ass_path}",
        "-c:v",
        render_options.video_codec,
        "-crf",
        str(render_options.crf),
        "-preset",
        render_options.preset,
        "-c:a",
        render_options.audio_codec,
        str(output_path),
    ]
    return command


def render_ass_to_video(
    *,
    video_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    options: RenderOptions | None = None,
) -> RenderVideoResult:
    """Burn ASS subtitles into a video using FFmpeg."""
    render_options = options or RenderOptions()
    source_video = Path(video_path)
    subtitle_file = Path(ass_path)
    rendered_output = Path(output_path)

    if not source_video.is_file():
        raise RenderError(f"Input video file does not exist: {source_video}")
    if not subtitle_file.is_file():
        raise RenderError(f"ASS subtitle file does not exist: {subtitle_file}")

    rendered_output.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_ass_burn_command(
        video_path=source_video,
        ass_path=subtitle_file,
        output_path=rendered_output,
        options=render_options,
    )

    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=render_options.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            f"FFmpeg render timed out after {render_options.timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise RenderError(f"Failed to execute FFmpeg: {exc}") from exc

    stderr = completed.stderr or ""
    if completed.returncode != 0:
        raise RenderError(
            f"FFmpeg render failed with exit code {completed.returncode}: {stderr.strip()}"
        )
    if not rendered_output.is_file():
        raise RenderError(
            f"FFmpeg reported success but output file was not created: {rendered_output}"
        )

    return RenderVideoResult(
        video_path=source_video,
        ass_path=subtitle_file,
        output_path=rendered_output,
        return_code=completed.returncode,
        stderr=stderr,
    )


def _escape_ass_filter_path(path: Path) -> str:
    """Return an FFmpeg ``ass`` filter-safe path string."""
    posix_path = path.resolve().as_posix()
    return (
        posix_path.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )
```

* `karaoke_engine/render/probe.py`

```python
"""FFprobe video inspection helpers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_engine.errors import RenderError

_FFPROBE_BINARY = "ffprobe"


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Basic video stream metadata from FFprobe."""

    width: int
    height: int
    duration_seconds: float | None = None


def build_ffprobe_command(path: str | Path) -> list[str]:
    """Build an FFprobe command list for JSON stream metadata."""
    return [
        _FFPROBE_BINARY,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]


def probe_video(path: str | Path, timeout_seconds: float = 30.0) -> VideoInfo:
    """Probe a video file and return width, height, and optional duration."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")

    video_path = Path(path)
    if not video_path.is_file():
        raise RenderError(f"Input video file does not exist: {video_path}")

    command = build_ffprobe_command(video_path)
    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            f"FFprobe timed out after {timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise RenderError(f"Failed to execute FFprobe: {exc}") from exc

    stderr = completed.stderr or ""
    if completed.returncode != 0:
        raise RenderError(
            f"FFprobe failed with exit code {completed.returncode}: {stderr.strip()}"
        )

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RenderError("FFprobe returned invalid JSON output") from exc

    return _parse_ffprobe_json(payload)


def _parse_ffprobe_json(payload: dict[str, Any]) -> VideoInfo:
    streams = payload.get("streams")
    if not isinstance(streams, list) or not streams:
        raise RenderError("FFprobe JSON output is missing video stream data")

    stream = streams[0]
    if not isinstance(stream, dict):
        raise RenderError("FFprobe JSON stream entry must be an object")

    width = stream.get("width")
    height = stream.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise RenderError("FFprobe JSON output is missing width/height")

    duration_seconds = _parse_duration(payload)
    return VideoInfo(
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )


def _parse_duration(payload: dict[str, Any]) -> float | None:
    format_section = payload.get("format")
    if not isinstance(format_section, dict):
        return None

    duration_value = format_section.get("duration")
    if duration_value is None:
        return None

    try:
        return float(duration_value)
    except (TypeError, ValueError) as exc:
        raise RenderError(
            f"FFprobe returned invalid duration value: {duration_value!r}"
        ) from exc
```

* `karaoke_engine/render/__init__.py`

```python
"""FFmpeg video rendering helpers."""

from karaoke_engine.render.ffmpeg import (
    RenderOptions,
    RenderVideoResult,
    build_ffmpeg_ass_burn_command,
    render_ass_to_video,
)
from karaoke_engine.render.probe import VideoInfo, build_ffprobe_command, probe_video

__all__ = [
    "RenderOptions",
    "RenderVideoResult",
    "VideoInfo",
    "build_ffmpeg_ass_burn_command",
    "build_ffprobe_command",
    "probe_video",
    "render_ass_to_video",
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
from karaoke_engine.parsers.whisper_json import load_whisper_json
from karaoke_engine.render.ffmpeg import RenderOptions, render_ass_to_video
from karaoke_engine.render.probe import probe_video
from karaoke_engine.segmenter import SegmentOptions, segment_document

_SUPPORTED_TRANSCRIPT_SUFFIXES = {".json"}
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
    if suffix not in _SUPPORTED_TRANSCRIPT_SUFFIXES:
        raise UnsupportedTranscriptFormatError(
            f"Unsupported transcript format {path.suffix!r}: only .json is supported"
        )
    return load_whisper_json(path)


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
from karaoke_engine.parsers import load_whisper_json, parse_whisper_json
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
    "load_whisper_json",
    "parse_whisper_json",
    "probe_video",
    "render_ass_to_video",
    "segment_document",
]

__version__ = "0.1.0"
```

* updated README render section

```markdown
## Optional FFmpeg rendering

Video rendering is optional and requires system **`ffmpeg`** and **`ffprobe`** installed on the server. FFmpeg is not bundled with this package.

## Basic video render usage

```python
from karaoke_engine import KaraokeEngine, RenderOptions

engine = KaraokeEngine()
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="karaoke_output.mp4",
    render_options=RenderOptions(crf=18, preset="veryfast"),
)
print(result.output_path)
```
```

## Example Render Usage

```python
from karaoke_engine import KaraokeEngine, RenderOptions

engine = KaraokeEngine()
result = engine.render_video(
    video_path="input.mp4",
    transcript_path="transcript.json",
    output_path="karaoke_output.mp4",
    render_options=RenderOptions(crf=18, preset="veryfast"),
)
print(result.output_path)
```

## Example FFmpeg Command

```python
[
    "ffmpeg",
    "-y",
    "-i",
    "input.mp4",
    "-vf",
    "ass=karaoke.ass",
    "-c:v",
    "libx264",
    "-crf",
    "18",
    "-preset",
    "veryfast",
    "-c:a",
    "copy",
    "karaoke_output.mp4",
]
```

## Design Decisions

- **`RenderError` exception**: Dedicated render/probe failures separate from ASS generation errors while remaining under `KaraokeEngineError`.
- **List-only subprocess**: FFmpeg and FFprobe are invoked with `shell=False` and explicit argument lists for server safety.
- **ASS filter path escaping**: Paths are normalized to POSIX and escaped for FFmpeg `ass=` filter syntax, including colon escaping on Windows drive letters.
- **Engine orchestration**: `render_video()` reuses `create_ass()` unchanged, then calls `render_ass_to_video()` for burn-in.
- **Sidecar ASS default**: When `ass_output_path` is omitted, ASS is written beside the output video using the same stem (`.ass`).
- **Auto probe resolution**: FFprobe fills missing `play_res_x`/`play_res_y` values so ASS PlayRes matches source video when not explicitly overridden.
- **Mocked tests**: Subprocess calls are mocked so CI does not require system FFmpeg.

## Risks / Questions

- **System dependency**: Rendering fails at runtime if `ffmpeg`/`ffprobe` are not installed or not on `PATH`.
- **Windows path escaping**: ASS filter escaping is implemented conservatively but may need refinement for unusual path characters.
- **Audio copy failures**: Default `audio_codec="copy"` may fail when output container/format differs from input; callers can override via `RenderOptions`.
- **No render progress**: Long renders block until FFmpeg exits or times out; no streaming progress reporting yet.
- **Probe before existence check**: `render_video()` probes resolution before `render_ass_to_video()` validates the video file for rendering; missing videos fail during probe or ASS creation depending on call order.

## Gatekeeper Review Request

Please review Gate 6 and tell me whether it is APPROVED or BLOCKED.
