import pytest
from pydantic import ValidationError

from app.llm import (
    build_chat_request,
    build_insight_request,
    parse_model_insights,
    parse_stream_token,
    prepare_history_messages,
    token_usage_from_response,
)
from app.models import Citation, ConversationMessage, DocumentChunk
from app.settings import Settings
from app.storage import now_utc


def test_parse_stream_token_reads_delta_content() -> None:
    data = '{"choices":[{"delta":{"content":"hello"}}]}'

    assert parse_stream_token(data) == "hello"


def test_parse_stream_token_ignores_invalid_payload() -> None:
    assert parse_stream_token("{}") == ""


def test_token_usage_from_response_reads_provider_usage() -> None:
    usage = token_usage_from_response(
        data={
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 40,
                "total_tokens": 140,
            }
        },
        settings=Settings(
            llm_input_price_per_1m_tokens=2,
            llm_output_price_per_1m_tokens=4,
        ),
        payload={"messages": [{"content": "hello"}]},
        completion_text="world",
    )

    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 40
    assert usage.total_tokens == 140
    assert usage.estimated_cost_usd == 0.00036


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


def test_build_chat_request_compacts_long_history_before_model_call() -> None:
    history = [
        ConversationMessage(
            id=f"message-{index}",
            conversation_id="conversation-1",
            role="user" if index % 2 == 0 else "assistant",
            content=f"long history message {index} " * 160,
            created_at=now_utc(),
        )
        for index in range(18)
    ]

    _, _, payload = build_chat_request(
        settings=Settings(deepseek_api_key="sk-test"),
        question="What remains in context?",
        citations=[
            Citation(
                chunk_id="chunk-1",
                page_number=1,
                text="Only bounded history should be sent with retrieved evidence.",
                score=0.9,
            )
        ],
        stream=False,
        history=history,
    )

    messages = payload["messages"]
    history_messages = messages[1:-1]
    payload_text = "\n".join(message["content"] for message in messages)

    assert messages[0]["role"] == "system"
    assert history_messages[0]["role"] == "system"
    assert "\u88ab\u538b\u7f29\u7684\u8f83\u65e9\u5386\u53f2\u5bf9\u8bdd" in history_messages[0]["content"]
    assert len(history_messages) <= 9
    assert "What remains in context?" in messages[-1]["content"]
    assert len(payload_text) < 9000


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


def test_build_insight_request_includes_json_schema() -> None:
    _, _, payload = build_insight_request(
        settings=Settings(deepseek_api_key="sk-test"),
        chunks=[
            DocumentChunk(
                id="chunk-1",
                document_id="doc-1",
                index=0,
                text="\u6587\u6863\u9700\u8981\u7ed3\u6784\u5316\u6d1e\u5bdf\u3002",
                page_number=1,
            )
        ],
    )

    prompt = payload["messages"][-1]["content"]
    assert payload["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in prompt
    assert "short_summary" in prompt
    assert "detailed_summary" in prompt


def test_parse_model_insights_validates_payload() -> None:
    insights = parse_model_insights(
        """
        ```json
        {
          "short_summary": "文档介绍结构化洞察。",
          "detailed_summary": "文档介绍结构化洞察，并要求输出稳定 JSON。",
          "keywords": ["结构化输出", "JSON"],
          "sections": [{"title": "洞察", "summary": "说明结构化洞察。"}],
          "suggested_questions": ["为什么需要结构化输出？"]
        }
        ```
        """
    )

    assert insights.mode == "model"
    assert insights.summary == "文档介绍结构化洞察。"
    assert insights.sections[0].title == "洞察"


def test_parse_model_insights_rejects_invalid_payload() -> None:
    with pytest.raises(ValidationError):
        parse_model_insights('{"short_summary": "缺字段"}')
