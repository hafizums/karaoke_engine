"""FFprobe video inspection helpers."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from karaoke_engine.errors import RenderError

_FFPROBE_BINARY = "ffprobe"


@dataclass(frozen=True, slots=True)
class VideoInfo:
    """Basic video stream metadata from FFprobe."""

    width: int
    height: int
    duration_seconds: float | None = None


def build_ffprobe_command(path: str | Path) -> list[str]:
    """Build an FFprobe command list for JSON stream metadata."""
    if not str(path).strip():
        raise RenderError("path must be non-empty")
    return [
        _FFPROBE_BINARY,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]


def probe_video(path: str | Path, timeout_seconds: float = 30.0) -> VideoInfo:
    """Probe a video file and return width, height, and optional duration."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be > 0")

    video_path = Path(path)
    if not video_path.is_file():
        raise RenderError(f"Input video file does not exist: {video_path}")

    command = build_ffprobe_command(video_path)
    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            f"FFprobe timed out after {timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise RenderError(f"Failed to execute FFprobe: {exc}") from exc

    stderr = completed.stderr or ""
    if completed.returncode != 0:
        raise RenderError(
            f"FFprobe failed with exit code {completed.returncode}: {stderr.strip()}"
        )

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RenderError("FFprobe returned invalid JSON output") from exc

    return _parse_ffprobe_json(payload)


def _parse_ffprobe_json(payload: dict[str, Any]) -> VideoInfo:
    streams = payload.get("streams")
    if not isinstance(streams, list) or not streams:
        raise RenderError("FFprobe JSON output is missing video stream data")

    stream = streams[0]
    if not isinstance(stream, dict):
        raise RenderError("FFprobe JSON stream entry must be an object")

    width = stream.get("width")
    height = stream.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        raise RenderError("FFprobe JSON output is missing width/height")

    duration_seconds = _parse_duration(payload)
    return VideoInfo(
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )


def _parse_duration(payload: dict[str, Any]) -> float | None:
    format_section = payload.get("format")
    if not isinstance(format_section, dict):
        return None

    duration_value = format_section.get("duration")
    if duration_value is None:
        return None

    try:
        return float(duration_value)
    except (TypeError, ValueError) as exc:
        raise RenderError(
            f"FFprobe returned invalid duration value: {duration_value!r}"
        ) from exc
