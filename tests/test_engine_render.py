import json
from pathlib import Path
from unittest.mock import patch

import pytest

import karaoke_engine
from karaoke_engine import KaraokeEngine, RenderOptions
from karaoke_engine.engine import RenderKaraokeVideoResult


ROOT_WORDS_PAYLOAD = {
    "text": "Aku cinta padamu",
    "words": [
        {"word": "Aku", "start": 0.0, "end": 0.4},
        {"word": "cinta", "start": 0.4, "end": 0.75},
        {"word": "padamu", "start": 0.75, "end": 1.55},
    ],
}


@pytest.fixture
def transcript_path(tmp_path: Path) -> Path:
    path = tmp_path / "transcript.json"
    path.write_text(json.dumps(ROOT_WORDS_PAYLOAD), encoding="utf-8")
    return path


@pytest.fixture
def video_path(tmp_path: Path) -> Path:
    path = tmp_path / "input.mp4"
    path.write_text("video", encoding="utf-8")
    return path


@pytest.fixture
def engine() -> KaraokeEngine:
    return KaraokeEngine()


def test_render_video_creates_ass_sidecar_when_omitted(
    engine: KaraokeEngine,
    video_path: Path,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "karaoke_output.mp4"
    ass_path = output_path.with_suffix(".ass")

    with (
        patch(
            "karaoke_engine.engine.probe_video",
            return_value=karaoke_engine.VideoInfo(width=1920, height=1080),
        ),
        patch(
            "karaoke_engine.engine.render_ass_to_video",
            return_value=karaoke_engine.RenderVideoResult(
                video_path=video_path,
                ass_path=ass_path,
                output_path=output_path,
                return_code=0,
                stderr="",
            ),
        ),
    ):
        result = engine.render_video(
            video_path=video_path,
            transcript_path=transcript_path,
            output_path=output_path,
            auto_probe_resolution=False,
            play_res_x=1920,
            play_res_y=1080,
        )

    assert result.ass_path == ass_path
    assert ass_path.exists()


def test_render_video_uses_explicit_play_resolution(
    engine: KaraokeEngine,
    video_path: Path,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "karaoke_output.mp4"

    with (
        patch("karaoke_engine.engine.probe_video") as probe_mock,
        patch(
            "karaoke_engine.engine.render_ass_to_video",
            return_value=karaoke_engine.RenderVideoResult(
                video_path=video_path,
                ass_path=output_path.with_suffix(".ass"),
                output_path=output_path,
                return_code=0,
                stderr="",
            ),
        ),
        patch.object(engine, "create_ass", wraps=engine.create_ass) as create_ass_mock,
    ):
        engine.render_video(
            video_path=video_path,
            transcript_path=transcript_path,
            output_path=output_path,
            play_res_x=1280,
            play_res_y=720,
            auto_probe_resolution=True,
        )

    probe_mock.assert_not_called()
    assert create_ass_mock.call_args.kwargs["play_res_x"] == 1280
    assert create_ass_mock.call_args.kwargs["play_res_y"] == 720


def test_render_video_auto_probes_resolution(
    engine: KaraokeEngine,
    video_path: Path,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "karaoke_output.mp4"

    with (
        patch(
            "karaoke_engine.engine.probe_video",
            return_value=karaoke_engine.VideoInfo(width=1080, height=1920, duration_seconds=10.0),
        ),
        patch(
            "karaoke_engine.engine.render_ass_to_video",
            return_value=karaoke_engine.RenderVideoResult(
                video_path=video_path,
                ass_path=output_path.with_suffix(".ass"),
                output_path=output_path,
                return_code=0,
                stderr="",
            ),
        ),
        patch.object(engine, "create_ass", wraps=engine.create_ass) as create_ass_mock,
    ):
        engine.render_video(
            video_path=video_path,
            transcript_path=transcript_path,
            output_path=output_path,
        )

    assert create_ass_mock.call_args.kwargs["play_res_x"] == 1080
    assert create_ass_mock.call_args.kwargs["play_res_y"] == 1920


def test_render_video_returns_structured_result(
    engine: KaraokeEngine,
    video_path: Path,
    transcript_path: Path,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "karaoke_output.mp4"
    ass_path = output_path.with_suffix(".ass")

    with (
        patch(
            "karaoke_engine.engine.probe_video",
            return_value=karaoke_engine.VideoInfo(width=1920, height=1080),
        ),
        patch(
            "karaoke_engine.engine.render_ass_to_video",
            return_value=karaoke_engine.RenderVideoResult(
                video_path=video_path,
                ass_path=ass_path,
                output_path=output_path,
                return_code=0,
                stderr="",
            ),
        ),
    ):
        result = engine.render_video(
            video_path=video_path,
            transcript_path=transcript_path,
            output_path=output_path,
            auto_probe_resolution=False,
            play_res_x=1920,
            play_res_y=1080,
        )

    assert isinstance(result, RenderKaraokeVideoResult)
    assert result.output_path == output_path
    assert result.line_count == 1
    assert result.word_count == 3
    assert result.source_format == "whisper_json"
    assert result.segmented is True


def test_public_exports_work() -> None:
    assert karaoke_engine.RenderOptions is not None
    assert karaoke_engine.RenderVideoResult is not None
    assert karaoke_engine.RenderKaraokeVideoResult is RenderKaraokeVideoResult
    assert karaoke_engine.VideoInfo is not None
    assert karaoke_engine.build_ffmpeg_ass_burn_command is not None
    assert karaoke_engine.render_ass_to_video is not None
    assert karaoke_engine.build_ffprobe_command is not None
    assert karaoke_engine.probe_video is not None
    assert karaoke_engine.RenderError is not None
    assert "RenderOptions" in karaoke_engine.__all__
    assert "render_ass_to_video" in karaoke_engine.__all__
