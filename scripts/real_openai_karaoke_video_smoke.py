#!/usr/bin/env python3
"""Manual real OpenAI + FFmpeg end-to-end karaoke smoke test.

This script is not part of normal pytest. It uses real OpenAI API credits and
requires OPENAI_API_KEY in the environment.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from karaoke_engine import KaraokeEngine, RenderOptions, SegmentOptions

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}

DEFAULT_OUTPUT_DIR = Path("real_api_smoke_output")
TRANSCRIPT_NAME = "openai_whisper_transcript.json"
ASS_NAME = "karaoke.ass"
RENDERED_NAME = "karaoke_output.mp4"
TEST_VIDEO_NAME = "test_video.mp4"


def _step_pass(step: str, message: str) -> None:
    print(f"PASS [{step}]: {message}")


def _step_fail(step: str, message: str) -> None:
    print(f"FAIL [{step}]: {message}", file=sys.stderr)
    sys.exit(1)


def _openai_key_help() -> str:
    if os.name == "nt":
        return (
            "OPENAI_API_KEY is not visible to this Python process.\n"
            "Set it in the SAME terminal session before running the script:\n"
            "  CMD:         set OPENAI_API_KEY=sk-your-key-here\n"
            "  PowerShell:  $env:OPENAI_API_KEY = \"sk-your-key-here\"\n"
            "Then verify in that same terminal:\n"
            "  python -c \"import os; print('ok' if os.environ.get('OPENAI_API_KEY') else 'missing')\"\n"
            "Note: `set VAR=...` in CMD does not work in PowerShell, and vice versa."
        )
    return (
        "OPENAI_API_KEY is not set. Export it in this shell before running:\n"
        "  export OPENAI_API_KEY=sk-your-key-here"
    )


def _require_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        _step_fail("env", _openai_key_help())

    try:
        from openai import OpenAI
    except ImportError:
        _step_fail(
            "deps",
            "openai package is required for this manual script only. "
            "Install with: pip install openai",
        )

    return OpenAI(api_key=api_key)


def _require_ffmpeg_tools(step: str) -> None:
    missing = [
        name
        for name in ("ffmpeg", "ffprobe")
        if shutil.which(name) is None
    ]
    if missing:
        _step_fail(
            step,
            f"required external tools not found on PATH: {', '.join(missing)}",
        )


def _is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def _response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
        if isinstance(payload, dict):
            return payload
    if isinstance(response, dict):
        return response
    raise TypeError("OpenAI transcription response is not a JSON object")


def _has_word_timestamps(data: dict[str, Any]) -> bool:
    words = data.get("words")
    if isinstance(words, list) and words:
        return all(
            isinstance(entry, dict)
            and "start" in entry
            and "end" in entry
            and ("word" in entry or "text" in entry)
            for entry in words
        )

    segments = data.get("segments")
    if not isinstance(segments, list):
        return False

    found_words = False
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_words = segment.get("words")
        if not isinstance(segment_words, list) or not segment_words:
            continue
        found_words = True
        if not all(
            isinstance(entry, dict)
            and "start" in entry
            and "end" in entry
            and ("word" in entry or "text" in entry)
            for entry in segment_words
        ):
            return False
    return found_words


def _probe_duration_seconds(media_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    completed = subprocess.run(
        command,
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        _step_fail("ffmpeg", f"ffprobe failed for {media_path}: {stderr}")

    try:
        duration = float((completed.stdout or "").strip())
    except ValueError:
        _step_fail("ffmpeg", f"ffprobe returned invalid duration for {media_path}")

    if duration <= 0:
        _step_fail("ffmpeg", f"ffprobe returned non-positive duration for {media_path}")
    return duration


def _make_test_video_from_audio(audio_path: Path, output_video: Path) -> Path:
    _require_ffmpeg_tools("ffmpeg")
    duration = _probe_duration_seconds(audio_path)
    output_video.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1920x1080",
        "-i",
        str(audio_path),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(output_video),
    ]
    completed = subprocess.run(
        command,
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        _step_fail("ffmpeg", f"failed to create test video: {stderr}")
    if not output_video.is_file():
        _step_fail("ffmpeg", f"test video was not created: {output_video}")

    _step_pass("ffmpeg", f"created test video at {output_video}")
    return output_video


def _verify_ass_file(ass_path: Path) -> None:
    if not ass_path.is_file():
        _step_fail("ass", f"ASS file was not created: {ass_path}")

    content = ass_path.read_text(encoding="utf-8")
    required = ("[Script Info]", "[V4+ Styles]", "[Events]", r"\kf")
    for marker in required:
        if marker not in content:
            _step_fail("ass", f"ASS output missing required marker: {marker}")

    _step_pass("ass", f"verified karaoke ASS at {ass_path}")


def _transcribe_media(client: Any, media_path: Path) -> dict[str, Any]:
    try:
        with media_path.open("rb") as media_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=media_file,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
    except Exception as exc:
        _step_fail("openai", f"transcription request failed: {exc}")

    try:
        payload = _response_to_dict(response)
    except TypeError as exc:
        _step_fail("openai", str(exc))

    if not _has_word_timestamps(payload):
        _step_fail(
            "openai",
            "transcription response is missing word-level timestamps",
        )

    _step_pass("openai", "received verbose_json transcription with word timestamps")
    return payload


def _resolve_render_video(
    *,
    input_media: Path,
    output_dir: Path,
    explicit_video: Path | None,
    make_test_video: bool,
) -> Path | None:
    if explicit_video is not None:
        if not explicit_video.is_file():
            _step_fail("input", f"video file does not exist: {explicit_video}")
        if not _is_video(explicit_video):
            _step_fail("input", f"--video must point to a video file: {explicit_video}")
        return explicit_video

    if _is_video(input_media):
        return input_media

    if not _is_audio(input_media):
        _step_fail(
            "input",
            f"unsupported input media type: {input_media.suffix!r}",
        )

    if make_test_video:
        return _make_test_video_from_audio(
            input_media,
            output_dir / TEST_VIDEO_NAME,
        )

    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Manual real OpenAI + FFmpeg karaoke smoke test. "
            "Uses OPENAI_API_KEY from the environment."
        ),
    )
    parser.add_argument(
        "input_media",
        type=Path,
        help="Input audio or video file (.mp3, .wav, .m4a, .mp4, etc.)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=None,
        help="Explicit video file to use for subtitle burn-in",
    )
    parser.add_argument(
        "--make-test-video",
        action="store_true",
        help=(
            "For audio-only input, create a simple black test video with FFmpeg "
            "and burn subtitles into it"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_media = args.input_media.resolve()
    output_dir = args.output_dir.resolve()

    if not input_media.is_file():
        _step_fail("input", f"input media file does not exist: {input_media}")

    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / TRANSCRIPT_NAME
    ass_path = output_dir / ASS_NAME
    rendered_path = output_dir / RENDERED_NAME

    print("karaoke_engine real OpenAI karaoke video smoke test")
    print(f"input: {input_media}")
    print(f"output_dir: {output_dir}")
    print()

    client = _require_openai_client()
    transcript = _transcribe_media(client, input_media)

    transcript_path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _step_pass("save", f"saved transcript to {transcript_path}")

    engine = KaraokeEngine()
    segment_options = SegmentOptions(max_words_per_line=5)

    try:
        ass_result = engine.create_ass(
            transcript_path=transcript_path,
            output_path=ass_path,
            segment_options=segment_options,
        )
    except Exception as exc:
        _step_fail("karaoke", f"create_ass failed: {exc}")

    if ass_result.source_format != "whisper_json":
        _step_fail(
            "karaoke",
            f"unexpected source_format: {ass_result.source_format!r}",
        )

    _verify_ass_file(ass_path)
    _step_pass(
        "karaoke",
        (
            f"created ASS with {ass_result.line_count} lines and "
            f"{ass_result.word_count} words"
        ),
    )

    render_video_path = _resolve_render_video(
        input_media=input_media,
        output_dir=output_dir,
        explicit_video=args.video.resolve() if args.video else None,
        make_test_video=args.make_test_video,
    )

    if render_video_path is None:
        print()
        print("SKIP [render]: audio-only input; video render not requested")
        print("OVERALL: PASS (ASS workflow complete)")
        return 0

    _require_ffmpeg_tools("ffmpeg")

    try:
        render_result = engine.render_video(
            video_path=render_video_path,
            transcript_path=transcript_path,
            output_path=rendered_path,
            ass_output_path=ass_path,
            segment_options=segment_options,
            render_options=RenderOptions(crf=23, preset="veryfast"),
        )
    except Exception as exc:
        _step_fail("render", f"render_video failed: {exc}")

    if not render_result.output_path.is_file():
        _step_fail("render", f"rendered video was not created: {rendered_path}")

    _verify_ass_file(render_result.ass_path)
    _step_pass("render", f"created karaoke video at {render_result.output_path}")

    print()
    print("OVERALL: PASS")
    print(f"transcript: {transcript_path}")
    print(f"ass: {ass_path}")
    print(f"video: {render_result.output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
