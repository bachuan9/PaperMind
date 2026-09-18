import json

from app.main import chunk_text, stream_event


def test_stream_event_returns_ndjson_line() -> None:
    line = stream_event("token", {"token": "hello"})

    assert line.endswith("\n")
    assert json.loads(line) == {"type": "token", "token": "hello"}


def test_chunk_text_splits_answer() -> None:
    assert chunk_text("abcdef", size=2) == ["ab", "cd", "ef"]
