from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from karaoke_engine.errors import RenderError
from karaoke_engine.render.ffmpeg import (
    RenderOptions,
    RenderVideoResult,
    build_ffmpeg_ass_burn_command,
    render_ass_to_video,
)


def test_render_options_validation() -> None:
    RenderOptions()

    with pytest.raises(ValueError, match="crf must be between"):
        RenderOptions(crf=52)

    with pytest.raises(ValueError, match="preset must be non-empty"):
        RenderOptions(preset="")

    with pytest.raises(ValueError, match="video_codec must be non-empty"):
        RenderOptions(video_codec="")

    with pytest.raises(ValueError, match="audio_codec must be non-empty"):
        RenderOptions(audio_codec="")

    with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
        RenderOptions(timeout_seconds=0)


def test_build_ffmpeg_command_uses_list_args() -> None:
    command = build_ffmpeg_ass_burn_command(
        video_path="input.mp4",
        ass_path="subs.ass",
        output_path="output.mp4",
    )
    assert isinstance(command, list)
    assert all(isinstance(part, str) for part in command)


def test_build_ffmpeg_command_includes_overwrite_flag() -> None:
    overwrite_command = build_ffmpeg_ass_burn_command(
        video_path="input.mp4",
        ass_path="subs.ass",
        output_path="output.mp4",
        options=RenderOptions(overwrite=True),
    )
    no_overwrite_command = build_ffmpeg_ass_burn_command(
        video_path="input.mp4",
        ass_path="subs.ass",
        output_path="output.mp4",
        options=RenderOptions(overwrite=False),
    )
    assert "-y" in overwrite_command
    assert "-n" in no_overwrite_command


def test_build_ffmpeg_command_includes_input_video_path() -> None:
    command = build_ffmpeg_ass_burn_command(
        video_path="input.mp4",
        ass_path="subs.ass",
        output_path="output.mp4",
    )
    assert command[command.index("-i") + 1] == "input.mp4"


def test_build_ffmpeg_command_includes_ass_filter() -> None:
    command = build_ffmpeg_ass_burn_command(
        video_path="input.mp4",
        ass_path="subs.ass",
        output_path="output.mp4",
    )
    filter_arg = command[command.index("-vf") + 1]
    assert filter_arg.startswith("ass=")
    assert "subs.ass" in filter_arg


def test_build_ffmpeg_command_includes_codec_crf_preset_and_audio() -> None:
    command = build_ffmpeg_ass_burn_command(
        video_path="input.mp4",
        ass_path="subs.ass",
        output_path="output.mp4",
        options=RenderOptions(crf=20, preset="fast", video_codec="libx264", audio_codec="aac"),
    )
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-crf") + 1] == "20"
    assert command[command.index("-preset") + 1] == "fast"
    assert command[command.index("-c:a") + 1] == "aac"


def test_render_ass_to_video_uses_shell_false(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output = tmp_path / "output.mp4"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")
    output.write_text("rendered", encoding="utf-8")

    completed = MagicMock(returncode=0, stderr="")
    with patch(
        "karaoke_engine.render.ffmpeg.subprocess.run",
        return_value=completed,
    ) as run_mock:
        render_ass_to_video(video_path=video, ass_path=ass, output_path=output)
        assert run_mock.call_args.kwargs["shell"] is False


def test_render_ass_to_video_missing_input_video_raises(tmp_path: Path) -> None:
    ass = tmp_path / "subs.ass"
    ass.write_text("ass", encoding="utf-8")
    with pytest.raises(RenderError, match="Input video file does not exist"):
        render_ass_to_video(
            video_path=tmp_path / "missing.mp4",
            ass_path=ass,
            output_path=tmp_path / "output.mp4",
        )


def test_render_ass_to_video_missing_ass_raises(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    video.write_text("video", encoding="utf-8")
    with pytest.raises(RenderError, match="ASS subtitle file does not exist"):
        render_ass_to_video(
            video_path=video,
            ass_path=tmp_path / "missing.ass",
            output_path=tmp_path / "output.mp4",
        )


def test_render_ass_to_video_creates_output_parent_directory(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output = tmp_path / "nested" / "dir" / "output.mp4"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")

    completed = MagicMock(returncode=0, stderr="")
    with patch(
        "karaoke_engine.render.ffmpeg.subprocess.run",
        return_value=completed,
    ):
        output.parent.mkdir(parents=True)
        output.write_text("rendered", encoding="utf-8")
        render_ass_to_video(video_path=video, ass_path=ass, output_path=output)

    assert output.parent.exists()


def test_render_ass_to_video_non_zero_exit_raises(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output = tmp_path / "output.mp4"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")

    completed = MagicMock(returncode=1, stderr="ffmpeg failed")
    with patch(
        "karaoke_engine.render.ffmpeg.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(RenderError, match="FFmpeg render failed"):
            render_ass_to_video(video_path=video, ass_path=ass, output_path=output)


def test_render_ass_to_video_timeout_raises(tmp_path: Path) -> None:
    import subprocess

    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output = tmp_path / "output.mp4"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")

    with patch(
        "karaoke_engine.render.ffmpeg.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["ffmpeg"], timeout=1),
    ):
        with pytest.raises(RenderError, match="timed out"):
            render_ass_to_video(
                video_path=video,
                ass_path=ass,
                output_path=output,
                options=RenderOptions(timeout_seconds=1),
            )


def test_render_ass_to_video_missing_output_after_success_raises(
    tmp_path: Path,
) -> None:
    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output = tmp_path / "output.mp4"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")

    completed = MagicMock(returncode=0, stderr="")
    with patch(
        "karaoke_engine.render.ffmpeg.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(RenderError, match="output file was not created"):
            render_ass_to_video(video_path=video, ass_path=ass, output_path=output)


def test_render_ass_to_video_success_returns_result(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output = tmp_path / "output.mp4"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")
    output.write_text("rendered", encoding="utf-8")

    completed = MagicMock(returncode=0, stderr="ok")
    with patch(
        "karaoke_engine.render.ffmpeg.subprocess.run",
        return_value=completed,
    ):
        result = render_ass_to_video(video_path=video, ass_path=ass, output_path=output)

    assert isinstance(result, RenderVideoResult)
    assert result.video_path == video
    assert result.ass_path == ass
    assert result.output_path == output
    assert result.return_code == 0
    assert result.stderr == "ok"
