"""High-level karaoke engine API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.ass.writer import AssWriter
from karaoke_engine.errors import AssGenerationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument
from karaoke_engine.parsers.whisper_json import load_whisper_json
from karaoke_engine.render.ffmpeg import RenderOptions, render_ass_to_video
from karaoke_engine.render.probe import probe_video
from karaoke_engine.segmenter import SegmentOptions, segment_document

_SUPPORTED_TRANSCRIPT_SUFFIXES = {".json"}
_DEFAULT_PLAY_RES_X = 1920
_DEFAULT_PLAY_RES_Y = 1080


@dataclass(frozen=True, slots=True)
class CreateAssResult:
    """Metadata returned after creating a karaoke ASS file."""

    ass_path: Path
    line_count: int
    word_count: int
    source_format: str
    segmented: bool


@dataclass(frozen=True, slots=True)
class RenderKaraokeVideoResult:
    """Metadata returned after rendering a karaoke video."""

    video_path: Path
    ass_path: Path
    output_path: Path
    line_count: int
    word_count: int
    source_format: str
    segmented: bool


class KaraokeEngine:
    """Orchestrates Whisper JSON parsing, segmentation, and ASS generation."""

    def create_ass(
        self,
        *,
        transcript_path: str | Path,
        output_path: str | Path,
        style: KaraokeStyle | None = None,
        segment_options: SegmentOptions | None = None,
        segment: bool = True,
        play_res_x: int = 1920,
        play_res_y: int = 1080,
        title: str = "Karaoke",
    ) -> CreateAssResult:
        """Load Whisper JSON, optionally segment, and write a karaoke ASS file."""
        parsed = _load_transcript(Path(transcript_path))
        final_document = (
            segment_document(parsed, segment_options)
            if segment
            else parsed
        )

        ass_path = Path(output_path)
        _ensure_output_parent(ass_path)

        writer = AssWriter(
            style=style,
            play_res_x=play_res_x,
            play_res_y=play_res_y,
            title=title,
        )
        try:
            writer.write_to_file(final_document, ass_path)
        except OSError as exc:
            raise AssGenerationError(
                f"Failed to write ASS file to {ass_path}: {exc}"
            ) from exc

        return CreateAssResult(
            ass_path=ass_path,
            line_count=len(final_document.lines),
            word_count=_count_words(final_document),
            source_format=final_document.source_format,
            segmented=segment,
        )

    def render_video(
        self,
        *,
        video_path: str | Path,
        transcript_path: str | Path,
        output_path: str | Path,
        ass_output_path: str | Path | None = None,
        style: KaraokeStyle | None = None,
        segment_options: SegmentOptions | None = None,
        segment: bool = True,
        play_res_x: int | None = None,
        play_res_y: int | None = None,
        title: str = "Karaoke",
        render_options: RenderOptions | None = None,
        auto_probe_resolution: bool = True,
    ) -> RenderKaraokeVideoResult:
        """Create ASS subtitles and burn them into an output video with FFmpeg."""
        source_video = Path(video_path)
        rendered_output = Path(output_path)
        subtitle_output = (
            Path(ass_output_path)
            if ass_output_path is not None
            else rendered_output.with_suffix(".ass")
        )

        resolved_play_res_x, resolved_play_res_y = _resolve_play_resolution(
            source_video=source_video,
            play_res_x=play_res_x,
            play_res_y=play_res_y,
            auto_probe_resolution=auto_probe_resolution,
        )

        ass_result = self.create_ass(
            transcript_path=transcript_path,
            output_path=subtitle_output,
            style=style,
            segment_options=segment_options,
            segment=segment,
            play_res_x=resolved_play_res_x,
            play_res_y=resolved_play_res_y,
            title=title,
        )

        render_ass_to_video(
            video_path=source_video,
            ass_path=ass_result.ass_path,
            output_path=rendered_output,
            options=render_options,
        )

        return RenderKaraokeVideoResult(
            video_path=source_video,
            ass_path=ass_result.ass_path,
            output_path=rendered_output,
            line_count=ass_result.line_count,
            word_count=ass_result.word_count,
            source_format=ass_result.source_format,
            segmented=ass_result.segmented,
        )


def _load_transcript(path: Path) -> KaraokeDocument:
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_TRANSCRIPT_SUFFIXES:
        raise UnsupportedTranscriptFormatError(
            f"Unsupported transcript format {path.suffix!r}: only .json is supported"
        )
    return load_whisper_json(path)


def _count_words(document: KaraokeDocument) -> int:
    return sum(len(line.words) for line in document.lines)


def _ensure_output_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_play_resolution(
    *,
    source_video: Path,
    play_res_x: int | None,
    play_res_y: int | None,
    auto_probe_resolution: bool,
) -> tuple[int, int]:
    resolved_play_res_x = play_res_x
    resolved_play_res_y = play_res_y

    if auto_probe_resolution and (play_res_x is None or play_res_y is None):
        video_info = probe_video(source_video)
        if play_res_x is None:
            resolved_play_res_x = video_info.width
        if play_res_y is None:
            resolved_play_res_y = video_info.height

    if resolved_play_res_x is None:
        resolved_play_res_x = _DEFAULT_PLAY_RES_X
    if resolved_play_res_y is None:
        resolved_play_res_y = _DEFAULT_PLAY_RES_Y

    return resolved_play_res_x, resolved_play_res_y
