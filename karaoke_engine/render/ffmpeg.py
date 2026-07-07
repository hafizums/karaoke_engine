"""FFmpeg ASS burn-in rendering."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from karaoke_engine.errors import RenderError

_FFMPEG_BINARY = "ffmpeg"


@dataclass(frozen=True, slots=True)
class RenderOptions:
    """FFmpeg encoding options for ASS burn-in rendering."""

    crf: int = 18
    preset: str = "veryfast"
    video_codec: str = "libx264"
    audio_codec: str = "copy"
    timeout_seconds: float = 1800.0
    overwrite: bool = True

    def __post_init__(self) -> None:
        if not 0 <= self.crf <= 51:
            raise ValueError("crf must be between 0 and 51")
        if not self.preset:
            raise ValueError("preset must be non-empty")
        if not self.video_codec:
            raise ValueError("video_codec must be non-empty")
        if not self.audio_codec:
            raise ValueError("audio_codec must be non-empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")


@dataclass(frozen=True, slots=True)
class RenderVideoResult:
    """Metadata returned after rendering ASS subtitles into a video."""

    video_path: Path
    ass_path: Path
    output_path: Path
    return_code: int
    stderr: str


def build_ffmpeg_ass_burn_command(
    *,
    video_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    options: RenderOptions | None = None,
) -> list[str]:
    """Build an FFmpeg command list for ASS subtitle burn-in."""
    if not str(video_path).strip():
        raise RenderError("video_path must be non-empty")
    if not str(ass_path).strip():
        raise RenderError("ass_path must be non-empty")
    if not str(output_path).strip():
        raise RenderError("output_path must be non-empty")

    render_options = options or RenderOptions()
    escaped_ass_path = _escape_ass_filter_path(Path(ass_path))
    command = [
        _FFMPEG_BINARY,
        "-y" if render_options.overwrite else "-n",
        "-i",
        str(video_path),
        "-vf",
        f"ass={escaped_ass_path}",
        "-c:v",
        render_options.video_codec,
        "-crf",
        str(render_options.crf),
        "-preset",
        render_options.preset,
        "-c:a",
        render_options.audio_codec,
        str(output_path),
    ]
    return command


def render_ass_to_video(
    *,
    video_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    options: RenderOptions | None = None,
) -> RenderVideoResult:
    """Burn ASS subtitles into a video using FFmpeg."""
    render_options = options or RenderOptions()
    source_video = Path(video_path)
    subtitle_file = Path(ass_path)
    rendered_output = Path(output_path)

    if not source_video.is_file():
        raise RenderError(f"Input video file does not exist: {source_video}")
    if not subtitle_file.is_file():
        raise RenderError(f"ASS subtitle file does not exist: {subtitle_file}")
    if rendered_output.exists() and rendered_output.is_dir():
        raise RenderError(f"Output path is an existing directory: {rendered_output}")

    rendered_output.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_ass_burn_command(
        video_path=source_video,
        ass_path=subtitle_file,
        output_path=rendered_output,
        options=render_options,
    )

    try:
        completed = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=render_options.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            f"FFmpeg render timed out after {render_options.timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise RenderError(f"Failed to execute FFmpeg: {exc}") from exc

    stderr = completed.stderr or ""
    if completed.returncode != 0:
        raise RenderError(
            f"FFmpeg render failed with exit code {completed.returncode}: {stderr.strip()}"
        )
    if not rendered_output.is_file():
        raise RenderError(
            f"FFmpeg reported success but output file was not created: {rendered_output}"
        )

    return RenderVideoResult(
        video_path=source_video,
        ass_path=subtitle_file,
        output_path=rendered_output,
        return_code=completed.returncode,
        stderr=stderr,
    )


def _escape_ass_filter_path(path: Path) -> str:
    """Return an FFmpeg ``ass`` filter-safe path string."""
    posix_path = path.resolve().as_posix()
    if len(posix_path) >= 2 and posix_path[1] == ":":
        inner = f"{posix_path[0]}\\:{posix_path[2:]}"
    else:
        inner = posix_path
    inner = inner.replace("'", "\\'")
    return f"'{inner}'"
