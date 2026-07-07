import pytest

import karaoke_engine
from karaoke_engine.errors import TranscriptValidationError
from karaoke_engine.models import KaraokeDocument, KaraokeLine, Word
from karaoke_engine.segmenter import SegmentOptions, segment_document


def _word(text: str, start: float, end: float) -> Word:
    return Word(text=text, start=start, end=end)


def _line(*words: Word) -> KaraokeLine:
    return KaraokeLine(words=words, start=words[0].start, end=words[-1].end)


def _document(*lines: KaraokeLine, source_format: str = "whisper_json") -> KaraokeDocument:
    return KaraokeDocument(lines=lines, source_format=source_format)


def _single_line_document(*words: Word) -> KaraokeDocument:
    return _document(_line(*words))


def _flattened_words(document: KaraokeDocument) -> list[Word]:
    words: list[Word] = []
    for line in document.lines:
        words.extend(line.words)
    return words


def test_splits_by_max_words() -> None:
    words = tuple(_word(f"w{i}", i * 0.2, (i + 1) * 0.2) for i in range(8))
    document = _single_line_document(*words)
    options = SegmentOptions(
        max_words_per_line=3,
        pause_break_seconds=100.0,
        max_line_duration=100.0,
    )

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 3
    assert [len(line.words) for line in segmented.lines] == [3, 3, 2]


def test_splits_by_max_chars() -> None:
    document = _single_line_document(
        _word("one", 0.0, 0.2),
        _word("two", 0.2, 0.4),
        _word("three", 0.4, 0.6),
        _word("four", 0.6, 0.8),
    )
    options = SegmentOptions(
        max_words_per_line=10,
        max_chars_per_line=10,
        max_line_duration=100.0,
        pause_break_seconds=100.0,
    )

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 2
    assert [word.text for word in segmented.lines[0].words] == ["one", "two"]
    assert [word.text for word in segmented.lines[1].words] == ["three", "four"]


def test_splits_by_max_duration() -> None:
    document = _single_line_document(
        _word("a", 0.0, 2.0),
        _word("b", 2.0, 4.0),
        _word("c", 4.0, 6.5),
    )
    options = SegmentOptions(
        max_words_per_line=10,
        max_chars_per_line=100,
        max_line_duration=5.0,
        pause_break_seconds=100.0,
    )

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 2
    assert [word.text for word in segmented.lines[0].words] == ["a", "b"]
    assert [word.text for word in segmented.lines[1].words] == ["c"]


def test_splits_by_pause() -> None:
    document = _single_line_document(
        _word("hello", 0.0, 0.5),
        _word("world", 1.5, 2.0),
        _word("again", 2.0, 2.5),
    )
    options = SegmentOptions(
        max_words_per_line=10,
        max_chars_per_line=100,
        max_line_duration=100.0,
        pause_break_seconds=0.65,
    )

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 2
    assert [word.text for word in segmented.lines[0].words] == ["hello"]
    assert [word.text for word in segmented.lines[1].words] == ["world", "again"]


def test_splits_after_punctuation_when_min_duration_is_met() -> None:
    document = _single_line_document(
        _word("Yes!", 0.0, 1.0),
        _word("continue", 1.0, 1.5),
    )
    options = SegmentOptions(
        max_words_per_line=10,
        max_chars_per_line=100,
        max_line_duration=100.0,
        min_line_duration=0.8,
        pause_break_seconds=100.0,
    )

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 2
    assert segmented.lines[0].words == (_word("Yes!", 0.0, 1.0),)
    assert segmented.lines[1].words == (_word("continue", 1.0, 1.5),)


def test_does_not_split_after_punctuation_before_min_duration() -> None:
    document = _single_line_document(
        _word("Go!", 0.0, 0.2),
        _word("on", 0.2, 0.5),
    )
    options = SegmentOptions(
        max_words_per_line=10,
        max_chars_per_line=100,
        max_line_duration=100.0,
        min_line_duration=0.8,
        pause_break_seconds=100.0,
    )

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 1
    assert [word.text for word in segmented.lines[0].words] == ["Go!", "on"]


def test_preserves_all_words_exactly_once() -> None:
    document = _single_line_document(
        _word("Aku", 0.0, 0.4),
        _word("cinta", 0.4, 0.75),
        _word("padamu", 0.75, 1.55),
        _word("selamanya", 1.55, 2.2),
    )
    options = SegmentOptions(max_words_per_line=2)

    segmented = segment_document(document, options)
    input_words = _flattened_words(document)
    output_words = _flattened_words(segmented)

    assert output_words == input_words
    assert len(output_words) == len(set((w.text, w.start, w.end) for w in output_words))


