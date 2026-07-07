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

__all__ = [
    "AssGenerationError",
    "AssWriter",
    "KaraokeDocument",
    "KaraokeEngineError",
    "KaraokeLine",
    "KaraokeStyle",
    "TranscriptValidationError",
    "UnsupportedTranscriptFormatError",
    "ValidationReport",
    "ValidationWarning",
    "Word",
    "escape_ass_text",
]

__version__ = "0.1.0"
