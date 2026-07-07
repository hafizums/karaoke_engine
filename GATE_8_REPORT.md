# Gate 8 Report — Production Hardening & Release Readiness

## Status

PASS

## Summary

Gate 8 hardens the karaoke engine for production readiness without adding runtime dependencies. Validation now checks line/word timing consistency and overlapping words, `KaraokeStyle` and `AssWriter` reject invalid configuration, FFmpeg/FFprobe helpers validate paths more strictly, Windows ASS filter paths are quoted for FFmpeg reliability, examples and CHANGELOG were added, and README/pyproject metadata were expanded for release use.

## Files Created

- `examples/whisper_sample.json`
- `examples/sample.srt`
- `examples/sample.vtt`
- `tests/test_validation_hardening.py`
- `tests/test_style_hardening.py`
- `tests/test_release_readiness.py`
- `CHANGELOG.md`
- `GATE_8_REPORT.md`

## Files Modified

- `karaoke_engine/validators.py`
- `karaoke_engine/ass/styles.py`
- `karaoke_engine/ass/writer.py`
- `karaoke_engine/render/ffmpeg.py`
- `karaoke_engine/render/probe.py`
- `README.md`
- `pyproject.toml`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* Validation hardening
* ASS style validation
* ASS writer option validation
* FFmpeg/probe hardening
* Examples
* README update
* CHANGELOG
* Release metadata review
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* Audio transcription
* OpenAI API calls
* Local Whisper
* Local LLM
* PyTorch
* CUDA
* Web UI
* Frappe integration
* Browser rendering
* Bundled FFmpeg

## Test Result

```
python -m pytest -q
........................................................................ [ 43%]
........................................................................ [ 86%]
.......................                                                  [100%]
167 passed in 0.48s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/validators.py`

