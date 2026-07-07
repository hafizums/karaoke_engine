"""End-to-end example workflow tests using bundled sample files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from karaoke_engine import KaraokeEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"


@pytest.fixture
def engine() -> KaraokeEngine:
    return KaraokeEngine()


def test_whisper_json_example_workflow(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = EXAMPLES_DIR / "whisper_sample.json"
    output_ass = tmp_path / "whisper_sample.ass"

    result = engine.create_ass(
        transcript_path=transcript,
        output_path=output_ass,
    )

    assert output_ass.is_file()
    content = output_ass.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert r"\kf" in content
    assert result.source_format == "whisper_json"
    assert result.line_count > 0
    assert result.word_count > 0


def test_srt_example_workflow(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = EXAMPLES_DIR / "sample.srt"
    output_ass = tmp_path / "sample.ass"

    result = engine.create_ass(
        transcript_path=transcript,
        output_path=output_ass,
    )

    assert output_ass.is_file()
    assert result.source_format == "srt_approx"


def test_vtt_example_workflow(engine: KaraokeEngine, tmp_path: Path) -> None:
    transcript = EXAMPLES_DIR / "sample.vtt"
    output_ass = tmp_path / "sample.ass"

    result = engine.create_ass(
        transcript_path=transcript,
        output_path=output_ass,
    )

    assert output_ass.is_file()
    assert result.source_format == "vtt_approx"


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not available",
)
def test_optional_ffmpeg_render_workflow(engine: KaraokeEngine, tmp_path: Path) -> None:
    video_path = tmp_path / "tiny.mp4"
    output_path = tmp_path / "tiny_out.mp4"
    transcript = EXAMPLES_DIR / "whisper_sample.json"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:d=1",
            "-c:v",
            "libx264",
            "-t",
            "1",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = engine.render_video(
        video_path=video_path,
        transcript_path=transcript,
        output_path=output_path,
        play_res_x=160,
        play_res_y=90,
        auto_probe_resolution=False,
    )

    assert output_path.is_file()
    assert result.ass_path.is_file()
    assert result.source_format == "whisper_json"
