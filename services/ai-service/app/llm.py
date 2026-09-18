import json
from dataclasses import dataclass
from time import perf_counter
from typing import AsyncIterator

import httpx
from pydantic import ValidationError

from .models import (
    Citation,
    ConversationMessage,
    DocumentChunk,
    DocumentInsightResponse,
    StructuredInsightPayload,
)
from .settings import Settings


MAX_CONTEXT_CHARS = 7200
MAX_HISTORY_CHARS = 5200
MAX_HISTORY_MESSAGES = 8
MAX_MESSAGE_CHARS = 1200
MAX_INSIGHT_CONTEXT_CHARS = 9000
ANSWER_STRUCTURE = (
    "## 直接回答\n"
    "- 用 2-4 句话回答用户问题。\n"
    "- 如果引用不足以回答，必须明确说“文档中没有足够依据”。\n\n"
    "## 文档依据\n"
    "- 用项目符号列出依据，并标注 [引用 1]、[引用 2] 等编号。\n"
    "- 只允许引用可用引用中的编号，不允许伪造页码或引用。\n\n"
    "## 边界和不确定性\n"
    "- 说明哪些内容是原文事实，哪些只是基于原文的推测。\n"
    "- 如果没有推测，写“无额外推测”。"
)


@dataclass(frozen=True)
class ModelAnswerResult:
    answer: str | None
    status: str
    latency_ms: int
    error: str | None = None


@dataclass(frozen=True)
class ModelInsightResult:
    insights: DocumentInsightResponse | None
    status: str
    latency_ms: int
    error: str | None = None


class ModelStreamError(Exception):
    def __init__(self, message: str, latency_ms: int = 0):
        super().__init__(message)
        self.latency_ms = latency_ms


async def answer_with_model(
    *,
    settings: Settings,
    question: str,
    citations: list[Citation],
    history: list[ConversationMessage] | None = None,
) -> ModelAnswerResult:
    if not settings.deepseek_api_key:
        return ModelAnswerResult(
            answer=None,
            status="skipped",
            latency_ms=0,
            error="\u672a\u914d\u7f6e DEEPSEEK_API_KEY",
        )
    if not citations:
        return ModelAnswerResult(
            answer=None,
            status="skipped",
            latency_ms=0,
            error="\u6ca1\u6709\u53ef\u7528\u5f15\u7528\u7247\u6bb5",
        )

    url, headers, payload = build_chat_request(
        settings=settings,
        question=question,
        citations=citations,
        stream=False,
        history=history,
    )

    started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()
            return ModelAnswerResult(
                answer=answer,
                status="success",
                latency_ms=elapsed_ms(started),
            )
    except httpx.HTTPStatusError as error:
        return ModelAnswerResult(
            answer=None,
            status="failed",
            latency_ms=elapsed_ms(started),
            error=f"\u6a21\u578b\u63a5\u53e3\u8fd4\u56de {error.response.status_code}",
        )
    except httpx.RequestError:
        return ModelAnswerResult(
            answer=None,
            status="failed",
            latency_ms=elapsed_ms(started),
            error="\u6a21\u578b\u63a5\u53e3\u8fde\u63a5\u5931\u8d25",
        )
    except (KeyError, IndexError, TypeError):
        return ModelAnswerResult(
            answer=None,
            status="failed",
            latency_ms=elapsed_ms(started),
            error="\u6a21\u578b\u54cd\u5e94\u683c\u5f0f\u5f02\u5e38",
        )


async def generate_insights_with_model(
    *,
    settings: Settings,
    chunks: list[DocumentChunk],
) -> ModelInsightResult:
    if not settings.deepseek_api_key:
        return ModelInsightResult(
            insights=None,
            status="skipped",
            latency_ms=0,
            error="\u672a\u914d\u7f6e DEEPSEEK_API_KEY",
        )
    if not chunks:
        return ModelInsightResult(
            insights=None,
            status="skipped",
            latency_ms=0,
            error="\u6ca1\u6709\u53ef\u7528\u6587\u6863\u7247\u6bb5",
        )

    url, headers, payload = build_insight_request(settings=settings, chunks=chunks)
    started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            insights = parse_model_insights(content)
            return ModelInsightResult(
                insights=insights,
                status="success",
                latency_ms=elapsed_ms(started),
            )
    except httpx.HTTPStatusError as error:
        return ModelInsightResult(
            insights=None,
            status="failed",
            latency_ms=elapsed_ms(started),
            error=f"\u6a21\u578b\u63a5\u53e3\u8fd4\u56de {error.response.status_code}",
        )
    except httpx.RequestError:
        return ModelInsightResult(
            insights=None,
            status="failed",
            latency_ms=elapsed_ms(started),
            error="\u6a21\u578b\u63a5\u53e3\u8fde\u63a5\u5931\u8d25",
        )
    except (KeyError, IndexError, TypeError, ValueError, ValidationError):
        return ModelInsightResult(
            insights=None,
            status="failed",
            latency_ms=elapsed_ms(started),
            error="\u6a21\u578b\u6d1e\u5bdf\u54cd\u5e94\u7ed3\u6784\u5f02\u5e38",
        )


