from pathlib import Path

from fastapi.testclient import TestClient

from app.agent_tools import list_agent_tool_definitions, run_agent_tool
from app.main import app, get_store
from app.models import DocumentChunk, DocumentDetail, DocumentSummary
from app.settings import Settings, get_settings
from app.storage import JsonStore, now_utc


def test_agent_tool_registry_exposes_portfolio_tools() -> None:
    tools = list_agent_tool_definitions()

    assert [tool.name for tool in tools] == [
        "summarize_document",
        "extract_keywords",
        "generate_questions",
        "create_markdown_note",
        "export_outline",
    ]
    assert all(tool.title for tool in tools)


def test_create_markdown_note_tool_returns_structured_output() -> None:
    document = build_document_detail()

    result = run_agent_tool("create_markdown_note", document)

    assert result.tool_name == "create_markdown_note"
    assert result.output_format == "markdown"
    assert "# Agent Notes" in result.content
    assert "学习卡片" in result.content
    assert result.data["study_cards"]
    assert result.citations


def test_run_agent_tool_endpoint_generates_questions(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    document = build_document_summary()
    chunks = build_chunks()
    store.save_document(document, chunks, {})
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        tools = client.get("/agent-tools")
        result = client.post(
            f"/documents/{document.id}/agent-tools/run",
            json={"tool_name": "generate_questions"},
        )

        assert tools.status_code == 200
        assert result.status_code == 200
        assert result.json()["tool_name"] == "generate_questions"
        assert len(result.json()["data"]["questions"]) == 10
        assert "复习题" in result.json()["content"]
    finally:
        app.dependency_overrides.clear()


def test_run_agent_tool_rejects_unprocessed_document(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    document = build_document_summary(status="processing")
    store.save_document(document, [], {})
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        result = client.post(
            f"/documents/{document.id}/agent-tools/run",
            json={"tool_name": "summarize_document"},
        )

        assert result.status_code == 409
        assert result.json()["error"]["code"] == "conflict"
    finally:
        app.dependency_overrides.clear()


def build_document_detail() -> DocumentDetail:
    summary = build_document_summary()
    return DocumentDetail(**summary.model_dump(), chunks=build_chunks())


def build_document_summary(status: str = "ready") -> DocumentSummary:
    return DocumentSummary(
        id="doc-agent",
        title="Agent Notes",
        filename="agent-notes.md",
        status=status,
        created_at=now_utc(),
        updated_at=now_utc(),
        size_bytes=1024,
        page_count=1,
        chunk_count=2,
        summary="Agent tools convert reading into reusable study artifacts.",
    )


def build_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            id="chunk-1",
            document_id="doc-agent",
            index=0,
            text=(
                "Agent tools convert reading into reusable study artifacts. "
                "Summaries, keywords, questions, cards, outlines, citations, "
                "automation, workflows, retrieval, and Markdown notes are core outputs."
            ),
            page_number=1,
        ),
        DocumentChunk(
            id="chunk-2",
            document_id="doc-agent",
            index=1,
            text=(
                "A tool registry keeps each capability explicit and testable. "
                "The document workflow can generate review questions and a presentation outline."
            ),
            page_number=1,
        ),
    ]
