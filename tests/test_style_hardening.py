import pytest

from karaoke_engine.ass.styles import KaraokeStyle


def test_valid_presets_are_valid() -> None:
    KaraokeStyle.default_1080p()
    KaraokeStyle.default_720p()
    KaraokeStyle.mobile_1080x1920()


def test_invalid_empty_style_name() -> None:
    with pytest.raises(ValueError, match="name must be non-empty"):
        KaraokeStyle(
            name="   ",
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
            margin_l=10,
            margin_r=10,
            margin_v=10,
            encoding=1,
        )


def test_invalid_font_size() -> None:
    with pytest.raises(ValueError, match="font_size must be > 0"):
        KaraokeStyle(
            name="Karaoke",
            font_name="Arial",
            font_size=0,
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
            margin_l=10,
            margin_r=10,
            margin_v=10,
            encoding=1,
        )


def test_invalid_color() -> None:
    with pytest.raises(ValueError, match="primary_color"):
        KaraokeStyle(
            name="Karaoke",
            font_name="Arial",
            font_size=48,
            primary_color="white",
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
            margin_l=10,
            margin_r=10,
            margin_v=10,
            encoding=1,
        )


def test_invalid_alignment() -> None:
    with pytest.raises(ValueError, match="alignment must be between 1 and 9"):
        KaraokeStyle(
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
            alignment=10,
            margin_l=10,
            margin_r=10,
            margin_v=10,
            encoding=1,
        )


def test_invalid_margins() -> None:
    with pytest.raises(ValueError, match="margin_l must be >= 0"):
        KaraokeStyle(
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
            margin_l=-1,
            margin_r=10,
            margin_v=10,
            encoding=1,
        )
