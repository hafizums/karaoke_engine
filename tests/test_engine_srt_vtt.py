import json
from pathlib import Path

import pytest

from karaoke_engine import KaraokeEngine, SegmentOptions
from karaoke_engine.errors import UnsupportedTranscriptFormatError


ROOT_WORDS_PAYLOAD = {
    "text": "Aku cinta padamu",
    "words": [
        {"word": "Aku", "start": 0.0, "end": 0.4},
        {"word": "cinta", "start": 0.4, "end": 0.75},
        {"word": "padamu", "start": 0.75, "end": 1.55},
        {"word": "selamanya", "start": 1.55, "end": 2.0},
        {"word": "dan", "start": 2.0, "end": 2.2},
        {"word": "kamu", "start": 2.2, "end": 2.5},
    ],
}

SRT_PAYLOAD = """1
00:00:00,000 --> 00:00:02,000
Aku cinta padamu selamanya dan kamu
"""

VTT_PAYLOAD = """WEBVTT

00:00:00.000 --> 00:00:02.000
Aku cinta padamu selamanya dan kamu
"""


@pytest.fixture
def engine() -> KaraokeEngine:
    return KaraokeEngine()


def test_create_ass_supports_srt(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = tmp_path / "lyrics.srt"
    transcript.write_text(SRT_PAYLOAD, encoding="utf-8")
    output = tmp_path / "karaoke.ass"

    result = engine.create_ass(transcript_path=transcript, output_path=output)

    assert output.exists()
    assert result.source_format == "srt_approx"


def test_create_ass_supports_uppercase_srt(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = tmp_path / "lyrics.SRT"
    transcript.write_text(SRT_PAYLOAD, encoding="utf-8")
    output = tmp_path / "karaoke.ass"

    result = engine.create_ass(transcript_path=transcript, output_path=output)
    assert result.source_format == "srt_approx"


def test_create_ass_supports_vtt(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = tmp_path / "lyrics.vtt"
    transcript.write_text(VTT_PAYLOAD, encoding="utf-8")
    output = tmp_path / "karaoke.ass"

    result = engine.create_ass(transcript_path=transcript, output_path=output)

    assert output.exists()
    assert result.source_format == "vtt_approx"


def test_create_ass_supports_uppercase_vtt(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = tmp_path / "lyrics.VTT"
    transcript.write_text(VTT_PAYLOAD, encoding="utf-8")
    output = tmp_path / "karaoke.ass"

    result = engine.create_ass(transcript_path=transcript, output_path=output)
    assert result.source_format == "vtt_approx"


def test_segmentation_works_with_approximate_parser_output(
    engine: KaraokeEngine,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "lyrics.srt"
    transcript.write_text(SRT_PAYLOAD, encoding="utf-8")
    output = tmp_path / "karaoke.ass"

    result = engine.create_ass(
        transcript_path=transcript,
        output_path=output,
        segment_options=SegmentOptions(max_words_per_line=2, pause_break_seconds=100.0),
    )

    assert result.line_count == 3
    assert result.word_count == 6


def test_unsupported_extension_still_raises(
    engine: KaraokeEngine,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "lyrics.txt"
    transcript.write_text("hello", encoding="utf-8")
    with pytest.raises(UnsupportedTranscriptFormatError, match="supported formats"):
        engine.create_ass(
            transcript_path=transcript,
            output_path=tmp_path / "karaoke.ass",
        )


def test_whisper_json_behavior_still_passes(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.json"
    transcript.write_text(json.dumps(ROOT_WORDS_PAYLOAD), encoding="utf-8")
    output = tmp_path / "karaoke.ass"

    result = engine.create_ass(transcript_path=transcript, output_path=output)
    assert result.source_format == "whisper_json"
    assert result.word_count == 6
