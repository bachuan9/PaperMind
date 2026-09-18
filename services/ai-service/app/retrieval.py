import math
import re
from collections import Counter

from .embeddings import cosine_similarity, embed_text
from .models import Citation, DocumentChunk


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?\u3002\uff01\uff1f])\s*|\n+")
VAGUE_CONTEXT_PATTERNS = (
    "\u4ec0\u4e48\u610f\u601d",
    "\u610f\u601d",
    "\u8bb2\u4ec0\u4e48",
    "\u8bf4\u4ec0\u4e48",
    "\u603b\u7ed3",
    "\u6982\u62ec",
    "\u89e3\u91ca",
    "\u770b\u4e0d\u61c2",
    "\u8fd9\u6bb5",
    "\u8fd9\u4e2a",
)


def retrieve(
    question: str,
    chunks: list[DocumentChunk],
    limit: int = 4,
    vectors: dict[str, list[float]] | None = None,
) -> list[Citation]:
    question_tokens = tokenize(question)
    if not question_tokens:
        return fallback_context(question, chunks, limit)

    query_vector = embed_text(question)
    stored_vectors = vectors or {}
    scored: list[Citation] = []
    for chunk in chunks:
        lexical_score = score_chunk(question_tokens, tokenize(chunk.text))
        vector = stored_vectors.get(chunk.id) or embed_text(chunk.text)
        vector_score = cosine_similarity(query_vector, vector)
        if lexical_score <= 0 and vector_score <= 0:
            continue
        score = round(
            (max(vector_score, 0.0) * 0.7)
            + (min(lexical_score / 10, 1.0) * 0.3),
            4,
        )
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
        token in compact
        for token in ("\u4ec0\u4e48", "\u600e\u4e48", "\u4e3a\u4ec0\u4e48")
    )


def build_extractive_answer(question: str, citations: list[Citation]) -> str:
    if not citations:
        return (
            "\u6211\u6ca1\u6709\u5728\u5f53\u524d\u6587\u6863\u4e2d\u68c0\u7d22\u5230"
            "\u8db3\u591f\u76f8\u5173\u7684\u539f\u6587\u4f9d\u636e\u3002"
            "\u53ef\u4ee5\u6362\u4e00\u79cd\u95ee\u6cd5\uff0c"
            "\u6216\u786e\u8ba4\u6587\u6863\u662f\u5426\u5df2\u5b8c\u6574\u89e3\u6790\u3002"
        )

    if is_context_question(question):
        return build_plain_explanation(citations)

    lines = [
        "\u57fa\u4e8e\u5f53\u524d\u6587\u6863\u4e2d\u6700\u76f8\u5173\u7684\u7247\u6bb5\uff0c\u53ef\u4ee5\u5148\u8fd9\u6837\u7406\u89e3\uff1a",
        "",
    ]
    for index, citation in enumerate(citations[:3], start=1):
        source = format_source(citation)
        lines.append(f"{index}. {source} \u63d0\u5230\uff1a{trim_text(citation.text, 220)}")

    lines.extend(
        [
            "",
            "\u5982\u679c\u4f60\u60f3\u8981\u66f4\u81ea\u7136\u7684\u89e3\u91ca\u3001\u603b\u7ed3\u6216\u63a8\u7406\uff0c\u9700\u8981\u5728 .env \u4e2d\u914d\u7f6e DEEPSEEK_API_KEY\u3002",
        ]
    )
    return "\n".join(lines)


def build_plain_explanation(citations: list[Citation]) -> str:
    points = extract_explanation_points(citations)
    summary = points[0] if points else citations[0].text

    lines = [
        f"\u7b80\u5355\u8bf4\uff0c\u8fd9\u7bc7\u6587\u6863\u4e3b\u8981\u662f\u5728\u8bf4\uff1a{trim_text(summary, 130)}",
        "",
        "\u53ef\u4ee5\u62c6\u6210\u51e0\u4e2a\u8981\u70b9\uff1a",
    ]
    for index, point in enumerate(points[:3], start=1):
        lines.append(f"{index}. {trim_text(point, 110)}")

    lines.extend(["", "\u5f15\u7528\u4f9d\u636e\uff1a"])
    for citation in citations[:2]:
        lines.append(f"- {format_source(citation)}\uff1a{trim_text(citation.text, 120)}")

    lines.extend(
        [
            "",
            "\u5f53\u524d\u4e3a\u65e0\u6a21\u578b Key \u7684\u672c\u5730\u89e3\u91ca\u6a21\u5f0f\uff0c\u6240\u4ee5\u6211\u4f1a\u5c3d\u91cf\u57fa\u4e8e\u539f\u6587\u63d0\u70bc\uff0c\u4e0d\u4f1a\u6269\u5c55\u539f\u6587\u5916\u7684\u63a8\u65ad\u3002",
        ]
    )
    return "\n".join(lines)


def extract_explanation_points(citations: list[Citation], limit: int = 4) -> list[str]:
    points: list[str] = []
    for citation in citations:
        for sentence in split_sentences(citation.text):
            if is_low_value_sentence(sentence):
                continue
            if any(sentence in point or point in sentence for point in points):
                continue
            points.append(sentence)
            if len(points) >= limit:
                return points
    return points


def split_sentences(text: str) -> list[str]:
    cleaned = text.replace("#", " ")
    raw_sentences = SENTENCE_RE.split(cleaned)
    sentences: list[str] = []
    for raw_sentence in raw_sentences:
        sentence = re.sub(r"\s+", " ", raw_sentence).strip(" -\t")
        if not sentence:
            continue
        if len(sentence) > 180:
            sentences.extend(split_long_sentence(sentence))
        else:
            sentences.append(sentence)
    return sentences


def split_long_sentence(sentence: str) -> list[str]:
    normalized = sentence
    for separator in (";", ",", "\uff0c", "\uff1b"):
        normalized = normalized.replace(separator, "|")
    return [
        part.strip(" -\t")
        for part in normalized.split("|")
        if len(part.strip(" -\t")) >= 8
    ]


def is_low_value_sentence(sentence: str) -> bool:
    compact = re.sub(r"\s+", "", sentence)
    if len(compact) < 8:
        return True
    if re.fullmatch(r"[\W_]+", compact):
        return True
    return False


def format_source(citation: Citation) -> str:
    if citation.page_number:
        return f"\u7b2c {citation.page_number} \u9875"
    return "\u6b63\u6587\u7247\u6bb5"


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
