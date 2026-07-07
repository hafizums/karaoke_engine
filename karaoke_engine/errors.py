"""Custom exceptions for karaoke_engine."""


class KaraokeEngineError(Exception):
    """Base exception for all karaoke_engine errors."""


class UnsupportedTranscriptFormatError(KaraokeEngineError):
    """Raised when an input transcript format is not supported."""


class TranscriptValidationError(KaraokeEngineError):
    """Raised when transcript data fails validation."""


class AssGenerationError(KaraokeEngineError):
    """Raised when ASS subtitle generation fails."""
