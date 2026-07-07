import importlib
import shutil
import subprocess
from pathlib import Path

import pytest

import karaoke_engine
from karaoke_engine import KaraokeEngine
from karaoke_engine.ass.writer import AssWriter
from karaoke_engine.errors import RenderError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.parsers import load_srt, load_vtt, load_whisper_json
from karaoke_engine.render.ffmpeg import build_ffmpeg_ass_burn_command, render_ass_to_video
from karaoke_engine.render.probe import build_ffprobe_command


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def test_ass_writer_rejects_invalid_play_resolution() -> None:
    with pytest.raises(ValueError, match="play_res_x must be > 0"):
        AssWriter(play_res_x=0)


def test_ass_writer_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="title must be non-empty"):
        AssWriter(title="   ")


def test_ffmpeg_command_builder_rejects_empty_paths() -> None:
    with pytest.raises(RenderError, match="video_path must be non-empty"):
        build_ffmpeg_ass_burn_command(
            video_path="",
            ass_path="subs.ass",
            output_path="out.mp4",
        )


def test_ffprobe_command_builder_rejects_empty_path() -> None:
    with pytest.raises(RenderError, match="path must be non-empty"):
        build_ffprobe_command("")


def test_render_rejects_output_directory(tmp_path: Path) -> None:
    video = tmp_path / "input.mp4"
    ass = tmp_path / "subs.ass"
    output_dir = tmp_path / "output_dir"
    video.write_text("video", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")
    output_dir.mkdir()

    with pytest.raises(RenderError, match="existing directory"):
        render_ass_to_video(
            video_path=video,
            ass_path=ass,
            output_path=output_dir,
        )


def test_examples_can_be_parsed() -> None:
    whisper_doc = load_whisper_json(EXAMPLES_DIR / "whisper_sample.json")
    srt_doc = load_srt(EXAMPLES_DIR / "sample.srt")
    vtt_doc = load_vtt(EXAMPLES_DIR / "sample.vtt")

    assert whisper_doc.source_format == "whisper_json"
    assert srt_doc.source_format == "srt_approx"
    assert vtt_doc.source_format == "vtt_approx"


def test_readme_usage_imports_work() -> None:
    assert KaraokeEngine is not None
    assert "create_ass" in dir(KaraokeEngine)
    assert "render_video" in dir(KaraokeEngine)


def test_public_exports_still_work() -> None:
    assert karaoke_engine.KaraokeEngine is KaraokeEngine
    assert "KaraokeEngine" in karaoke_engine.__all__
    assert "RenderOptions" in karaoke_engine.__all__


def test_package_imports_cleanly() -> None:
    importlib.reload(karaoke_engine)


def test_no_heavy_runtime_dependencies() -> None:
    metadata_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    content = metadata_path.read_text(encoding="utf-8")
    assert "torch" not in content
    assert 'dependencies = []' in content


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not available",
)
def test_optional_ffmpeg_smoke(tmp_path: Path) -> None:
    video_name = "tiny.mp4"
    ass_name = "tiny.ass"
    output_name = "tiny_out.mp4"

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
            video_name,
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="hi", start=0.0, end=0.5),),
                start=0.0,
                end=0.5,
            ),
        ),
        source_format="whisper_json",
    )
    AssWriter(play_res_x=160, play_res_y=90).write_to_file(
        document,
        tmp_path / ass_name,
    )

    result = render_ass_to_video(
        video_path=tmp_path / video_name,
        ass_path=tmp_path / ass_name,
        output_path=tmp_path / output_name,
    )
    assert result.output_path.exists()
