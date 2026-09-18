import json
from dataclasses import dataclass
from time import perf_counter
from typing import AsyncIterator

import httpx

from .models import Citation, ConversationMessage
from .settings import Settings


@dataclass(frozen=True)
class ModelAnswerResult:
    answer: str | None
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
    context = "\n\n".join(
        f"[\u5f15\u7528 {index + 1} | \u9875\u7801: {citation.page_number or '\u6b63\u6587'}]\n{citation.text}"
        for index, citation in enumerate(citations)
    )
    prompt = (
        "\u4f60\u662f PaperMind \u7684\u6587\u6863\u95ee\u7b54\u52a9\u624b\u3002"
        "\u8bf7\u53ea\u57fa\u4e8e\u7ed9\u5b9a\u5f15\u7528\u56de\u7b54\u7528\u6237\u95ee\u9898\u3002"
        "\u5982\u679c\u5f15\u7528\u4e0d\u8db3\u4ee5\u56de\u7b54\uff0c"
        "\u76f4\u63a5\u8bf4\u660e\u6587\u6863\u4e2d\u6ca1\u6709\u8db3\u591f\u4f9d\u636e\u3002"
        "\u56de\u7b54\u540e\u7528\u7b80\u77ed\u5217\u8868\u6807\u660e\u7528\u5230\u7684\u5f15\u7528\u7f16\u53f7\uff0c"
        "\u4e0d\u8981\u4f2a\u9020\u9875\u7801\u3002\n\n"
        f"\u7528\u6237\u95ee\u9898\uff1a{question}\n\n"
        f"\u53ef\u7528\u5f15\u7528\uff1a\n{context}"
    )
    messages = [
        {
            "role": "system",
            "content": "\u4f60\u4e25\u8c28\u3001\u7b80\u6d01\uff0c\u4f18\u5148\u4fdd\u8bc1\u56de\u7b54\u53ef\u6eaf\u6e90\u3002",
        }
    ]
    for message in (history or [])[-8:]:
        messages.append(
            {
                "role": message.role,
                "content": message.content[:4000],
            }
        )
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.2,
        "stream": stream,
    }
    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    return url, headers, payload


def parse_stream_token(data: str) -> str:
    try:
        payload = json.loads(data)
        return payload["choices"][0].get("delta", {}).get("content", "")
    except (KeyError, IndexError, TypeError, ValueError):
        return ""


def elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
