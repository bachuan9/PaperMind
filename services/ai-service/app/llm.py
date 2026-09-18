from dataclasses import dataclass
from time import perf_counter

import httpx

from .models import Citation
from .settings import Settings


@dataclass(frozen=True)
class ModelAnswerResult:
    answer: str | None
    status: str
    latency_ms: int
    error: str | None = None


async def answer_with_model(
    *,
    settings: Settings,
    question: str,
    citations: list[Citation],
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

    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "\u4f60\u4e25\u8c28\u3001\u7b80\u6d01\uff0c\u4f18\u5148\u4fdd\u8bc1\u56de\u7b54\u53ef\u6eaf\u6e90\u3002",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

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


def elapsed_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
