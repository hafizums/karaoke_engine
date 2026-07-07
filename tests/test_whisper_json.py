import json
from pathlib import Path

import pytest

import karaoke_engine
from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.parsers import load_whisper_json, parse_whisper_json
from karaoke_engine.parsers.whisper_json import parse_whisper_json as parse_whisper_json_direct


ROOT_WORDS_PAYLOAD = {
    "text": "Aku cinta padamu",
    "words": [
        {"word": "Aku", "start": 0.0, "end": 0.4},
        {"word": "cinta", "start": 0.4, "end": 0.75},
        {"word": "padamu", "start": 0.75, "end": 1.55},
    ],
}

SEGMENT_WORDS_PAYLOAD = {
    "text": "Aku cinta padamu",
    "segments": [
        {
            "start": 0.0,
            "end": 1.55,
            "text": "Aku cinta padamu",
            "words": [
                {"word": "Aku", "start": 0.0, "end": 0.4},
                {"word": "cinta", "start": 0.4, "end": 0.75},
                {"word": "padamu", "start": 0.75, "end": 1.55},
            ],
        }
    ],
}


def test_parses_root_level_words() -> None:
    document = parse_whisper_json(ROOT_WORDS_PAYLOAD)
    assert document.source_format == "whisper_json"
    assert len(document.lines) == 1
    assert document.lines[0].words == (
        Word(text="Aku", start=0.0, end=0.4),
        Word(text="cinta", start=0.4, end=0.75),
        Word(text="padamu", start=0.75, end=1.55),
    )
    assert document.lines[0].start == 0.0
    assert document.lines[0].end == 1.55


def test_parses_segment_level_words() -> None:
    document = parse_whisper_json(SEGMENT_WORDS_PAYLOAD)
    assert len(document.lines) == 1
    assert len(document.lines[0].words) == 3


def test_prefers_segment_level_words_over_root_level_words() -> None:
    payload = {
        **ROOT_WORDS_PAYLOAD,
        "segments": [
            {
                "start": 0.0,
                "end": 0.4,
                "text": "Aku",
                "words": [{"word": "Aku", "start": 0.0, "end": 0.4}],
            },
            {
                "start": 0.4,
                "end": 1.55,
                "text": "cinta padamu",
                "words": [
                    {"word": "cinta", "start": 0.4, "end": 0.75},
                    {"word": "padamu", "start": 0.75, "end": 1.55},
                ],
            },
        ],
    }
    document = parse_whisper_json(payload)
    assert len(document.lines) == 2
    assert len(document.lines[0].words) == 1
    assert len(document.lines[1].words) == 2


def test_accepts_text_key_when_word_key_is_absent() -> None:
    payload = {
        "words": [
            {"text": " Hello ", "start": 0.0, "end": 0.5},
        ]
    }
    document = parse_whisper_json(payload)
    assert document.lines[0].words[0].text == "Hello"


def test_strips_word_whitespace() -> None:
    payload = {
        "words": [
            {"word": "  Aku  ", "start": 0.0, "end": 0.4},
        ]
    }
    document = parse_whisper_json(payload)
    assert document.lines[0].words[0].text == "Aku"


def test_preserves_punctuation() -> None:
    payload = {
        "words": [
            {"word": "Hello,", "start": 0.0, "end": 0.4},
            {"word": "world!", "start": 0.4, "end": 0.8},
        ]
    }
    document = parse_whisper_json(payload)
    assert document.lines[0].words[0].text == "Hello,"
    assert document.lines[0].words[1].text == "world!"


def test_converts_timestamps_to_float() -> None:
    payload = {
        "words": [
            {"word": "Aku", "start": 0, "end": "0.4"},
        ]
    }
    document = parse_whisper_json(payload)
    assert document.lines[0].words[0].start == 0.0
    assert document.lines[0].words[0].end == 0.4


