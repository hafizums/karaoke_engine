import pytest

from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.validators import ensure_valid_document, validate_document, validate_word


def test_validate_word_accepts_valid_word() -> None:
    word = Word(text="hello", start=0.0, end=0.5)
    report = validate_word(word)
    assert report.is_valid


def test_validate_word_rejects_empty_text() -> None:
    word = Word(text="   ", start=0.0, end=0.5)
    report = validate_word(word)
    assert not report.is_valid
    assert any(error.code == "empty_text" for error in report.errors)


def test_validate_word_rejects_negative_timestamps() -> None:
    word = Word(text="hello", start=-0.1, end=0.5)
    report = validate_word(word)
    assert not report.is_valid
    assert any(error.code == "negative_timestamp" for error in report.errors)


def test_validate_word_rejects_invalid_timing() -> None:
    word = Word(text="hello", start=1.0, end=1.0)
    report = validate_word(word)
    assert not report.is_valid
    assert any(error.code == "invalid_word_timing" for error in report.errors)


def test_validate_word_rejects_ass_override_tags() -> None:
    word = Word(text=r"{\k50}sing", start=0.0, end=0.5)
    report = validate_word(word)
    assert not report.is_valid
    assert any(error.code == "ass_override_tag" for error in report.errors)


def test_validate_document_and_raise() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="hello", start=0.0, end=0.5),),
                start=0.0,
                end=0.5,
            ),
        )
    )
    assert validate_document(document).is_valid
    ensure_valid_document(document)


def test_ensure_valid_document_raises_for_invalid_data() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(Word(text="", start=0.0, end=0.5),),
                start=0.0,
                end=0.5,
            ),
        )
    )
    with pytest.raises(TranscriptValidationError):
        ensure_valid_document(document)
