from app.llm import parse_stream_token


def test_parse_stream_token_reads_delta_content() -> None:
    data = '{"choices":[{"delta":{"content":"hello"}}]}'

    assert parse_stream_token(data) == "hello"


def test_parse_stream_token_ignores_invalid_payload() -> None:
    assert parse_stream_token("{}") == ""
