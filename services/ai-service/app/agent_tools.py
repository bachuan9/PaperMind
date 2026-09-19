from dataclasses import dataclass
from typing import Callable

from .analyzer import build_document_insights
from .models import (
    AgentToolDefinition,
    AgentToolName,
    AgentToolResult,
    Citation,
    DocumentChunk,
    DocumentDetail,
    InsightSection,
)
from .retrieval import trim_text
from .storage import now_utc


ToolHandler = Callable[[DocumentDetail], AgentToolResult]


@dataclass(frozen=True)
class AgentToolSpec:
    name: AgentToolName
    title: str
    description: str
    handler: ToolHandler

    def definition(self) -> AgentToolDefinition:
        return AgentToolDefinition(
            name=self.name,
            title=self.title,
            description=self.description,
        )


def list_agent_tool_definitions() -> list[AgentToolDefinition]:
    return [tool.definition() for tool in AGENT_TOOLS]


def run_agent_tool(tool_name: AgentToolName, document: DocumentDetail) -> AgentToolResult:
    return AGENT_TOOLS_BY_NAME[tool_name].handler(document)


def summarize_document(document: DocumentDetail) -> AgentToolResult:
    insights = build_document_insights(document.chunks)
    citations = build_citations(document)
    content = "\n".join(
        [
            f"# {document.title} 摘要",
            "",
            "## 短摘要",
            insights.short_summary or "暂无摘要。",
            "",
            "## 详细摘要",
            insights.detailed_summary or insights.summary or "暂无摘要。",
            "",
            "## 关键依据",
            *citation_lines(citations),
        ]
    )

    return build_result(
        tool_name="summarize_document",
        title="全文摘要",
        content=content,
        data={
            "short_summary": insights.short_summary,
            "detailed_summary": insights.detailed_summary,
            "keywords": insights.keywords,
        },
        citations=citations,
    )


def extract_keywords_tool(document: DocumentDetail) -> AgentToolResult:
    insights = build_document_insights(document.chunks)
    keywords = insights.keywords
    citations = build_citations(document)
    rows = []
    for keyword in keywords:
        evidence = find_keyword_evidence(keyword, document.chunks)
        rows.append(f"- **{keyword}**：{evidence or '文档中的高频主题词。'}")

    content = "\n".join(
        [
            f"# {document.title} 关键术语",
            "",
            *(rows or ["- 暂无可提取关键词。"]),
            "",
            "## 来源片段",
            *citation_lines(citations),
        ]
    )

    return build_result(
        tool_name="extract_keywords",
        title="关键术语",
        content=content,
        data={"keywords": keywords},
        citations=citations,
    )


def generate_questions_tool(document: DocumentDetail) -> AgentToolResult:
    insights = build_document_insights(document.chunks)
    questions = build_review_questions(insights.keywords, insights.sections)
    citations = build_citations(document)
    content = "\n".join(
        [
            f"# {document.title} 复习题",
            "",
            *[f"{index}. {question}" for index, question in enumerate(questions, start=1)],
            "",
            "## 出题依据",
            *citation_lines(citations),
        ]
    )

    return build_result(
        tool_name="generate_questions",
        title="复习题",
        content=content,
        data={"questions": questions},
        citations=citations,
    )


def create_markdown_note(document: DocumentDetail) -> AgentToolResult:
    insights = build_document_insights(document.chunks)
    questions = build_review_questions(insights.keywords, insights.sections, limit=6)
    cards = build_study_cards(insights.keywords, insights.sections)
    citations = build_citations(document, limit=6)
    content = "\n".join(
        [
            f"# {document.title}",
            "",
            "> 由 PaperMind Agent 工具生成。",
            "",
            "## 文档信息",
            f"- 文件名：{document.filename}",
            f"- 页数：{document.page_count or 1}",
            f"- 片段数：{document.chunk_count}",
            "",
            "## 摘要",
            insights.detailed_summary or insights.summary or document.summary or "暂无摘要。",
            "",
            "## 关键术语",
            *[f"- {keyword}" for keyword in insights.keywords],
            "",
            "## 文章提纲",
            *section_lines(insights.sections),
            "",
            "## 复习题",
            *[f"{index}. {question}" for index, question in enumerate(questions, start=1)],
            "",
            "## 学习卡片",
            *study_card_lines(cards),
            "",
            "## 关键摘录",
            *quote_lines(citations),
        ]
    )

    return build_result(
        tool_name="create_markdown_note",
        title="Markdown 笔记",
        content=content,
        data={
            "keywords": insights.keywords,
            "questions": questions,
            "study_cards": cards,
            "sections": [section.model_dump() for section in insights.sections],
        },
        citations=citations,
    )


def export_outline(document: DocumentDetail) -> AgentToolResult:
    insights = build_document_insights(document.chunks)
    outline = build_presentation_outline(document, insights.sections, insights.summary)
    citations = build_citations(document)
    content = "\n".join(
        [
            f"# {document.title} 汇报大纲",
            "",
            *outline_lines(outline),
            "",
            "## 参考来源",
            *citation_lines(citations),
        ]
    )

    return build_result(
        tool_name="export_outline",
        title="汇报大纲",
        content=content,
        data={"outline": outline},
        citations=citations,
    )


def build_result(
    *,
    tool_name: AgentToolName,
    title: str,
    content: str,
    data: dict,
    citations: list[Citation],
) -> AgentToolResult:
    return AgentToolResult(
        tool_name=tool_name,
        title=title,
        content=content,
        data=data,
        citations=citations,
        created_at=now_utc(),
    )


