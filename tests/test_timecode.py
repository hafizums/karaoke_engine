import pytest

from karaoke_engine.utils.timecode import seconds_to_ass_time, seconds_to_centiseconds


def test_seconds_to_centiseconds_rounds_deterministically() -> None:
    assert seconds_to_centiseconds(0.0) == 0
    assert seconds_to_centiseconds(1.234) == 123
    assert seconds_to_centiseconds(1.235) == 124


def test_seconds_to_ass_time_formats_values() -> None:
    assert seconds_to_ass_time(0.0) == "0:00:00.00"
    assert seconds_to_ass_time(61.23) == "0:01:01.23"
    assert seconds_to_ass_time(3661.01) == "1:01:01.01"


def test_seconds_to_ass_time_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        seconds_to_ass_time(-0.1)

    with pytest.raises(ValueError, match="must not be negative"):
        seconds_to_centiseconds(-1.0)
