"""Lightweight server-friendly karaoke subtitle engine."""

from karaoke_engine.errors import (
    AssGenerationError,
    KaraokeEngineError,
    RenderError,
    TranscriptValidationError,
    UnsupportedTranscriptFormatError,
)
from karaoke_engine.ass import AssWriter, KaraokeStyle, escape_ass_text
from karaoke_engine.engine import CreateAssResult, KaraokeEngine, RenderKaraokeVideoResult
from karaoke_engine.models import (
    KaraokeDocument,
    KaraokeLine,
    ValidationReport,
    ValidationWarning,
    Word,
)
from karaoke_engine.parsers import load_whisper_json, parse_whisper_json
from karaoke_engine.render import (
    RenderOptions,
    RenderVideoResult,
    VideoInfo,
    build_ffmpeg_ass_burn_command,
    build_ffprobe_command,
    probe_video,
    render_ass_to_video,
)
from karaoke_engine.segmenter import SegmentOptions, segment_document

__all__ = [
    "AssGenerationError",
    "AssWriter",
    "CreateAssResult",
    "KaraokeDocument",
    "KaraokeEngine",
    "KaraokeEngineError",
    "KaraokeLine",
    "KaraokeStyle",
    "RenderError",
    "RenderKaraokeVideoResult",
    "RenderOptions",
    "RenderVideoResult",
    "SegmentOptions",
    "TranscriptValidationError",
    "UnsupportedTranscriptFormatError",
    "ValidationReport",
    "ValidationWarning",
    "VideoInfo",
    "Word",
    "build_ffmpeg_ass_burn_command",
    "build_ffprobe_command",
    "escape_ass_text",
    "load_whisper_json",
    "parse_whisper_json",
    "probe_video",
    "render_ass_to_video",
    "segment_document",
]

__version__ = "0.1.0"
