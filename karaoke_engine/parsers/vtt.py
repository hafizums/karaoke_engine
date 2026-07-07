"""WebVTT subtitle parser with approximate word timing."""

from __future__ import annotations

import re
from pathlib import Path

from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine
from karaoke_engine.parsers.cue_utils import build_karaoke_line
from karaoke_engine.validators import ensure_valid_document

_SOURCE_FORMAT = "vtt_approx"
_TIMING_LINE_PATTERN = re.compile(
    r"^(.+?)\s*-->\s*(.+?)(?:\s+.*)?$"
)
_FULL_TIMESTAMP_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")
_SHORT_TIMESTAMP_PATTERN = re.compile(r"^(\d{2}):(\d{2})\.(\d{3})$")


def parse_vtt_text(text: str) -> KaraokeDocument:
    """Parse WebVTT subtitle text into a validated ``KaraokeDocument``."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.lstrip("\ufeff").startswith("WEBVTT"):
        raise UnsupportedTranscriptFormatError("VTT file must begin with WEBVTT")

    lines = normalized.split("\n")
    cue_blocks = _extract_vtt_cue_blocks(lines)
    karaoke_lines: list[KaraokeLine] = []

    for block_index, block in enumerate(cue_blocks):
        line = _parse_vtt_block(block, block_index=block_index)
        if line is not None:
            karaoke_lines.append(line)

    if not karaoke_lines:
        raise TranscriptValidationError("VTT transcript is empty")

    document = KaraokeDocument(lines=tuple(karaoke_lines), source_format=_SOURCE_FORMAT)
    ensure_valid_document(document)
    return document


def load_vtt(path: str | Path) -> KaraokeDocument:
    """Load and parse a WebVTT subtitle file from disk."""
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Cannot read VTT file {file_path}: {exc}"
        ) from exc
    return parse_vtt_text(text)


def _extract_vtt_cue_blocks(lines: list[str]) -> list[list[str]]:
    index = 0
    if index < len(lines) and lines[index].strip().lstrip("\ufeff").startswith("WEBVTT"):
        index += 1

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            break
        if "-->" in line:
            break
        index += 1

    blocks: list[list[str]] = []
    current_block: list[str] = []
    in_note_block = False

    while index < len(lines):
        line = lines[index].strip()
        index += 1

        if line.upper().startswith("NOTE"):
            if current_block:
                blocks.append(current_block)
                current_block = []
            in_note_block = True
            continue

        if in_note_block:
            if not line:
                in_note_block = False
            continue

        if not line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue

        current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return blocks


def _parse_vtt_block(block: list[str], *, block_index: int) -> KaraokeLine | None:
    if not block:
        return None

    timing_index = _find_timing_line_index(block)
    if timing_index is None:
        raise UnsupportedTranscriptFormatError(
            f"VTT block {block_index} is missing a timing line"
        )

    timing_line = block[timing_index]
    text_lines = block[timing_index + 1 :]
    if not text_lines:
        return None

    start, end = _parse_vtt_timing_line(timing_line, block_index=block_index)
    cue_text = " ".join(text_lines)
    return build_karaoke_line(cue_text, start, end)


def _find_timing_line_index(block: list[str]) -> int | None:
    for index, line in enumerate(block):
        if "-->" in line:
            return index
    return None


def _parse_vtt_timing_line(timing_line: str, *, block_index: int) -> tuple[float, float]:
    match = _TIMING_LINE_PATTERN.match(timing_line.strip())
    if not match:
        raise UnsupportedTranscriptFormatError(
            f"Malformed VTT timing line in block {block_index}: {timing_line!r}"
        )

    start = _parse_vtt_timestamp(match.group(1).strip(), block_index=block_index)
    end = _parse_vtt_timestamp(match.group(2).strip(), block_index=block_index)
    if end <= start:
        raise UnsupportedTranscriptFormatError(
            f"VTT cue end time must be greater than start time in block {block_index}"
        )
    return start, end


def _parse_vtt_timestamp(timestamp: str, *, block_index: int) -> float:
    full_match = _FULL_TIMESTAMP_PATTERN.match(timestamp)
    if full_match:
        hours, minutes, seconds, milliseconds = (int(part) for part in full_match.groups())
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

    short_match = _SHORT_TIMESTAMP_PATTERN.match(timestamp)
    if short_match:
        minutes, seconds, milliseconds = (int(part) for part in short_match.groups())
        return minutes * 60 + seconds + milliseconds / 1000.0

    raise UnsupportedTranscriptFormatError(
        f"Malformed VTT timestamp in block {block_index}: {timestamp!r}"
    )