```python
"""Validation helpers for karaoke documents."""

from __future__ import annotations

import re

from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, ValidationReport, Word

_ASS_OVERRIDE_TAG_PATTERN = re.compile(r"\{[^}]*\}")
_TIMING_TOLERANCE_SECONDS = 0.001


def _validate_timestamp(value: float, path: str, report: ValidationReport) -> None:
    if value < 0:
        report.add_error(
            code="negative_timestamp",
            message=f"Timestamp must not be negative: {value}",
            path=path,
        )


def _validate_word_timing(word: Word, path: str, report: ValidationReport) -> None:
    _validate_timestamp(word.start, f"{path}.start", report)
    _validate_timestamp(word.end, f"{path}.end", report)
    if word.end <= word.start:
        report.add_error(
            code="invalid_word_timing",
            message=(
                f"Word end time must be greater than start time: "
                f"start={word.start}, end={word.end}"
            ),
            path=path,
        )


def _validate_text(text: str, path: str, report: ValidationReport) -> None:
    if not text or not text.strip():
        report.add_error(
            code="empty_text",
            message="Text must not be empty",
            path=path,
        )
        return

    if _ASS_OVERRIDE_TAG_PATTERN.search(text):
        report.add_error(
            code="ass_override_tag",
            message="Raw ASS override tags are not allowed in transcript text",
            path=path,
        )


def _validate_line_word_consistency(
    line: KaraokeLine,
    path: str,
    report: ValidationReport,
) -> None:
    if not line.words:
        return

    first_word = line.words[0]
    last_word = line.words[-1]

    if line.start > first_word.start + _TIMING_TOLERANCE_SECONDS:
        report.add_error(
            code="line_start_after_first_word",
            message=(
                f"Line start must be less than or equal to first word start: "
                f"line_start={line.start}, first_word_start={first_word.start}"
            ),
            path=path,
        )

    if line.end + _TIMING_TOLERANCE_SECONDS < last_word.end:
        report.add_error(
            code="line_end_before_last_word",
            message=(
                f"Line end must be greater than or equal to last word end: "
                f"line_end={line.end}, last_word_end={last_word.end}"
            ),
            path=path,
        )

    for index in range(1, len(line.words)):
        previous_word = line.words[index - 1]
        current_word = line.words[index]

        if current_word.start + _TIMING_TOLERANCE_SECONDS < previous_word.start:
            report.add_error(
                code="word_start_order",
                message=(
                    "Words inside a line must be in non-decreasing start-time order: "
                    f"previous_start={previous_word.start}, "
                    f"current_start={current_word.start}"
                ),
                path=f"{path}.words[{index}]",
            )

        if current_word.start + _TIMING_TOLERANCE_SECONDS < previous_word.end:
            report.add_warning(
                code="overlapping_words",
                message=(
                    "Words overlap beyond timing tolerance: "
                    f"previous_end={previous_word.end}, "
                    f"current_start={current_word.start}"
                ),
                path=f"{path}.words[{index}]",
            )


def validate_word(word: Word, path: str = "word") -> ValidationReport:
    """Validate a single word."""
    report = ValidationReport()
    _validate_text(word.text, f"{path}.text", report)
    _validate_word_timing(word, path, report)
    return report


def validate_line(line: KaraokeLine, path: str = "line") -> ValidationReport:
    """Validate a karaoke line and its words."""
    report = ValidationReport()
    _validate_timestamp(line.start, f"{path}.start", report)
    _validate_timestamp(line.end, f"{path}.end", report)
    if line.end <= line.start:
        report.add_error(
            code="invalid_line_timing",
            message=(
                f"Line end time must be greater than start time: "
                f"start={line.start}, end={line.end}"
            ),
            path=path,
        )

    if not line.words:
        report.add_error(
            code="empty_line",
            message="Line must contain at least one word",
            path=path,
        )

    for index, word in enumerate(line.words):
        word_report = validate_word(word, path=f"{path}.words[{index}]")
        report.warnings.extend(word_report.warnings)
        report.errors.extend(word_report.errors)

    _validate_line_word_consistency(line, path, report)
    return report


def validate_document(document: KaraokeDocument) -> ValidationReport:
    """Validate a karaoke document."""
    report = ValidationReport()

    if not document.source_format or not document.source_format.strip():
        report.add_error(
            code="empty_source_format",
            message="Document source_format must be non-empty",
            path="document.source_format",
        )

    if not document.lines:
        report.add_error(
            code="empty_document",
            message="Document must contain at least one line",
            path="document",
        )

    for index, line in enumerate(document.lines):
        line_report = validate_line(line, path=f"lines[{index}]")
        report.warnings.extend(line_report.warnings)
        report.errors.extend(line_report.errors)

    return report


def ensure_valid_document(document: KaraokeDocument) -> ValidationReport:
    """Validate a document and raise if invalid."""
    report = validate_document(document)
    if not report.is_valid:
        messages = "; ".join(error.message for error in report.errors)
        raise TranscriptValidationError(messages)
    return report
```

* `karaoke_engine/ass/styles.py`

