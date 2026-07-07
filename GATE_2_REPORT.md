# Gate 2 Report — ASS Writer

## Status

PASS

## Summary

Gate 2 adds a deterministic ASS karaoke subtitle writer that converts validated `KaraokeDocument` objects into complete `.ass` files. The implementation includes a typed `KaraokeStyle` dataclass with 1080p, 720p, and mobile portrait presets, an `AssWriter` that emits `[Script Info]`, `[V4+ Styles]`, and `[Events]` sections, `\kf` centisecond karaoke timing with a 1 cs minimum per word, and integration with Gate 1 validation and ASS text escaping.

## Files Created

- `karaoke_engine/ass/styles.py`
- `karaoke_engine/ass/writer.py`
- `tests/test_ass_style.py`
- `tests/test_ass_writer.py`
- `GATE_2_REPORT.md`

## Files Modified

- `karaoke_engine/ass/__init__.py`
- `karaoke_engine/__init__.py`

## Dependencies Added

None.

## Implemented Scope

Confirm each completed item:

* KaraokeStyle dataclass
* Style presets
* ASS writer
* ASS header generation
* ASS style generation
* ASS dialogue event generation
* Karaoke `\kf` timing
* ASS escaping integration
* Validation before writing
* Tests

## Explicitly Not Implemented

Confirm these were not implemented:

* Whisper parser
* Segmenter
* FFmpeg
* SRT parser
* VTT parser
* Web UI
* Frappe integration

## Test Result

```
python -m pytest -q
............................                                             [100%]
28 passed in 0.09s
```

## Important Code Snippets

Paste the full contents of:

* `karaoke_engine/ass/styles.py`

```python
"""ASS style definitions for karaoke subtitles."""

from __future__ import annotations

from dataclasses import dataclass


def _ass_bool(value: bool) -> int:
    return -1 if value else 0


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

* `karaoke_engine/ass/writer.py`

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

* `karaoke_engine/ass/__init__.py`

```python
"""ASS-related helpers."""

from karaoke_engine.ass.escape import escape_ass_text
from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.ass.writer import AssWriter

__all__ = ["AssWriter", "KaraokeStyle", "escape_ass_text"]
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
]

__version__ = "0.1.0"
```

## Example Output

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

- **Validation before generation**: `AssWriter.generate()` calls `ensure_valid_document()` so invalid transcripts raise `TranscriptValidationError` before any ASS output is produced.
- **Separate style and play resolution**: `KaraokeStyle` controls font/colour/margins while `AssWriter` controls `PlayResX`/`PlayResY`, allowing presets to be reused across resolutions when needed.
- **`\kf` fill karaoke**: Word durations use ASS `\kf` tags in centiseconds, clamped to a minimum of 1 cs for player compatibility.
- **Deterministic output**: Fixed section order, stable document iteration, `\n` line endings, and a trailing newline make repeated generation identical.
- **Layered safety**: Gate 1 validation blocks raw `{...}` override tags in source text; `escape_ass_text()` escapes backslashes, braces, and newlines in emitted dialogue text.
- **Error split**: `TranscriptValidationError` for invalid documents; `AssGenerationError` for filesystem failures during `write_to_file()`.
- **Public API surface**: `AssWriter`, `KaraokeStyle`, and `escape_ass_text` are exported from both `karaoke_engine.ass` and the package root.

## Risks / Questions

- **Line vs word timing**: Dialogue event start/end use line-level timestamps only; word timings inside `\kf` tags are not cross-checked against line bounds.
- **PlayRes coupling**: Style presets do not embed resolution; callers must pair `default_720p()` with `play_res_x=1280, play_res_y=720` manually.
- **Single style only**: Gate 2 emits one karaoke style and one dialogue layer; multi-style or actor-name layouts are out of scope.
- **Font availability**: Presets assume `Arial`; players without that font will substitute silently.
- **Very short words**: Sub-10 ms words are clamped to 1 cs, which may visually compress fast syllables.

## Gatekeeper Review Request

Please review Gate 2 and tell me whether it is APPROVED or BLOCKED.
