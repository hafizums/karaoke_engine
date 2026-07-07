"""Validation helpers for karaoke documents."""

from __future__ import annotations

import re

from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, ValidationReport, Word

_ASS_OVERRIDE_TAG_PATTERN = re.compile(r"\{[^}]*\}")


def _validate_timestamp(value: float, path: str, report: ValidationReport) -> None:
    if value < 0:
        report.add_error(
            code="negative_timestamp",
            message=f"Timestamp must not be negative: {value}",
            path=path,
        )


def _validate_word_timing(word: Word, path: str, report: ValidationReport) -> None:
    _validate_timestamp(word.start, f"{path}.start", report)
    _validate_timestamp(word.end, f"{path}.end", report)
    if word.end <= word.start:
        report.add_error(
            code="invalid_word_timing",
            message=(
                f"Word end time must be greater than start time: "
                f"start={word.start}, end={word.end}"
            ),
            path=path,
        )


def _validate_text(text: str, path: str, report: ValidationReport) -> None:
    if not text or not text.strip():
        report.add_error(
            code="empty_text",
            message="Text must not be empty",
            path=path,
        )
        return

    if _ASS_OVERRIDE_TAG_PATTERN.search(text):
        report.add_error(
            code="ass_override_tag",
            message="Raw ASS override tags are not allowed in transcript text",
            path=path,
        )


def validate_word(word: Word, path: str = "word") -> ValidationReport:
    """Validate a single word."""
    report = ValidationReport()
    _validate_text(word.text, f"{path}.text", report)
    _validate_word_timing(word, path, report)
    return report


def validate_line(line: KaraokeLine, path: str = "line") -> ValidationReport:
    """Validate a karaoke line and its words."""
    report = ValidationReport()
    _validate_timestamp(line.start, f"{path}.start", report)
    _validate_timestamp(line.end, f"{path}.end", report)
    if line.end <= line.start:
        report.add_error(
            code="invalid_line_timing",
            message=(
                f"Line end time must be greater than start time: "
                f"start={line.start}, end={line.end}"
            ),
            path=path,
        )

    if not line.words:
        report.add_error(
            code="empty_line",
            message="Line must contain at least one word",
            path=path,
        )

    for index, word in enumerate(line.words):
        word_report = validate_word(word, path=f"{path}.words[{index}]")
        report.warnings.extend(word_report.warnings)
        report.errors.extend(word_report.errors)

    return report


def validate_document(document: KaraokeDocument) -> ValidationReport:
    """Validate a karaoke document."""
    report = ValidationReport()
    if not document.lines:
        report.add_error(
            code="empty_document",
            message="Document must contain at least one line",
            path="document",
        )

    for index, line in enumerate(document.lines):
        line_report = validate_line(line, path=f"lines[{index}]")
        report.warnings.extend(line_report.warnings)
        report.errors.extend(line_report.errors)

    return report


def ensure_valid_document(document: KaraokeDocument) -> ValidationReport:
    """Validate a document and raise if invalid."""
    report = validate_document(document)
    if not report.is_valid:
        messages = "; ".join(error.message for error in report.errors)
        raise TranscriptValidationError(messages)
    return report
