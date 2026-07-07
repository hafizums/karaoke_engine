"""Lightweight server-friendly karaoke subtitle engine."""

from karaoke_engine.errors import (
    AssGenerationError,
    KaraokeEngineError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)
from karaoke_engine.ass import AssWriter, KaraokeStyle, escape_ass_text
from karaoke_engine.models import (
    KaraokeDocument,
    KaraokeLine,
    ValidationReport,
    ValidationWarning,
    Word,
)
from karaoke_engine.parsers import load_whisper_json, parse_whisper_json
from karaoke_engine.segmenter import SegmentOptions, segment_document

__all__ = [
    "AssGenerationError",
    "AssWriter",
    "KaraokeDocument",
    "KaraokeEngineError",
    "KaraokeLine",
    "KaraokeStyle",
    "SegmentOptions",
    "TranscriptValidationError",
    "UnsupportedTranscriptFormatError",
    "ValidationReport",
    "ValidationWarning",
    "Word",
    "escape_ass_text",
    "load_whisper_json",
    "parse_whisper_json",
    "segment_document",
]

__version__ = "0.1.0"
