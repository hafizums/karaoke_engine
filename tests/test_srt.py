import pytest

import karaoke_engine
from karaoke_engine.errors import TranscriptValidationError, UnsupportedTranscriptFormatError
from karaoke_engine.parsers.srt import load_srt, parse_srt_text


BASIC_SRT = """1
00:00:01,000 --> 00:00:03,500
Hello world!

2
00:00:04,000 --> 00:00:06,000
<i>Bye</i> there.
"""


def test_parses_basic_srt() -> None:
    document = parse_srt_text(BASIC_SRT)
    assert document.source_format == "srt_approx"
    assert len(document.lines) == 2
    assert [word.text for word in document.lines[0].words] == ["Hello", "world!"]


def test_parses_cue_index_lines() -> None:
    document = parse_srt_text(BASIC_SRT)
    assert document.lines[0].start == 1.0
    assert document.lines[0].end == 3.5


def test_parses_multiline_text() -> None:
    srt = """1
00:00:00,000 --> 00:00:02,000
Hello
world
"""
    document = parse_srt_text(srt)
    assert [word.text for word in document.lines[0].words] == ["Hello", "world"]


def test_strips_simple_tags() -> None:
    document = parse_srt_text(BASIC_SRT)
    assert [word.text for word in document.lines[1].words] == ["Bye", "there."]


def test_preserves_punctuation() -> None:
    document = parse_srt_text(BASIC_SRT)
    assert document.lines[0].words[1].text == "world!"


def test_evenly_distributes_approximate_word_timings() -> None:
    document = parse_srt_text(BASIC_SRT)
    first_line = document.lines[0]
    assert first_line.words[0].start == 1.0
    assert first_line.words[0].end == pytest.approx(2.25)
    assert first_line.words[1].start == pytest.approx(2.25)


def test_last_word_end_equals_cue_end() -> None:
    document = parse_srt_text(BASIC_SRT)
    for line in document.lines:
        assert line.words[-1].end == line.end


def test_rejects_malformed_timing() -> None:
    srt = """1
bad timing
Hello
"""
    with pytest.raises(UnsupportedTranscriptFormatError, match="Malformed SRT timing"):
        parse_srt_text(srt)


def test_rejects_end_before_start() -> None:
    srt = """1
00:00:03,000 --> 00:00:01,000
Hello
"""
    with pytest.raises(UnsupportedTranscriptFormatError, match="greater than start"):
        parse_srt_text(srt)


def test_ignores_empty_cues() -> None:
    srt = """1
00:00:00,000 --> 00:00:01,000


2
00:00:01,000 --> 00:00:02,000
Hello
"""
    document = parse_srt_text(srt)
    assert len(document.lines) == 1
    assert document.lines[0].words[0].text == "Hello"


def test_rejects_empty_transcript() -> None:
    with pytest.raises(TranscriptValidationError, match="empty"):
        parse_srt_text("")


def test_public_exports_work() -> None:
    assert karaoke_engine.parse_srt_text is parse_srt_text
    assert karaoke_engine.load_srt is load_srt
    assert "parse_srt_text" in karaoke_engine.__all__
    assert "load_srt" in karaoke_engine.__all__


def test_load_srt_reads_file(tmp_path) -> None:
    path = tmp_path / "sample.srt"
    path.write_text(BASIC_SRT, encoding="utf-8")
    document = load_srt(path)
    assert document.source_format == "srt_approx"