```python
"""ASS style definitions for karaoke subtitles."""

from __future__ import annotations

import re
from dataclasses import dataclass

_ASS_COLOR_PATTERN = re.compile(r"^&H([0-9A-Fa-f]{8}|[0-9A-Fa-f]{6})$")


def _ass_bool(value: bool) -> int:
    return -1 if value else 0


def _validate_ass_color(value: str, field_name: str) -> None:
    if not _ASS_COLOR_PATTERN.match(value):
        raise ValueError(
            f"{field_name} must be an ASS color in &HAABBGGRR or &HBBGGRR format"
        )


@dataclass(frozen=True, slots=True)
class KaraokeStyle:
    """ASS V4+ style definition for karaoke dialogue."""

    name: str
    font_name: str
    font_size: int
    primary_color: str
    secondary_color: str
    outline_color: str
    back_color: str
    bold: bool
    italic: bool
    underline: bool
    strikeout: bool
    scale_x: int
    scale_y: int
    spacing: int
    angle: float
    border_style: int
    outline: int
    shadow: int
    alignment: int
    margin_l: int
    margin_r: int
    margin_v: int
    encoding: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.font_name.strip():
            raise ValueError("font_name must be non-empty")
        if self.font_size <= 0:
            raise ValueError("font_size must be > 0")
        for field_name, color in (
            ("primary_color", self.primary_color),
            ("secondary_color", self.secondary_color),
            ("outline_color", self.outline_color),
            ("back_color", self.back_color),
        ):
            _validate_ass_color(color, field_name)
        if self.scale_x <= 0:
            raise ValueError("scale_x must be > 0")
        if self.scale_y <= 0:
            raise ValueError("scale_y must be > 0")
        if self.border_style not in {1, 3}:
            raise ValueError("border_style must be 1 or 3")
        if self.outline < 0:
            raise ValueError("outline must be >= 0")
        if self.shadow < 0:
            raise ValueError("shadow must be >= 0")
        if not 1 <= self.alignment <= 9:
            raise ValueError("alignment must be between 1 and 9")
        if self.margin_l < 0:
            raise ValueError("margin_l must be >= 0")
        if self.margin_r < 0:
            raise ValueError("margin_r must be >= 0")
        if self.margin_v < 0:
            raise ValueError("margin_v must be >= 0")
        if self.encoding < 0:
            raise ValueError("encoding must be >= 0")

    @classmethod
    def default_1080p(cls) -> KaraokeStyle:
        """Style preset for 1920x1080 landscape karaoke."""
        return cls(
            name="Karaoke",
            font_name="Arial",
            font_size=72,
            primary_color="&H00FFFFFF",
            secondary_color="&H0000FFFF",
            outline_color="&H00000000",
            back_color="&H64000000",
            bold=False,
            italic=False,
            underline=False,
            strikeout=False,
            scale_x=100,
            scale_y=100,
            spacing=0,
            angle=0.0,
            border_style=1,
            outline=3,
            shadow=1,
            alignment=2,
            margin_l=40,
            margin_r=40,
            margin_v=60,
            encoding=1,
        )

    @classmethod
    def default_720p(cls) -> KaraokeStyle:
        """Style preset for 1280x720 landscape karaoke."""
        return cls(
            name="Karaoke",
            font_name="Arial",
            font_size=48,
            primary_color="&H00FFFFFF",
            secondary_color="&H0000FFFF",
            outline_color="&H00000000",
            back_color="&H64000000",
            bold=False,
            italic=False,
            underline=False,
            strikeout=False,
            scale_x=100,
            scale_y=100,
            spacing=0,
            angle=0.0,
            border_style=1,
            outline=2,
            shadow=1,
            alignment=2,
            margin_l=30,
            margin_r=30,
            margin_v=40,
            encoding=1,
        )

    @classmethod
    def mobile_1080x1920(cls) -> KaraokeStyle:
        """Style preset for 1080x1920 portrait mobile karaoke."""
        return cls(
            name="Karaoke",
            font_name="Arial",
            font_size=64,
            primary_color="&H00FFFFFF",
            secondary_color="&H0000FFFF",
            outline_color="&H00000000",
            back_color="&H64000000",
            bold=False,
            italic=False,
            underline=False,
            strikeout=False,
            scale_x=100,
            scale_y=100,
            spacing=0,
            angle=0.0,
            border_style=1,
            outline=3,
            shadow=1,
            alignment=2,
            margin_l=50,
            margin_r=50,
            margin_v=140,
            encoding=1,
        )

    def to_ass_style_line(self) -> str:
        """Render this style as an ASS ``Style:`` line."""
        return (
            f"Style: {self.name},"
            f"{self.font_name},"
            f"{self.font_size},"
            f"{self.primary_color},"
            f"{self.secondary_color},"
            f"{self.outline_color},"
            f"{self.back_color},"
            f"{_ass_bool(self.bold)},"
            f"{_ass_bool(self.italic)},"
            f"{_ass_bool(self.underline)},"
            f"{_ass_bool(self.strikeout)},"
            f"{self.scale_x},"
            f"{self.scale_y},"
            f"{self.spacing},"
            f"{self.angle},"
            f"{self.border_style},"
            f"{self.outline},"
            f"{self.shadow},"
            f"{self.alignment},"
            f"{self.margin_l},"
            f"{self.margin_r},"
            f"{self.margin_v},"
            f"{self.encoding}"
        )
```

