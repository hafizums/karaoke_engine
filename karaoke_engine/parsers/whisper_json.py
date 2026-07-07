"""OpenAI Whisper verbose_json transcript parser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.validators import ensure_valid_document

_SOURCE_FORMAT = "whisper_json"


def parse_whisper_json(data: dict[str, Any]) -> KaraokeDocument:
    """Parse Whisper verbose_json data into a validated ``KaraokeDocument``."""
    if not isinstance(data, dict):
        raise UnsupportedTranscriptFormatError("Whisper JSON root must be an object")

    if _has_segment_words(data):
        document = _parse_segment_words(data)
    elif _has_root_words(data):
        document = _parse_root_words(data)
    else:
        raise UnsupportedTranscriptFormatError(
            "Unsupported Whisper JSON shape: expected root-level 'words' or "
            "segment-level 'segments[].words' with word timestamps"
        )

    if not document.lines:
        raise TranscriptValidationError("Whisper transcript is empty")

    ensure_valid_document(document)
    return document


def load_whisper_json(path: str | Path) -> KaraokeDocument:
    """Load and parse a Whisper verbose_json file from disk."""
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Cannot read Whisper JSON file {file_path}: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UnsupportedTranscriptFormatError(
            f"Malformed JSON file {file_path}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON root must be an object in {file_path}"
        )

    return parse_whisper_json(data)


def _has_segment_words(data: dict[str, Any]) -> bool:
    segments = data.get("segments")
    if not isinstance(segments, list):
        return False
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        words = segment.get("words")
        if isinstance(words, list) and words:
            return True
    return False


def _has_root_words(data: dict[str, Any]) -> bool:
    words = data.get("words")
    return isinstance(words, list) and bool(words)


def _parse_root_words(data: dict[str, Any]) -> KaraokeDocument:
    words_data = data.get("words")
    if not isinstance(words_data, list) or not words_data:
        raise UnsupportedTranscriptFormatError(
            "Whisper JSON is missing root-level 'words' with timestamps"
        )

    words = tuple(
        _parse_word_entry(entry, path=f"words[{index}]")
        for index, entry in enumerate(words_data)
    )
    line = _build_line(words)
    return KaraokeDocument(lines=(line,), source_format=_SOURCE_FORMAT)


def _parse_segment_words(data: dict[str, Any]) -> KaraokeDocument:
    segments = data.get("segments")
    if not isinstance(segments, list):
        raise UnsupportedTranscriptFormatError(
            "Whisper JSON 'segments' must be a list when segment words are used"
        )

    lines: list[KaraokeLine] = []
    for segment_index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise UnsupportedTranscriptFormatError(
                f"Whisper JSON segments[{segment_index}] must be an object"
            )

        words_data = segment.get("words")
        if not isinstance(words_data, list) or not words_data:
            continue

        words = tuple(
            _parse_word_entry(
                entry,
                path=f"segments[{segment_index}].words[{word_index}]",
            )
            for word_index, entry in enumerate(words_data)
        )
        lines.append(_build_line(words))

    return KaraokeDocument(lines=tuple(lines), source_format=_SOURCE_FORMAT)


def _parse_word_entry(entry: Any, *, path: str) -> Word:
    if not isinstance(entry, dict):
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} must be an object"
        )

    text = _extract_word_text(entry, path=path)
    start = _extract_timestamp(entry, field="start", path=path)
    end = _extract_timestamp(entry, field="end", path=path)

    return Word(text=text, start=start, end=end)


def _extract_word_text(entry: dict[str, Any], *, path: str) -> str:
    if "word" in entry:
        raw_text = entry["word"]
    elif "text" in entry:
        raw_text = entry["text"]
    else:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} is missing 'word' or 'text'"
        )

    if raw_text is None:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has empty text"
        )

    text = str(raw_text).strip()
    if not text:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has empty text after stripping"
        )

    return text


def _extract_timestamp(entry: dict[str, Any], *, field: str, path: str) -> float:
    if field not in entry:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} is missing '{field}' timestamp"
        )

    value = entry[field]
    if value is None:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has null '{field}' timestamp"
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise UnsupportedTranscriptFormatError(
            f"Whisper JSON word entry at {path} has invalid '{field}' timestamp: {value!r}"
        ) from exc


def _build_line(words: tuple[Word, ...]) -> KaraokeLine:
    return KaraokeLine(
        words=words,
        start=words[0].start,
        end=words[-1].end,
    )
