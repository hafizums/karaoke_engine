from karaoke_engine.ass.styles import KaraokeStyle


def test_default_1080p_preset_values() -> None:
    style = KaraokeStyle.default_1080p()
    assert style.name == "Karaoke"
    assert style.font_name == "Arial"
    assert style.font_size == 72
    assert style.alignment == 2
    assert style.margin_v == 60
    assert style.encoding == 1


def test_default_720p_preset_values() -> None:
    style = KaraokeStyle.default_720p()
    assert style.font_size == 48
    assert style.outline == 2
    assert style.margin_l == 30
    assert style.margin_r == 30
    assert style.margin_v == 40


def test_mobile_1080x1920_preset_values() -> None:
    style = KaraokeStyle.mobile_1080x1920()
    assert style.font_size == 64
    assert style.margin_v == 140
    assert style.margin_l == 50
    assert style.margin_r == 50


def test_to_ass_style_line_contains_core_fields() -> None:
    style = KaraokeStyle.default_1080p()
    line = style.to_ass_style_line()
    assert line.startswith("Style: Karaoke,Arial,72,")
    assert line.endswith(",40,40,60,1")
