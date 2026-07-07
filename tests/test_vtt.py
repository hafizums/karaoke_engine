import pytest

import karaoke_engine
from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.parsers.vtt import load_vtt, parse_vtt_text


BASIC_VTT = """WEBVTT
Kind: captions
Language: en

cue-1
00:00:01.000 --> 00:00:03.500
Hello world!

00:01.000 --> 00:03.500
<i>Bye</i> there.

NOTE
This should be ignored

01:00.000 --> 01:01.000
Final cue
"""


def test_parses_webvtt_header() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert document.source_format == "vtt_approx"
    assert len(document.lines) == 3


def test_parses_header_metadata() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert document.lines[0].words[0].text == "Hello"


def test_parses_cue_identifiers() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert document.lines[0].start == 1.0


def test_parses_note_blocks_and_ignores_them() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert all("ignored" not in word.text for line in document.lines for word in line.words)


def test_parses_full_and_short_timestamps() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert document.lines[0].end == 3.5
    assert document.lines[1].start == 1.0
    assert document.lines[1].end == 3.5
    assert document.lines[2].start == 60.0
    assert document.lines[2].end == 61.0


def test_parses_multiline_cue_text() -> None:
    vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello
world
"""
    document = parse_vtt_text(vtt)
    assert [word.text for word in document.lines[0].words] == ["Hello", "world"]


def test_strips_simple_tags() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert [word.text for word in document.lines[1].words] == ["Bye", "there."]


def test_preserves_punctuation() -> None:
    document = parse_vtt_text(BASIC_VTT)
    assert document.lines[0].words[1].text == "world!"


def test_evenly_distributes_approximate_word_timings() -> None:
    document = parse_vtt_text(BASIC_VTT)
    first_line = document.lines[0]
    assert first_line.words[0].start == 1.0
    assert first_line.words[0].end == pytest.approx(2.25)


def test_last_word_end_equals_cue_end() -> None:
    document = parse_vtt_text(BASIC_VTT)
    for line in document.lines:
        assert line.words[-1].end == line.end


def test_rejects_malformed_timing() -> None:
    vtt = """WEBVTT

bad timing
Hello
"""
    with pytest.raises(UnsupportedTranscriptFormatError, match="missing a timing line"):
        parse_vtt_text(vtt)


def test_rejects_empty_transcript() -> None:
    with pytest.raises(TranscriptValidationError, match="empty"):
        parse_vtt_text("WEBVTT\n\n")


def test_rejects_missing_webvtt_header() -> None:
    with pytest.raises(UnsupportedTranscriptFormatError, match="WEBVTT"):
        parse_vtt_text("00:00:01.000 --> 00:00:02.000\nHello")


def test_public_exports_work() -> None:
    assert karaoke_engine.parse_vtt_text is parse_vtt_text
    assert karaoke_engine.load_vtt is load_vtt
    assert "parse_vtt_text" in karaoke_engine.__all__
    assert "load_vtt" in karaoke_engine.__all__


def test_load_vtt_reads_file(tmp_path) -> None:
    path = tmp_path / "sample.vtt"
    path.write_text(BASIC_VTT, encoding="utf-8")
    document = load_vtt(path)
    assert document.source_format == "vtt_approx"
