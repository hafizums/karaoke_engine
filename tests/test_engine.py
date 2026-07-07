import json
from pathlib import Path

import pytest

import karaoke_engine
from karaoke_engine import KaraokeEngine, KaraokeStyle, SegmentOptions
from karaoke_engine.errors import (
    AssGenerationError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)


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


@pytest.fixture
def transcript_path(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.json"
    path.write_text(json.dumps(ROOT_WORDS_PAYLOAD), encoding="utf-8")
    return path


@pytest.fixture
def engine() -> KaraokeEngine:
    return KaraokeEngine()


def test_create_ass_creates_ass_file(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "karaoke.ass"
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=output_path,
    )

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "Dialogue:" in content
    assert result.ass_path == output_path


def test_result_contains_correct_ass_path(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "out" / "karaoke.ass"
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=output_path,
    )
    assert result.ass_path == output_path.resolve() or result.ass_path == output_path


def test_result_contains_correct_line_count(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "karaoke.ass",
        segment_options=SegmentOptions(max_words_per_line=2, pause_break_seconds=100.0),
    )
    assert result.line_count == 3


def test_result_contains_correct_word_count(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "karaoke.ass",
    )
    assert result.word_count == 6


def test_result_source_format_is_preserved(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "karaoke.ass",
    )
    assert result.source_format == "whisper_json"


def test_segmentation_is_enabled_by_default(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "karaoke.ass",
        segment_options=SegmentOptions(max_words_per_line=2, pause_break_seconds=100.0),
    )
    assert result.segmented is True
    assert result.line_count == 3


def test_segment_false_writes_unsegmented_document(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "karaoke.ass",
        segment=False,
    )
    assert result.segmented is False
    assert result.line_count == 1
    assert result.word_count == 6


def test_custom_segment_options_affects_line_count(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    result_default = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "default.ass",
        segment_options=SegmentOptions(max_words_per_line=6, pause_break_seconds=100.0),
    )
    result_split = engine.create_ass(
        transcript_path=transcript_path,
        output_path=tmp_path / "split.ass",
        segment_options=SegmentOptions(max_words_per_line=2, pause_break_seconds=100.0),
    )
    assert result_default.line_count == 1
    assert result_split.line_count == 3


def test_custom_karaoke_style_is_used(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    style = KaraokeStyle.default_720p()
    output_path = tmp_path / "karaoke.ass"
    engine.create_ass(
        transcript_path=transcript_path,
        output_path=output_path,
        style=style,
    )
    content = output_path.read_text(encoding="utf-8")
    assert "Style: Karaoke,Arial,48," in content


def test_custom_play_resolution_is_used(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "karaoke.ass"
    engine.create_ass(
        transcript_path=transcript_path,
        output_path=output_path,
        play_res_x=1280,
        play_res_y=720,
    )
    content = output_path.read_text(encoding="utf-8")
    assert "PlayResX: 1280" in content
    assert "PlayResY: 720" in content


def test_parent_output_directory_is_created(
    engine: KaraokeEngine,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "nested" / "dir" / "karaoke.ass"
    result = engine.create_ass(
        transcript_path=transcript_path,
        output_path=output_path,
    )
    assert output_path.exists()
    assert result.ass_path == output_path


def test_unsupported_extension_raises(
    engine: KaraokeEngine,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("not json", encoding="utf-8")
    with pytest.raises(UnsupportedTranscriptFormatError, match="only .json is supported"):
        engine.create_ass(
            transcript_path=transcript,
            output_path=tmp_path / "karaoke.ass",
        )


def test_malformed_json_raises(
    engine: KaraokeEngine,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "broken.json"
    transcript.write_text("{not json", encoding="utf-8")
    with pytest.raises(UnsupportedTranscriptFormatError, match="Malformed JSON"):
        engine.create_ass(
            transcript_path=transcript,
            output_path=tmp_path / "karaoke.ass",
        )


def test_invalid_transcript_raises_validation_error(
    engine: KaraokeEngine,
    tmp_path: Path,
) -> None:
    transcript = tmp_path / "invalid.json"
    transcript.write_text(
        json.dumps(
            {
                "words": [
                    {"word": "bad", "start": 1.0, "end": 1.0},
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(TranscriptValidationError):
        engine.create_ass(
            transcript_path=transcript,
            output_path=tmp_path / "karaoke.ass",
        )


def test_no_ffmpeg_or_render_video_behavior() -> None:
    root_names = set(dir(karaoke_engine))
    assert "render_video" not in root_names
    assert "FFmpeg" not in root_names
    engine_names = set(dir(KaraokeEngine))
    assert "render_video" not in engine_names


def test_public_exports_work() -> None:
    assert karaoke_engine.KaraokeEngine is KaraokeEngine
    assert karaoke_engine.CreateAssResult is not None
    assert "KaraokeEngine" in karaoke_engine.__all__
    assert "CreateAssResult" in karaoke_engine.__all__
