from karaoke_engine.ass.escape import escape_ass_text


def test_escape_ass_text_escapes_special_characters() -> None:
    assert escape_ass_text("hello") == "hello"
    assert escape_ass_text("a\\b") == "a\\\\b"
    assert escape_ass_text("{tag}") == "\\{tag\\}"
    assert escape_ass_text("line1\nline2") == "line1\\Nline2"
    assert escape_ass_text("line1\r\nline2") == "line1\\Nline2"


def test_escape_ass_text_is_deterministic() -> None:
    text = "Sing\\along {now}\r\n"
    assert escape_ass_text(text) == escape_ass_text(text)
