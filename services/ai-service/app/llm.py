import httpx

from .models import Citation
from .settings import Settings


async def answer_with_model(
    *,
    settings: Settings,
    question: str,
    citations: list[Citation],
) -> str | None:
    if not settings.deepseek_api_key or not citations:
        return None

    context = "\n\n".join(
        f"[引用 {index + 1} | 页码: {citation.page_number or '正文'}]\n{citation.text}"
        for index, citation in enumerate(citations)
    )
    prompt = (
        "你是 PaperMind 的文档问答助手。请只基于给定引用回答用户问题。"
        "如果引用不足以回答，直接说明文档中没有足够依据。"
        "回答后用简短列表标明用到的引用编号，不要伪造页码。\n\n"
        f"用户问题：{question}\n\n"
        f"可用引用：\n{context}"
    )

    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "你严谨、简洁，优先保证回答可溯源。",
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

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
