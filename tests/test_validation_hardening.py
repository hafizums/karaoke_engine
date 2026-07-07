import pytest

from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.validators import ensure_valid_document, validate_document


def _valid_document() -> KaraokeDocument:
    return KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(
                    Word(text="hello", start=0.0, end=0.5),
                    Word(text="world", start=0.5, end=1.0),
                ),
                start=0.0,
                end=1.0,
            ),
        ),
        source_format="whisper_json",
    )


def test_validate_document_report_mode_accepts_valid_document() -> None:
    report = validate_document(_valid_document())
    assert report.is_valid
    assert not report.errors


def test_ensure_valid_document_raises_for_invalid_document() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="bad", start=1.0, end=1.0),),
                start=0.0,
                end=1.0,
            ),
        ),
        source_format="whisper_json",
    )
    with pytest.raises(TranscriptValidationError):
        ensure_valid_document(document)


def test_rejects_empty_source_format() -> None:
    document = KaraokeDocument(lines=_valid_document().lines, source_format="   ")
    report = validate_document(document)
    assert not report.is_valid
    assert any(error.code == "empty_source_format" for error in report.errors)


def test_rejects_line_start_after_first_word() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="hello", start=0.0, end=0.5),),
                start=0.5,
                end=0.5,
            ),
        ),
        source_format="whisper_json",
    )
    report = validate_document(document)
    assert any(error.code == "line_start_after_first_word" for error in report.errors)


def test_rejects_line_end_before_last_word() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="hello", start=0.0, end=1.0),),
                start=0.0,
                end=0.5,
            ),
        ),
        source_format="whisper_json",
    )
    report = validate_document(document)
    assert any(error.code == "line_end_before_last_word" for error in report.errors)


def test_rejects_non_decreasing_word_starts() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(
                    Word(text="one", start=0.5, end=0.8),
                    Word(text="two", start=0.2, end=1.0),
                ),
                start=0.2,
                end=1.0,
            ),
        ),
        source_format="whisper_json",
    )
    report = validate_document(document)
    assert any(error.code == "word_start_order" for error in report.errors)


def test_overlapping_words_produce_warning_not_error() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(
                    Word(text="one", start=0.0, end=0.6),
                    Word(text="two", start=0.2, end=1.0),
                ),
                start=0.0,
                end=1.0,
            ),
        ),
        source_format="whisper_json",
    )
    report = validate_document(document)
    assert report.is_valid
    assert any(warning.code == "overlapping_words" for warning in report.warnings)


def test_line_padding_before_first_word_is_allowed() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="hello", start=0.2, end=1.0),),
                start=0.0,
                end=1.0,
            ),
        ),
        source_format="whisper_json",
    )
    report = validate_document(document)
    assert report.is_valid
