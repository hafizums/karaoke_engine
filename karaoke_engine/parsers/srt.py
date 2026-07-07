"""SRT subtitle parser with approximate word timing."""

from __future__ import annotations

import re
from pathlib import Path

from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine
from karaoke_engine.parsers.cue_utils import build_karaoke_line
from karaoke_engine.validators import ensure_valid_document

_SOURCE_FORMAT = "srt_approx"
_TIMING_LINE_PATTERN = re.compile(
    r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})$"
)


def parse_srt_text(text: str) -> KaraokeDocument:
    """Parse SRT subtitle text into a validated ``KaraokeDocument``."""
    blocks = _split_srt_blocks(text)
    lines: list[KaraokeLine] = []

    for block_index, block in enumerate(blocks):
        line = _parse_srt_block(block, block_index=block_index)
        if line is not None:
            lines.append(line)

    if not lines:
        raise TranscriptValidationError("SRT transcript is empty")

    document = KaraokeDocument(lines=tuple(lines), source_format=_SOURCE_FORMAT)
    ensure_valid_document(document)
    return document


def load_srt(path: str | Path) -> KaraokeDocument:
    """Load and parse an SRT subtitle file from disk."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Cannot read SRT file {file_path}: {exc}"
        ) from exc
    return parse_srt_text(text)


def _split_srt_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    return [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]


def _parse_srt_block(block: str, *, block_index: int) -> KaraokeLine | None:
    block_lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not block_lines:
        return None

    line_index = 0
    if block_lines[0].isdigit():
        line_index = 1

    if line_index >= len(block_lines):
        raise UnsupportedTranscriptFormatError(
            f"SRT block {block_index} is missing a timing line"
        )

    timing_line = block_lines[line_index]
    text_lines = block_lines[line_index + 1 :]
    if not text_lines:
        return None

    start, end = _parse_srt_timing_line(timing_line, block_index=block_index)
    cue_text = " ".join(text_lines)
    return build_karaoke_line(cue_text, start, end)


def _parse_srt_timing_line(timing_line: str, *, block_index: int) -> tuple[float, float]:
    match = _TIMING_LINE_PATTERN.match(timing_line.strip())
    if not match:
        raise UnsupportedTranscriptFormatError(
            f"Malformed SRT timing line in block {block_index}: {timing_line!r}"
        )

    start = _srt_timestamp_to_seconds(match.group(1, 2, 3, 4))
    end = _srt_timestamp_to_seconds(match.group(5, 6, 7, 8))
    if end <= start:
        raise UnsupportedTranscriptFormatError(
            f"SRT cue end time must be greater than start time in block {block_index}"
        )
    return start, end


def _srt_timestamp_to_seconds(parts: tuple[str, str, str, str]) -> float:
    hours, minutes, seconds, milliseconds = (int(part) for part in parts)
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