async def stream_answer_with_model(
    *,
    settings: Settings,
    question: str,
    citations: list[Citation],
    history: list[ConversationMessage] | None = None,
) -> AsyncIterator[str]:
    if not settings.deepseek_api_key:
        raise ModelStreamError("\u672a\u914d\u7f6e DEEPSEEK_API_KEY")
    if not citations:
        raise ModelStreamError("\u6ca1\u6709\u53ef\u7528\u5f15\u7528\u7247\u6bb5")

    url, headers, payload = build_chat_request(
        settings=settings,
        question=question,
        citations=citations,
        stream=True,
        history=history,
    )
    started = perf_counter()

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    token = parse_stream_token(data)
                    if token:
                        yield token
    except httpx.HTTPStatusError as error:
        raise ModelStreamError(
            f"\u6a21\u578b\u63a5\u53e3\u8fd4\u56de {error.response.status_code}",
            elapsed_ms(started),
        ) from error
    except httpx.RequestError as error:
        raise ModelStreamError(
            "\u6a21\u578b\u63a5\u53e3\u8fde\u63a5\u5931\u8d25",
            elapsed_ms(started),
        ) from error


def build_chat_request(
    *,
    settings: Settings,
    question: str,
    citations: list[Citation],
    stream: bool,
    history: list[ConversationMessage] | None = None,
) -> tuple[str, dict[str, str], dict]:
    payload = {
        "model": settings.llm_model,
        "messages": build_messages(
            question=question,
            citations=citations,
            history=history or [],
        ),
        "temperature": 0.2,
        "stream": stream,
    }
    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    return url, headers, payload


def build_messages(
    *,
    question: str,
    citations: list[Citation],
    history: list[ConversationMessage],
) -> list[dict[str, str]]:
    messages = [
        {
            "role": "system",
            "content": (
                "\u4f60\u662f PaperMind \u7684\u6587\u6863\u95ee\u7b54\u52a9\u624b\u3002"
                "\u4f60\u4e25\u8c28\u3001\u7b80\u6d01\uff0c\u4f18\u5148\u4fdd\u8bc1\u56de\u7b54\u53ef\u6eaf\u6e90\u3002"
                "\u6240\u6709\u7ed3\u8bba\u90fd\u5fc5\u987b\u57fa\u4e8e\u5f53\u524d\u63d0\u4f9b\u7684\u6587\u6863\u5f15\u7528\u3002"
            ),
        }
    ]
    messages.extend(prepare_history_messages(history))
    messages.append({"role": "user", "content": build_user_prompt(question, citations)})
    return messages


def build_insight_request(
    *,
    settings: Settings,
    chunks: list[DocumentChunk],
) -> tuple[str, dict[str, str], dict]:
    schema = StructuredInsightPayload.model_json_schema()
    prompt = (
        "\u8bf7\u57fa\u4e8e\u7ed9\u5b9a\u6587\u6863\u7247\u6bb5\u751f\u6210\u7ed3\u6784\u5316\u6587\u6863\u6d1e\u5bdf\u3002"
        "\u4ec5\u8f93\u51fa JSON\uff0c\u4e0d\u8981 Markdown\uff0c\u4e0d\u8981\u989d\u5916\u89e3\u91ca\u3002"
        "\u4e0d\u5f97\u7f16\u9020\u6587\u6863\u4e2d\u6ca1\u6709\u7684\u4fe1\u606f\u3002\n\n"
        "\u8f93\u51fa JSON \u5fc5\u987b\u7b26\u5408\u4ee5\u4e0b JSON Schema\uff1a\n"
        f"{json.dumps(schema, ensure_ascii=False)}\n\n"
        f"\u6587\u6863\u7247\u6bb5\uff1a\n{build_insight_context(chunks)}"
    )
    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "\u4f60\u662f PaperMind \u7684\u7ed3\u6784\u5316\u6587\u6863\u5206\u6790\u52a9\u624b\u3002"
                    "\u4f60\u53ea\u8f93\u51fa\u53ef\u88ab JSON.parse \u89e3\u6790\u7684 JSON \u5bf9\u8c61\u3002"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    return url, headers, payload


def build_insight_context(chunks: list[DocumentChunk]) -> str:
    blocks: list[str] = []
    used_chars = 0
    for chunk in sorted(chunks, key=lambda item: item.index):
        source = f"\u7b2c {chunk.page_number} \u9875" if chunk.page_number else f"\u7247\u6bb5 {chunk.index + 1}"
        text = trim_content(chunk.text, 1000)
        block = f"[{source}]\n{text}"
        if used_chars + len(block) > MAX_INSIGHT_CONTEXT_CHARS and blocks:
            blocks.append("\u2026\u2026\u5176\u4f59\u7247\u6bb5\u5df2\u56e0\u957f\u5ea6\u9650\u5236\u7701\u7565\u3002")
            break
        blocks.append(block)
        used_chars += len(block)
    return "\n\n".join(blocks)


