from pathlib import Path

import pytest

from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.ass.writer import AssWriter
from karaoke_engine.errors import AssGenerationError, TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word


def _sample_document() -> KaraokeDocument:
    return KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(
                    Word(text="Aku", start=0.0, end=0.4),
                    Word(text="cinta", start=0.4, end=0.75),
                    Word(text="padamu", start=0.75, end=1.55),
                ),
                start=0.0,
                end=1.55,
            ),
        ),
        source_format="test",
    )


def test_ass_header_exists() -> None:
    content = AssWriter().generate(_sample_document())
    assert "[Script Info]" in content
    assert "ScriptType: v4.00+" in content
    assert "WrapStyle: 2" in content
    assert "ScaledBorderAndShadow: yes" in content
    assert "PlayResX: 1920" in content
    assert "PlayResY: 1080" in content


def test_style_section_exists() -> None:
    content = AssWriter().generate(_sample_document())
    assert "[V4+ Styles]" in content
    assert "Format: Name, Fontname, Fontsize" in content
    assert "Style: Karaoke,Arial,72," in content


def test_events_section_exists() -> None:
    content = AssWriter().generate(_sample_document())
    assert "[Events]" in content
    assert "Format: Layer, Start, End, Style" in content
    assert content.count("Dialogue:") == 1


def test_dialogue_uses_kf_tags_and_centiseconds() -> None:
    content = AssWriter().generate(_sample_document())
    assert r"{\kf40}Aku {\kf35}cinta {\kf80}padamu" in content


def test_word_text_is_escaped() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(
                    Word(text=r"path\to", start=0.0, end=0.5),
                    Word(text="line\nbreak", start=0.5, end=1.0),
                ),
                start=0.0,
                end=1.0,
            ),
        )
    )
    content = AssWriter().generate(document)
    assert r"{\kf50}path\\to" in content
    assert r"{\kf50}line\Nbreak" in content


def test_raw_ass_override_tags_are_rejected() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text=r"{\kf99}hack", start=0.0, end=0.5),),
                start=0.0,
                end=0.5,
            ),
        )
    )
    with pytest.raises(TranscriptValidationError):
        AssWriter().generate(document)


def test_invalid_document_fails() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="bad", start=1.0, end=1.0),),
                start=0.0,
                end=1.0,
            ),
        )
    )
    with pytest.raises(TranscriptValidationError):
        AssWriter().generate(document)


def test_output_is_deterministic() -> None:
    document = _sample_document()
    writer = AssWriter()
    assert writer.generate(document) == writer.generate(document)


def test_write_to_file_creates_utf8_ass(tmp_path: Path) -> None:
    output_path = tmp_path / "karaoke.ass"
    AssWriter().write_to_file(_sample_document(), output_path)
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert "[Script Info]" in text
    assert text.endswith("\n")


def test_write_to_file_raises_ass_generation_error(tmp_path: Path) -> None:
    writer = AssWriter()
    with pytest.raises(AssGenerationError):
        writer.write_to_file(_sample_document(), tmp_path / "missing" / "karaoke.ass")


def test_minimum_word_duration_is_one_centisecond() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="hi", start=0.0, end=0.001),),
                start=0.0,
                end=0.001,
            ),
        )
    )
    content = AssWriter().generate(document)
    assert r"{\kf1}hi" in content


def test_custom_style_and_resolution() -> None:
    style = KaraokeStyle.default_720p()
    writer = AssWriter(style=style, play_res_x=1280, play_res_y=720)
    content = writer.generate(_sample_document())
    assert "PlayResX: 1280" in content
    assert "PlayResY: 720" in content
    assert "Style: Karaoke,Arial,48," in content