def test_preserves_word_order() -> None:
    document = _single_line_document(
        _word("one", 0.0, 0.2),
        _word("two", 0.2, 0.4),
        _word("three", 0.4, 0.6),
        _word("four", 0.6, 0.8),
        _word("five", 0.8, 1.0),
    )
    options = SegmentOptions(max_words_per_line=2)

    segmented = segment_document(document, options)
    assert [word.text for word in _flattened_words(segmented)] == [
        "one",
        "two",
        "three",
        "four",
        "five",
    ]


def test_does_not_mutate_input_document() -> None:
    document = _single_line_document(
        _word("one", 0.0, 0.2),
        _word("two", 0.2, 0.4),
        _word("three", 0.4, 0.6),
    )
    before = KaraokeDocument(
        lines=document.lines,
        source_format=document.source_format,
    )

    segment_document(document, SegmentOptions(max_words_per_line=1))

    assert document == before


def test_validates_input_document() -> None:
    document = KaraokeDocument(
        lines=(
            KaraokeLine(
                words=(_word("bad", 1.0, 1.0),),
                start=0.0,
                end=1.0,
            ),
        )
    )
    with pytest.raises(TranscriptValidationError):
        segment_document(document)


def test_validates_output_document() -> None:
    document = _single_line_document(_word("ok", 0.0, 0.5))
    segmented = segment_document(document)
    assert segmented.lines[0].start == 0.0
    assert segmented.lines[0].end == 0.5


def test_rejects_invalid_segment_options() -> None:
    with pytest.raises(ValueError, match="max_words_per_line"):
        SegmentOptions(max_words_per_line=0)

    with pytest.raises(ValueError, match="max_chars_per_line"):
        SegmentOptions(max_chars_per_line=0)

    with pytest.raises(ValueError, match="max_line_duration must be > 0"):
        SegmentOptions(max_line_duration=0)

    with pytest.raises(ValueError, match="max_line_duration must be >= min_line_duration"):
        SegmentOptions(max_line_duration=1.0, min_line_duration=2.0)


def test_handles_single_long_word_as_one_line() -> None:
    document = _single_line_document(_word("supercalifragilistic", 0.0, 0.5))
    options = SegmentOptions(max_chars_per_line=5)

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 1
    assert segmented.lines[0].words[0].text == "supercalifragilistic"


def test_handles_single_long_duration_word_as_one_line() -> None:
    document = _single_line_document(_word("hold", 0.0, 8.0))
    options = SegmentOptions(max_line_duration=2.0)

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 1
    assert segmented.lines[0].words[0].text == "hold"


def test_preserves_source_format_by_default() -> None:
    document = _document(
        _line(_word("one", 0.0, 0.2), _word("two", 0.2, 0.4)),
        source_format="whisper_json",
    )
    segmented = segment_document(document, SegmentOptions(max_words_per_line=1))
    assert segmented.source_format == "whisper_json"


def test_can_set_source_format_to_segmented() -> None:
    document = _single_line_document(_word("one", 0.0, 0.2), _word("two", 0.2, 0.4))
    options = SegmentOptions(max_words_per_line=1, preserve_source_format=False)
    segmented = segment_document(document, options)
    assert segmented.source_format == "segmented"


def test_deterministic_output_for_same_input_and_options() -> None:
    document = _single_line_document(
        _word("Aku", 0.0, 0.4),
        _word("cinta", 0.4, 0.75),
        _word("padamu", 0.75, 1.55),
        _word("dan", 1.55, 1.8),
        _word("kamu", 1.8, 2.1),
    )
    options = SegmentOptions(max_words_per_line=2)

    first = segment_document(document, options)
    second = segment_document(document, options)

    assert first == second


def test_works_with_multi_line_input_from_gate_3() -> None:
    document = _document(
        _line(_word("Aku", 0.0, 0.4)),
        _line(_word("cinta", 0.4, 0.75), _word("padamu", 0.75, 1.55)),
        source_format="whisper_json",
    )
    options = SegmentOptions(max_words_per_line=2)

    segmented = segment_document(document, options)

    assert len(segmented.lines) == 2
    assert [word.text for word in segmented.lines[0].words] == ["Aku", "cinta"]
    assert [word.text for word in segmented.lines[1].words] == ["padamu"]


def test_public_exports_work() -> None:
    assert karaoke_engine.SegmentOptions is SegmentOptions
    assert karaoke_engine.segment_document is segment_document
    assert "SegmentOptions" in karaoke_engine.__all__
    assert "segment_document" in karaoke_engine.__all__


def test_raises_when_document_has_no_words() -> None:
    document = KaraokeDocument(lines=(), source_format="whisper_json")
    with pytest.raises(TranscriptValidationError):
        segment_document(document)


def test_no_future_gate_behavior_is_introduced() -> None:
    module_path = karaoke_engine.__file__
    assert module_path is not None
    root_names = set(dir(karaoke_engine))
    assert "Engine" not in root_names
    assert "render_video" not in root_names
    assert "parse_srt" not in root_names
    assert "parse_vtt" not in root_names
