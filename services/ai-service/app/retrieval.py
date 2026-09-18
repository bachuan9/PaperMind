import math
import re
from collections import Counter

from .models import Citation, DocumentChunk


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
VAGUE_CONTEXT_PATTERNS = (
    "\u4ec0\u4e48\u610f\u601d",  # 什么意思
    "\u610f\u601d",  # 意思
    "\u8bb2\u4ec0\u4e48",  # 讲什么
    "\u8bf4\u4ec0\u4e48",  # 说什么
    "\u603b\u7ed3",  # 总结
    "\u6982\u62ec",  # 概括
    "\u89e3\u91ca",  # 解释
    "\u770b\u4e0d\u61c2",  # 看不懂
    "\u8fd9\u6bb5",  # 这段
    "\u8fd9\u4e2a",  # 这个
)


def retrieve(question: str, chunks: list[DocumentChunk], limit: int = 4) -> list[Citation]:
    question_tokens = tokenize(question)
    if not question_tokens:
        return fallback_context(question, chunks, limit)

    scored: list[Citation] = []
    for chunk in chunks:
        score = score_chunk(question_tokens, tokenize(chunk.text))
        if score <= 0:
            continue
        scored.append(
            Citation(
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                text=trim_text(chunk.text, 420),
                score=score,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    if scored:
        return scored[:limit]

    return fallback_context(question, chunks, limit)


def fallback_context(
    question: str,
    chunks: list[DocumentChunk],
    limit: int = 4,
) -> list[Citation]:
    if not chunks or not is_context_question(question):
        return []

    return [
        Citation(
            chunk_id=chunk.id,
            page_number=chunk.page_number,
            text=trim_text(chunk.text, 420),
            score=0.01,
        )
        for chunk in sorted(chunks, key=lambda item: item.index)[:limit]
    ]


def is_context_question(question: str) -> bool:
    compact = re.sub(r"\s+", "", question.lower())
    if not compact:
        return False
    if any(pattern in compact for pattern in VAGUE_CONTEXT_PATTERNS):
        return True
    return len(compact) <= 8 and any(
        token in compact for token in ("\u4ec0\u4e48", "\u600e\u4e48", "\u4e3a\u4ec0\u4e48")
    )


def build_extractive_answer(question: str, citations: list[Citation]) -> str:
    if not citations:
        return (
            "\u6211\u6ca1\u6709\u5728\u5f53\u524d\u6587\u6863\u4e2d\u68c0\u7d22\u5230"
            "\u8db3\u591f\u76f8\u5173\u7684\u539f\u6587\u4f9d\u636e\u3002"
            "\u53ef\u4ee5\u6362\u4e00\u79cd\u95ee\u6cd5\uff0c"
            "\u6216\u786e\u8ba4\u6587\u6863\u662f\u5426\u5df2\u5b8c\u6574\u89e3\u6790\u3002"
        )

    lines = [
        "\u57fa\u4e8e\u5f53\u524d\u6587\u6863\u4e2d\u6700\u76f8\u5173\u7684\u7247\u6bb5\uff0c\u53ef\u4ee5\u5148\u8fd9\u6837\u7406\u89e3\uff1a",
        "",
    ]
    for index, citation in enumerate(citations[:3], start=1):
        source = (
            f"\u7b2c {citation.page_number} \u9875"
            if citation.page_number
            else "\u6b63\u6587\u7247\u6bb5"
        )
        lines.append(f"{index}. {source} \u63d0\u5230\uff1a{citation.text}")

    lines.extend(
        [
            "",
            "\u5982\u679c\u4f60\u60f3\u8981\u66f4\u81ea\u7136\u7684\u89e3\u91ca\u3001\u603b\u7ed3\u6216\u63a8\u7406\uff0c\u9700\u8981\u5728 .env \u4e2d\u914d\u7f6e OPENAI_API_KEY\u3002",
        ]
    )
    return "\n".join(lines)


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if contains_cjk(token) and len(token) > 1:
            expanded.extend(token[index : index + 2] for index in range(len(token) - 1))
    return expanded


def score_chunk(question_tokens: list[str], chunk_tokens: list[str]) -> float:
    if not chunk_tokens:
        return 0.0
    question_counts = Counter(question_tokens)
    chunk_counts = Counter(chunk_tokens)
    overlap = set(question_counts) & set(chunk_counts)
    if not overlap:
        return 0.0
    weighted_overlap = sum(
        min(question_counts[token], chunk_counts[token]) * (1.0 + math.log1p(len(token)))
        for token in overlap
    )
    norm = math.sqrt(len(question_tokens)) * math.sqrt(len(chunk_tokens))
    return round(weighted_overlap / norm * 10, 4)


def trim_text(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


def contains_cjk(token: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in token)
