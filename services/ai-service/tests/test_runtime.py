from pathlib import Path

from app.models import (
    ConversationMessage,
    DocumentChunk,
    DocumentNote,
    DocumentSummary,
    LlmCallLog,
    ProcessingJob,
)
from app.runtime import get_model_status
from app.settings import Settings
from app.storage import JsonStore, now_utc


def test_model_status_reflects_deepseek_configuration() -> None:
    settings = Settings(
        deepseek_api_key="sk-test",
        deepseek_base_url="https://api.siliconflow.cn/v1",
        llm_model="deepseek-ai/DeepSeek-V4-Flash",
    )

    status = get_model_status(settings)

    assert status.provider == "SiliconFlow"
    assert status.configured is True
    assert status.model == "deepseek-ai/DeepSeek-V4-Flash"


def test_json_store_persists_llm_logs(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    log = LlmCallLog(
        id="log-1",
        created_at=now_utc(),
        document_id="doc-1",
        question_preview="question",
        provider="local",
        model="deepseek-ai/DeepSeek-V4-Flash",
        mode="extractive",
        status="skipped",
        latency_ms=0,
        citation_count=1,
        error="\u672a\u914d\u7f6e DEEPSEEK_API_KEY",
    )

    store.append_llm_log(log)

    logs = store.list_llm_logs()
    assert len(logs) == 1
    assert logs[0].id == "log-1"
    assert logs[0].error == "\u672a\u914d\u7f6e DEEPSEEK_API_KEY"


def test_json_store_persists_conversations_and_vectors(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    document = DocumentSummary(
        id="doc-1",
        title="RAG Notes",
        filename="rag.md",
        status="ready",
        created_at=now_utc(),
        updated_at=now_utc(),
        size_bytes=100,
        page_count=1,
        chunk_count=1,
        summary="summary",
    )
    chunk = DocumentChunk(
        id="chunk-1",
        document_id="doc-1",
        index=0,
        text="\u5f15\u7528\u6eaf\u6e90",
        page_number=1,
    )

    store.save_document(document, [chunk], {"chunk-1": [0.2, 0.8]})
    store.save_processing_job(
        ProcessingJob(
            id="job-1",
            document_id="doc-1",
            status="succeeded",
            attempts=1,
            max_attempts=1,
            created_at=now_utc(),
            updated_at=now_utc(),
            finished_at=now_utc(),
        )
    )
    conversation = store.create_conversation("doc-1", "\u5f15\u7528\u6eaf\u6e90")
    store.append_message(
        ConversationMessage(
            id="message-1",
            conversation_id=conversation.id,
            role="user",
            content="\u4ec0\u4e48\u662f\u5f15\u7528\u6eaf\u6e90",
            created_at=now_utc(),
        )
    )

    assert store.get_document_vectors("doc-1") == {"chunk-1": [0.2, 0.8]}
    conversations = store.list_conversations("doc-1")
    assert len(conversations) == 1
    assert conversations[0].message_count == 1
    assert store.list_messages(conversation.id)[0].content == "\u4ec0\u4e48\u662f\u5f15\u7528\u6eaf\u6e90"

    assert store.delete_document("doc-1") is True
    assert store.get_document_vectors("doc-1") == {}
    assert store.list_conversations("doc-1") == []
    assert store.list_processing_jobs("doc-1") == []


def test_json_store_persists_document_notes(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    note = DocumentNote(
        id="note-1",
        document_id="doc-1",
        content="\u8fd9\u662f\u4e00\u6761\u9605\u8bfb\u7b14\u8bb0",
        created_at=now_utc(),
        updated_at=now_utc(),
    )

    store.save_note(note)

    notes = store.list_notes("doc-1")
    assert len(notes) == 1
    assert notes[0].content == "\u8fd9\u662f\u4e00\u6761\u9605\u8bfb\u7b14\u8bb0"
