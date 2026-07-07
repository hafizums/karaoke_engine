"""Validation helpers for karaoke documents."""

from __future__ import annotations

import re

from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, ValidationReport, Word

_ASS_OVERRIDE_TAG_PATTERN = re.compile(r"\{[^}]*\}")
_TIMING_TOLERANCE_SECONDS = 0.001


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


def _validate_line_word_consistency(
    line: KaraokeLine,
    path: str,
    report: ValidationReport,
) -> None:
    if not line.words:
        return

    first_word = line.words[0]
    last_word = line.words[-1]

    if line.start > first_word.start + _TIMING_TOLERANCE_SECONDS:
        report.add_error(
            code="line_start_after_first_word",
            message=(
                f"Line start must be less than or equal to first word start: "
                f"line_start={line.start}, first_word_start={first_word.start}"
            ),
            path=path,
        )

    if line.end + _TIMING_TOLERANCE_SECONDS < last_word.end:
        report.add_error(
            code="line_end_before_last_word",
            message=(
                f"Line end must be greater than or equal to last word end: "
                f"line_end={line.end}, last_word_end={last_word.end}"
            ),
            path=path,
        )

    for index in range(1, len(line.words)):
        previous_word = line.words[index - 1]
        current_word = line.words[index]

        if current_word.start + _TIMING_TOLERANCE_SECONDS < previous_word.start:
            report.add_error(
                code="word_start_order",
                message=(
                    "Words inside a line must be in non-decreasing start-time order: "
                    f"previous_start={previous_word.start}, "
                    f"current_start={current_word.start}"
                ),
                path=f"{path}.words[{index}]",
            )

        if current_word.start + _TIMING_TOLERANCE_SECONDS < previous_word.end:
            report.add_warning(
                code="overlapping_words",
                message=(
                    "Words overlap beyond timing tolerance: "
                    f"previous_end={previous_word.end}, "
                    f"current_start={current_word.start}"
                ),
                path=f"{path}.words[{index}]",
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

    _validate_line_word_consistency(line, path, report)
    return report


def validate_document(document: KaraokeDocument) -> ValidationReport:
    """Validate a karaoke document."""
    report = ValidationReport()

    if not document.source_format or not document.source_format.strip():
        report.add_error(
            code="empty_source_format",
            message="Document source_format must be non-empty",
            path="document.source_format",
        )

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