def parse_model_insights(content: str) -> DocumentInsightResponse:
    raw_payload = json.loads(extract_json_object(content))
    payload = StructuredInsightPayload.model_validate(raw_payload)
    return DocumentInsightResponse(
        summary=payload.short_summary,
        short_summary=payload.short_summary,
        detailed_summary=payload.detailed_summary,
        keywords=payload.keywords,
        sections=payload.sections,
        suggested_questions=payload.suggested_questions,
        mode="model",
    )


def extract_json_object(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        stripped = stripped.removesuffix("```").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("JSON object not found")
    return stripped[start : end + 1]


def build_user_prompt(question: str, citations: list[Citation]) -> str:
    return (
        "\u8bf7\u53ea\u57fa\u4e8e\u7ed9\u5b9a\u5f15\u7528\u56de\u7b54\u7528\u6237\u95ee\u9898\u3002"
        "\u5982\u679c\u5f15\u7528\u4e0d\u8db3\u4ee5\u56de\u7b54\uff0c"
        "\u5fc5\u987b\u660e\u786e\u8bf4\u660e\u6587\u6863\u4e2d\u6ca1\u6709\u8db3\u591f\u4f9d\u636e\u3002"
        "\u4e0d\u8981\u4f2a\u9020\u9875\u7801\u3001\u539f\u6587\u6216\u5f15\u7528\u7f16\u53f7\u3002"
        "\u5982\u9700\u8981\u63a8\u6d4b\uff0c\u5fc5\u987b\u653e\u5728\u201c\u8fb9\u754c\u548c\u4e0d\u786e\u5b9a\u6027\u201d\u4e2d\u3002\n\n"
        "\u8bf7\u4e25\u683c\u6309\u4ee5\u4e0b\u7ed3\u6784\u8f93\u51fa\uff1a\n"
        f"{ANSWER_STRUCTURE}\n\n"
        f"\u7528\u6237\u95ee\u9898\uff1a{question}\n\n"
        f"\u53ef\u7528\u5f15\u7528\uff1a\n{build_context(citations)}"
    )


def build_context(citations: list[Citation]) -> str:
    blocks: list[str] = []
    used_chars = 0
    for index, citation in enumerate(citations, start=1):
        source = citation.page_number or "\u6b63\u6587"
        text = trim_content(citation.text, 1100)
        block = f"[\u5f15\u7528 {index} | \u9875\u7801: {source}]\n{text}"
        if used_chars + len(block) > MAX_CONTEXT_CHARS and blocks:
            blocks.append("\u2026\u2026\u5176\u4f59\u5f15\u7528\u5df2\u56e0\u957f\u5ea6\u9650\u5236\u7701\u7565\u3002")
            break
        blocks.append(block)
        used_chars += len(block)
    return "\n\n".join(blocks)


def prepare_history_messages(
    history: list[ConversationMessage],
) -> list[dict[str, str]]:
    selected: list[ConversationMessage] = []
    used_chars = 0
    for message in reversed(history):
        content = trim_content(message.content, MAX_MESSAGE_CHARS)
        next_total = used_chars + len(content)
        if len(selected) >= MAX_HISTORY_MESSAGES or next_total > MAX_HISTORY_CHARS:
            break
        selected.append(message)
        used_chars = next_total

    selected.reverse()
    selected_ids = {message.id for message in selected}
    omitted = [message for message in history if message.id not in selected_ids]

    messages: list[dict[str, str]] = []
    if omitted:
        messages.append(
            {
                "role": "system",
                "content": build_history_summary(omitted),
            }
        )
    messages.extend(
        {
            "role": message.role,
            "content": trim_content(message.content, MAX_MESSAGE_CHARS),
        }
        for message in selected
    )
    return messages


def build_history_summary(messages: list[ConversationMessage]) -> str:
    lines = [
        f"\u4ee5\u4e0b\u662f\u88ab\u538b\u7f29\u7684\u8f83\u65e9\u5386\u53f2\u5bf9\u8bdd\uff0c\u5171 {len(messages)} \u6761\uff1a"
    ]
    for message in messages[-6:]:
        role = "\u7528\u6237" if message.role == "user" else "\u52a9\u624b"
        lines.append(f"- {role}\uff1a{trim_content(message.content, 180)}")
    return trim_content("\n".join(lines), 1400)


def trim_content(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "\u2026"


def parse_stream_token(data: str) -> str:
    try:
        payload = json.loads(data)
        return payload["choices"][0].get("delta", {}).get("content", "")
    except (KeyError, IndexError, TypeError, ValueError):
        return ""


def elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
