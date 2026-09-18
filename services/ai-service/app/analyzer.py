import re
from collections import Counter

from .models import DocumentChunk, DocumentInsightResponse, InsightSection
from .retrieval import trim_text


SENTENCE_RE = re.compile(r"(?<=[.!?\u3002\uff01\uff1f])\s+|\n+")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "\u4e00\u4e2a",
    "\u4e0d\u8981",
    "\u4e0d\u80fd",
    "\u4ec0\u4e48",
    "\u4ed6\u4eec",
    "\u4f60\u4eec",
    "\u6211\u4eec",
    "\u8fd9\u4e2a",
    "\u8fd9\u4e9b",
    "\u90a3\u4e2a",
    "\u53ef\u4ee5",
    "\u56e0\u4e3a",
    "\u6240\u4ee5",
    "\u5982\u679c",
    "\u5f53\u524d",
    "\u6587\u6863",
}


def build_document_insights(chunks: list[DocumentChunk]) -> DocumentInsightResponse:
    text = "\n".join(chunk.text for chunk in sorted(chunks, key=lambda item: item.index))
    short_summary = build_summary(text, limit=220, max_sentences=2)
    detailed_summary = build_summary(text, limit=860, max_sentences=8)
    keywords = extract_keywords(text)
    sections = build_sections(chunks)
    questions = build_suggested_questions(keywords, sections)

    return DocumentInsightResponse(
        summary=short_summary,
        short_summary=short_summary,
        detailed_summary=detailed_summary,
        keywords=keywords,
        sections=sections,
        suggested_questions=questions,
        mode="extractive",
    )


def build_summary(text: str, limit: int = 460, max_sentences: int = 4) -> str:
    sentences = [
        clean_sentence(sentence)
        for sentence in SENTENCE_RE.split(text)
        if clean_sentence(sentence)
    ]
    if not sentences:
        return ""

    selected: list[str] = []
    total = 0
    for sentence in sentences:
        if len(sentence) < 8:
            continue
        next_total = total + len(sentence)
        if next_total > limit and selected:
            break
        selected.append(sentence)
        total = next_total
        if len(selected) >= max_sentences:
            break

    if not selected:
        selected = [sentences[0]]
    return trim_text(" ".join(selected), limit)


def extract_keywords(text: str, limit: int = 10) -> list[str]:
    counts: Counter[str] = Counter()
    for token in TOKEN_RE.findall(text.lower()):
        if re.fullmatch(r"\d+", token):
            continue
        if contains_cjk(token):
            for gram in cjk_grams(token):
                if gram not in STOPWORDS:
                    counts[gram] += score_keyword(gram)
        elif token not in STOPWORDS:
            counts[token] += score_keyword(token)

    keywords: list[str] = []
    for keyword, _ in counts.most_common(limit * 3):
        if any(keyword in existing or existing in keyword for existing in keywords):
            continue
        keywords.append(keyword)
        if len(keywords) >= limit:
            break
    return keywords


def build_sections(chunks: list[DocumentChunk], limit: int = 5) -> list[InsightSection]:
    sections: list[InsightSection] = []
    for chunk in sorted(chunks, key=lambda item: item.index)[:limit]:
        source = (
            f"\u7b2c {chunk.page_number} \u9875"
            if chunk.page_number
            else f"\u7247\u6bb5 {chunk.index + 1}"
        )
        title = infer_section_title(chunk.text, source)
        sections.append(
            InsightSection(
                title=title,
                summary=build_summary(chunk.text, limit=220),
            )
        )
    return sections


def build_suggested_questions(
    keywords: list[str],
    sections: list[InsightSection],
    limit: int = 4,
) -> list[str]:
    questions: list[str] = []
    for keyword in keywords[:3]:
        questions.append(
            f"\u6587\u6863\u4e2d\u5173\u4e8e\u300c{keyword}\u300d\u7684\u6838\u5fc3\u89c2\u70b9\u662f\u4ec0\u4e48\uff1f"
        )
    if sections:
        questions.append("\u8bf7\u7528\u66f4\u901a\u4fd7\u7684\u8bdd\u89e3\u91ca\u8fd9\u7bc7\u6587\u6863\u3002")
    questions.append("\u8fd9\u7bc7\u6587\u6863\u6709\u54ea\u4e9b\u53ef\u6267\u884c\u7684\u7ed3\u8bba\uff1f")
    return questions[:limit]


def infer_section_title(text: str, fallback: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip().strip("#").strip()
        if 2 <= len(line) <= 36:
            return line
    return fallback


def clean_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence).strip(" -\t")


def cjk_grams(token: str) -> list[str]:
    if len(token) <= 4:
        return [token]
    grams: list[str] = []
    for size in (4, 3, 2):
        grams.extend(token[index : index + size] for index in range(len(token) - size + 1))
    return grams


def score_keyword(keyword: str) -> float:
    return 1.0 + min(len(keyword), 8) / 8


def contains_cjk(token: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in token)
