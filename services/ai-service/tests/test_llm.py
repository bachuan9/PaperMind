from app.llm import build_chat_request, parse_stream_token, prepare_history_messages
from app.models import Citation, ConversationMessage
from app.settings import Settings
from app.storage import now_utc


def test_parse_stream_token_reads_delta_content() -> None:
    data = '{"choices":[{"delta":{"content":"hello"}}]}'

    assert parse_stream_token(data) == "hello"


def test_parse_stream_token_ignores_invalid_payload() -> None:
    assert parse_stream_token("{}") == ""


def test_build_chat_request_requires_fixed_answer_structure() -> None:
    _, _, payload = build_chat_request(
        settings=Settings(deepseek_api_key="sk-test"),
        question="\u4ec0\u4e48\u662f\u5f15\u7528\u6eaf\u6e90\uff1f",
        citations=[
            Citation(
                chunk_id="chunk-1",
                page_number=3,
                text="\u5f15\u7528\u6eaf\u6e90\u9700\u8981\u5c55\u793a\u539f\u6587\u7247\u6bb5\u3002",
                score=0.9,
            )
        ],
        stream=False,
    )

    prompt = payload["messages"][-1]["content"]
    assert "## \u76f4\u63a5\u56de\u7b54" in prompt
    assert "## \u6587\u6863\u4f9d\u636e" in prompt
    assert "## \u8fb9\u754c\u548c\u4e0d\u786e\u5b9a\u6027" in prompt
    assert "\u4e0d\u8981\u4f2a\u9020\u9875\u7801" in prompt


def test_prepare_history_messages_compacts_long_history() -> None:
    history = [
        ConversationMessage(
            id=f"message-{index}",
            conversation_id="conversation-1",
            role="user" if index % 2 == 0 else "assistant",
            content=f"\u5386\u53f2\u6d88\u606f {index} " * 140,
            created_at=now_utc(),
        )
        for index in range(14)
    ]

    messages = prepare_history_messages(history)

    assert messages[0]["role"] == "system"
    assert "\u88ab\u538b\u7f29\u7684\u8f83\u65e9\u5386\u53f2\u5bf9\u8bdd" in messages[0]["content"]
    assert len(messages) <= 9
    assert messages[-1]["content"].startswith("\u5386\u53f2\u6d88\u606f 13")
