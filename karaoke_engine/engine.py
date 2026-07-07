"""High-level karaoke engine API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from karaoke_engine.ass.styles import KaraokeStyle
from karaoke_engine.ass.writer import AssWriter
from karaoke_engine.errors import AssGenerationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument
from karaoke_engine.parsers.whisper_json import load_whisper_json
from karaoke_engine.segmenter import SegmentOptions, segment_document

_SUPPORTED_TRANSCRIPT_SUFFIXES = {".json"}


@dataclass(frozen=True, slots=True)
class CreateAssResult:
    """Metadata returned after creating a karaoke ASS file."""

    ass_path: Path
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