def build_citations(document: DocumentDetail, limit: int = 4) -> list[Citation]:
    citations = []
    for chunk in ordered_chunks(document)[:limit]:
        citations.append(
            Citation(
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                text=trim_text(chunk.text, 360),
                score=1.0,
            )
        )
    return citations


def ordered_chunks(document: DocumentDetail) -> list[DocumentChunk]:
    return sorted(document.chunks, key=lambda item: item.index)


def citation_lines(citations: list[Citation]) -> list[str]:
    if not citations:
        return ["- 暂无可用来源。"]
    return [
        f"- [引用 {index}] {source_label(citation)}：{trim_text(citation.text, 140)}"
        for index, citation in enumerate(citations, start=1)
    ]


def quote_lines(citations: list[Citation]) -> list[str]:
    if not citations:
        return ["暂无摘录。"]
    lines: list[str] = []
    for index, citation in enumerate(citations, start=1):
        lines.extend(
            [
                f"### 引用 {index}：{source_label(citation)}",
                "",
                quote_block(citation.text),
                "",
            ]
        )
    return lines


def source_label(citation: Citation) -> str:
    if citation.page_number:
        return f"第 {citation.page_number} 页"
    return "正文片段"


def find_keyword_evidence(keyword: str, chunks: list[DocumentChunk]) -> str:
    lowered_keyword = keyword.lower()
    for chunk in chunks:
        normalized = " ".join(chunk.text.split())
        if lowered_keyword in normalized.lower():
            return trim_text(normalized, 120)
    return ""


def build_review_questions(
    keywords: list[str],
    sections: list[InsightSection],
    *,
    limit: int = 10,
) -> list[str]:
    questions: list[str] = []
    for keyword in keywords[:5]:
        questions.append(f"文档中关于「{keyword}」的核心观点是什么？")
        questions.append(f"「{keyword}」和全文主题之间有什么关系？")
    for section in sections[:4]:
        questions.append(f"请概括「{section.title}」这一部分的重点。")
    questions.extend(
        [
            "这篇文档主要想解决什么问题？",
            "文档给出了哪些可以直接引用的结论？",
            "哪些内容属于原文事实，哪些只能作为推测？",
            "如果要向别人汇报这篇文档，应该先讲哪三个要点？",
        ]
    )
    return dedupe(questions)[:limit]


def build_study_cards(
    keywords: list[str],
    sections: list[InsightSection],
    *,
    limit: int = 8,
) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for keyword in keywords[:4]:
        cards.append(
            {
                "front": f"什么是「{keyword}」？",
                "back": "结合文档原文解释它的含义、作用和出现的上下文。",
            }
        )
    for section in sections[:4]:
        cards.append(
            {
                "front": f"「{section.title}」的重点是什么？",
                "back": trim_text(section.summary, 180),
            }
        )
    return cards[:limit]


def study_card_lines(cards: list[dict[str, str]]) -> list[str]:
    if not cards:
        return ["暂无学习卡片。"]
    lines: list[str] = []
    for index, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"### 卡片 {index}",
                f"- 正面：{card['front']}",
                f"- 背面：{card['back']}",
                "",
            ]
        )
    return lines


def section_lines(sections: list[InsightSection]) -> list[str]:
    if not sections:
        return ["暂无提纲。"]
    lines: list[str] = []
    for index, section in enumerate(sections, start=1):
        lines.append(f"{index}. {section.title}")
        lines.append(f"   - {section.summary}")
    return lines


def build_presentation_outline(
    document: DocumentDetail,
    sections: list[InsightSection],
    summary: str,
) -> list[dict[str, object]]:
    outline: list[dict[str, object]] = [
        {
            "title": "开场：文档主题",
            "bullets": [
                f"文档：{document.title}",
                trim_text(summary or document.summary or document.filename, 160),
            ],
        }
    ]
    for section in sections[:5]:
        outline.append(
            {
                "title": section.title,
                "bullets": [trim_text(section.summary, 160)],
            }
        )
    outline.append(
        {
            "title": "结尾：可追问问题",
            "bullets": [
                "哪些结论可以直接引用？",
                "哪些信息需要回到原文继续核对？",
            ],
        }
    )
    return outline


def outline_lines(outline: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(outline, start=1):
        lines.append(f"## {index}. {item['title']}")
        for bullet in item.get("bullets", []):
            lines.append(f"- {bullet}")
        lines.append("")
    return lines


def quote_block(value: str) -> str:
    return "\n".join(f"> {line or ' '}" for line in value.splitlines())


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        compact = " ".join(value.split())
        if not compact or compact in seen:
            continue
        seen.add(compact)
        unique.append(compact)
    return unique


AGENT_TOOLS: tuple[AgentToolSpec, ...] = (
    AgentToolSpec(
        name="summarize_document",
        title="全文摘要",
        description="生成短摘要、详细摘要和关键依据。",
        handler=summarize_document,
    ),
    AgentToolSpec(
        name="extract_keywords",
        title="关键术语",
        description="提取关键词并给出对应原文线索。",
        handler=extract_keywords_tool,
    ),
    AgentToolSpec(
        name="generate_questions",
        title="复习题",
        description="生成 10 道可用于复习和面试讲解的问题。",
        handler=generate_questions_tool,
    ),
    AgentToolSpec(
        name="create_markdown_note",
        title="Markdown 笔记",
        description="整理摘要、提纲、复习题、学习卡片和摘录。",
        handler=create_markdown_note,
    ),
    AgentToolSpec(
        name="export_outline",
        title="汇报大纲",
        description="生成适合项目汇报或论文分享的结构化大纲。",
        handler=export_outline,
    ),
)
AGENT_TOOLS_BY_NAME = {tool.name: tool for tool in AGENT_TOOLS}