* modified `karaoke_engine/ass/writer.py`

```python
"""ASS subtitle writer for karaoke documents."""

from __future__ import annotations

from pathlib import Path

from karaoke_engine.ass.escape import escape_ass_text
from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.errors import AssGenerationError, TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.utils.timecode import seconds_to_ass_time, seconds_to_centiseconds
from karaoke_engine.validators import ensure_valid_document

_STYLE_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
    "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
    "MarginR, MarginV, Encoding"
)
_EVENT_FORMAT = (
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
)
_MIN_WORD_DURATION_CS = 1
_KARAOKE_TAG = "kf"


class AssWriter:
    """Generate deterministic ASS karaoke subtitle files from documents."""

    def __init__(
        self,
        style: KaraokeStyle | None = None,
        *,
        play_res_x: int = 1920,
        play_res_y: int = 1080,
        title: str = "Karaoke",
    ) -> None:
        if play_res_x <= 0:
            raise ValueError("play_res_x must be > 0")
        if play_res_y <= 0:
            raise ValueError("play_res_y must be > 0")
        if not title.strip():
            raise ValueError("title must be non-empty")

        self.style = style or KaraokeStyle.default_1080p()
        self.play_res_x = play_res_x
        self.play_res_y = play_res_y
        self.title = title

    def generate(self, document: KaraokeDocument) -> str:
        """Validate and return a complete ASS file as a string."""
        ensure_valid_document(document)
        sections = [
            self._render_script_info(),
            self._render_styles(),
            self._render_events(document),
        ]
        return "\n".join(sections) + "\n"

    def write_to_file(self, document: KaraokeDocument, path: str | Path) -> None:
        """Validate, generate, and write ASS output to ``path`` as UTF-8."""
        output_path = Path(path)
        try:
            content = self.generate(document)
            output_path.write_text(content, encoding="utf-8", newline="\n")
        except TranscriptValidationError:
            raise
        except OSError as exc:
            raise AssGenerationError(
                f"Failed to write ASS file to {output_path}: {exc}"
            ) from exc

    def _render_script_info(self) -> str:
        lines = [
            "[Script Info]",
            f"Title: {self.title}",
            "ScriptType: v4.00+",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            f"PlayResX: {self.play_res_x}",
            f"PlayResY: {self.play_res_y}",
        ]
        return "\n".join(lines)

    def _render_styles(self) -> str:
        lines = [
            "",
            "[V4+ Styles]",
            _STYLE_FORMAT,
            self.style.to_ass_style_line(),
        ]
        return "\n".join(lines)

    def _render_events(self, document: KaraokeDocument) -> str:
        dialogue_lines = [
            self._render_dialogue(line)
            for line in document.lines
        ]
        lines = [
            "",
            "[Events]",
            _EVENT_FORMAT,
            *dialogue_lines,
        ]
        return "\n".join(lines)

    def _render_dialogue(self, line: KaraokeLine) -> str:
        start = seconds_to_ass_time(line.start)
        end = seconds_to_ass_time(line.end)
        text = self._render_karaoke_text(line.words)
        return (
            f"Dialogue: 0,{start},{end},{self.style.name},,0,0,0,,{text}"
        )

    def _render_karaoke_text(self, words: tuple[Word, ...]) -> str:
        parts: list[str] = []
        for word in words:
            duration_cs = max(
                _MIN_WORD_DURATION_CS,
                seconds_to_centiseconds(word.end - word.start),
            )
            escaped_text = escape_ass_text(word.text)
            parts.append(f"{{\\{_KARAOKE_TAG}{duration_cs}}}{escaped_text}")
        return " ".join(parts)
```

