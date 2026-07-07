import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from karaoke_engine.errors import RenderError
from karaoke_engine.render.probe import VideoInfo, build_ffprobe_command, probe_video


def test_build_ffprobe_command_uses_list_args() -> None:
    command = build_ffprobe_command("input.mp4")
    assert isinstance(command, list)
    assert command[0] == "ffprobe"
    assert "input.mp4" in command


def test_probe_video_parses_width_height_and_duration(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    video.write_text("video", encoding="utf-8")

    payload = {
        "streams": [{"width": 1280, "height": 720}],
        "format": {"duration": "12.5"},
    }
    completed = MagicMock(returncode=0, stderr="", stdout=json.dumps(payload))
    with patch(
        "karaoke_engine.render.probe.subprocess.run",
        return_value=completed,
    ) as run_mock:
        info = probe_video(video)

    assert isinstance(info, VideoInfo)
    assert info.width == 1280
    assert info.height == 720
    assert info.duration_seconds == 12.5
    assert run_mock.call_args.kwargs["shell"] is False


def test_probe_video_failure_raises_clear_error(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    video.write_text("video", encoding="utf-8")

    completed = MagicMock(returncode=1, stderr="probe failed", stdout="")
    with patch(
        "karaoke_engine.render.probe.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(RenderError, match="FFprobe failed"):
            probe_video(video)


def test_probe_video_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(RenderError, match="Input video file does not exist"):
        probe_video(tmp_path / "missing.mp4")