def test_rejects_missing_words() -> None:
    with pytest.raises(UnsupportedTranscriptFormatError, match="Unsupported Whisper JSON shape"):
        parse_whisper_json({"text": "Aku cinta padamu"})


def test_rejects_missing_start_or_end() -> None:
    with pytest.raises(UnsupportedTranscriptFormatError, match="missing 'start'"):
        parse_whisper_json({"words": [{"word": "Aku", "end": 0.4}]})

    with pytest.raises(UnsupportedTranscriptFormatError, match="missing 'end'"):
        parse_whisper_json({"words": [{"word": "Aku", "start": 0.0}]})


def test_rejects_empty_text() -> None:
    with pytest.raises(UnsupportedTranscriptFormatError, match="empty text"):
        parse_whisper_json({"words": [{"word": "   ", "start": 0.0, "end": 0.4}]})


def test_rejects_invalid_timing() -> None:
    with pytest.raises(TranscriptValidationError, match="greater than start time"):
        parse_whisper_json({"words": [{"word": "Aku", "start": 1.0, "end": 1.0}]})


def test_rejects_malformed_json_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(UnsupportedTranscriptFormatError, match="Malformed JSON"):
        load_whisper_json(path)


def test_rejects_unsupported_json_shape() -> None:
    with pytest.raises(UnsupportedTranscriptFormatError, match="must be an object"):
        parse_whisper_json([])  # type: ignore[arg-type]

    with pytest.raises(UnsupportedTranscriptFormatError, match="Unsupported Whisper JSON shape"):
        parse_whisper_json({"segments": [{"start": 0.0, "end": 1.0, "text": "no words"}]})


def test_ignores_empty_segments() -> None:
    payload = {
        "segments": [
            {"start": 0.0, "end": 0.2, "text": "", "words": []},
            {
                "start": 0.2,
                "end": 0.6,
                "text": "Aku",
                "words": [{"word": "Aku", "start": 0.2, "end": 0.6}],
            },
        ]
    }
    document = parse_whisper_json(payload)
    assert len(document.lines) == 1
    assert document.lines[0].words[0].text == "Aku"


def test_validates_document_before_returning() -> None:
    document = parse_whisper_json(ROOT_WORDS_PAYLOAD)
    assert isinstance(document, KaraokeDocument)
    assert all(isinstance(line, KaraokeLine) for line in document.lines)


def test_load_whisper_json_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "whisper.json"
    path.write_text(json.dumps(ROOT_WORDS_PAYLOAD), encoding="utf-8")
    document = load_whisper_json(path)
    assert len(document.lines) == 1


def test_public_exports_work() -> None:
    assert karaoke_engine.parse_whisper_json is parse_whisper_json_direct
    assert karaoke_engine.load_whisper_json is load_whisper_json
    assert "parse_whisper_json" in karaoke_engine.__all__
    assert "load_whisper_json" in karaoke_engine.__all__


def test_no_gate_4_segmentation_behavior() -> None:
    payload = {
        "words": [
            {"word": "one", "start": 0.0, "end": 0.2},
            {"word": "two", "start": 5.0, "end": 5.2},
            {"word": "three", "start": 10.0, "end": 10.2},
        ]
    }
    document = parse_whisper_json(payload)
    assert len(document.lines) == 1
    assert len(document.lines[0].words) == 3

    segmented_payload = {
        "segments": [
            {
                "start": 0.0,
                "end": 0.2,
                "text": "one",
                "words": [{"word": "one", "start": 0.0, "end": 0.2}],
            },
            {
                "start": 5.0,
                "end": 10.2,
                "text": "two three",
                "words": [
                    {"word": "two", "start": 5.0, "end": 5.2},
                    {"word": "three", "start": 10.0, "end": 10.2},
                ],
            },
        ]
    }
    segmented_document = parse_whisper_json(segmented_payload)
    assert len(segmented_document.lines) == 2
    assert len(segmented_document.lines[0].words) == 1
    assert len(segmented_document.lines[1].words) == 2