* modified `karaoke_engine/render/ffmpeg.py`

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
    if not str(video_path).strip():
        raise RenderError("video_path must be non-empty")
    if not str(ass_path).strip():
        raise RenderError("ass_path must be non-empty")
    if not str(output_path).strip():
        raise RenderError("output_path must be non-empty")

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
    if rendered_output.exists() and rendered_output.is_dir():
        raise RenderError(f"Output path is an existing directory: {rendered_output}")

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
    if len(posix_path) >= 2 and posix_path[1] == ":":
        inner = f"{posix_path[0]}\\:{posix_path[2:]}"
    else:
        inner = posix_path
    inner = inner.replace("'", "\\'")
    return f"'{inner}'"
```

* modified `karaoke_engine/render/probe.py`

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
    if not str(path).strip():
        raise RenderError("path must be non-empty")
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

* updated README production notes section

```markdown
## Production notes

- The engine converts existing transcripts; it does not transcribe audio.
- No OpenAI API calls are made by this package.
- No PyTorch, CUDA, or local Whisper installation is required.
- FFmpeg is optional and must be installed separately for `render_video()`.
- SRT/VTT timing is approximate and should be treated as a fallback path.
- Use Whisper JSON with word timestamps whenever possible for best karaoke quality.
```

* `CHANGELOG.md`

```markdown
# Changelog

All notable changes to `karaoke_engine` are documented in this file.

## [0.1.0] - Unreleased

### Added

- Gate 1: package foundation with typed models, exceptions, ASS escaping, and timecode helpers.
- Gate 2: ASS karaoke writer with `KaraokeStyle` presets and `\kf` timing.
- Gate 3: Whisper `verbose_json` parser with word-level timestamps.
- Gate 4: configurable karaoke line segmenter.
- Gate 5: high-level `KaraokeEngine.create_ass()` API.
- Gate 6: optional FFmpeg/FFprobe video rendering via `KaraokeEngine.render_video()`.
- Gate 7: SRT and VTT fallback parsers with approximate word timing.
- Gate 8: production hardening, examples, README/CHANGELOG updates, and expanded validation.

### Notes

- Runtime dependencies remain empty; `pytest` is available via the `dev` extra.
- FFmpeg is an optional external system dependency for video rendering.
- SRT and VTT inputs use approximate per-word timing, not true karaoke timestamps.
```

## Example Files

* `examples/whisper_sample.json`

Three-word Whisper JSON sample (`Aku`, `cinta`, `padamu`) with real per-word timestamps from 0.0s to 1.55s.

* `examples/sample.srt`

Two short SRT cues demonstrating comma-millisecond timing and multi-line subtitle support.

* `examples/sample.vtt`

Two short WebVTT cues with `WEBVTT` header and dot-millisecond timing.

## Design Decisions

- **1 ms timing tolerance**: Small float-safe tolerance avoids rejecting valid parser output while still catching meaningful inconsistencies.
- **Overlaps as warnings**: Word overlaps beyond tolerance produce `ValidationWarning` entries so documents remain usable in report mode while surfacing timing quality issues.
- **Style validation in `__post_init__`**: Invalid `KaraokeStyle` values fail fast at construction time without changing public APIs.
- **Writer/render option validation via `ValueError`/`RenderError`**: Matches existing `RenderOptions` and keeps hard failures distinct from transcript validation.
- **Quoted ASS paths for FFmpeg**: Windows drive-letter paths are wrapped in single quotes in the `ass=` filter argument to improve real FFmpeg compatibility.
- **Optional smoke test**: Real FFmpeg smoke coverage is skipped automatically when binaries are unavailable; normal CI remains fully mocked.

## Risks / Questions

- **Overlap warnings do not block `ensure_valid_document()`**: Overlapping words are surfaced but do not fail hard validation; callers needing strict non-overlap must inspect `ValidationReport.warnings`.
- **ASS color validation is syntactic only**: Colors are validated by format, not by playback appearance across players/fonts.
- **Windows FFmpeg path behavior**: Quoted drive-letter escaping is improved but still depends on the installed FFmpeg build.
- **Examples are minimal**: They are intended for docs/tests, not as production lyric datasets.

## Gatekeeper Review Request

Please review Gate 8 and tell me whether it is APPROVED or BLOCKED.
