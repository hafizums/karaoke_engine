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
