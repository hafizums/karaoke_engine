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
