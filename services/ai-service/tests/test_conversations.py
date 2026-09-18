from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.llm import ModelAnswerResult
from app.main import app, get_store
from app.parser import ParsedPage
from app.settings import Settings, get_settings
from app.storage import JsonStore


def test_ask_endpoint_creates_conversation_history(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        upload = client.post(
            "/documents",
            files={
                "file": (
                    "notes.md",
                    "\u5f15\u7528\u6eaf\u6e90\u9700\u8981\u5c55\u793a\u539f\u6587\u4f9d\u636e\u3002".encode(),
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["id"]

        answer = client.post(
            f"/documents/{document_id}/ask",
            json={
                "question": "\u4ec0\u4e48\u662f\u5f15\u7528\u6eaf\u6e90",
            },
        )

        assert answer.status_code == 200
        conversation_id = answer.json()["conversation_id"]
        conversations = client.get(f"/documents/{document_id}/conversations")
        messages = client.get(f"/conversations/{conversation_id}/messages")

        assert conversations.status_code == 200
        assert conversations.json()[0]["message_count"] == 2
        assert messages.status_code == 200
        assert [message["role"] for message in messages.json()] == ["user", "assistant"]
    finally:
        app.dependency_overrides.clear()


def test_duplicate_upload_returns_existing_document(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        files = {
            "file": (
                "same-notes.md",
                b"PaperMind stores duplicate uploads only once.",
                "text/markdown",
            )
        }

        first_upload = client.post("/documents", files=files)
        second_upload = client.post("/documents", files=files)
        documents = client.get("/documents")

        assert first_upload.status_code == 200
        assert second_upload.status_code == 200
        assert first_upload.json()["id"] == second_upload.json()["id"]
        assert documents.status_code == 200
        assert len(documents.json()) == 1
    finally:
        app.dependency_overrides.clear()


def test_upload_records_processing_job_and_retries_parse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = JsonStore(tmp_path)
    parse_call_count = 0

    def flaky_parse_document(_: Path) -> list[ParsedPage]:
        nonlocal parse_call_count
        parse_call_count += 1
        if parse_call_count == 1:
            raise ValueError("temporary parse failure")
        return [ParsedPage(page_number=None, text="Retry parsing succeeds.")]

    monkeypatch.setattr("app.main.parse_document", flaky_parse_document)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        ai_parse_max_attempts=2,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        upload = client.post(
            "/documents",
            files={
                "file": (
                    "retry.md",
                    b"Retry parsing succeeds.",
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["id"]
        jobs = client.get(f"/documents/{document_id}/processing-jobs")

        assert upload.json()["status"] == "ready"
        assert parse_call_count == 2
        assert jobs.status_code == 200
        assert jobs.json()[0]["status"] == "succeeded"
        assert jobs.json()[0]["attempts"] == 2
        assert jobs.json()[0]["max_attempts"] == 2
    finally:
        app.dependency_overrides.clear()


def test_upload_records_failed_processing_job_after_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = JsonStore(tmp_path)

    def failing_parse_document(_: Path) -> list[ParsedPage]:
        raise ValueError("permanent parse failure")

    monkeypatch.setattr("app.main.parse_document", failing_parse_document)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        ai_parse_max_attempts=2,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        upload = client.post(
            "/documents",
            files={
                "file": (
                    "broken.md",
                    b"Broken document",
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["id"]
        jobs = client.get(f"/documents/{document_id}/processing-jobs")

        assert upload.json()["status"] == "failed"
        assert jobs.status_code == 200
        assert jobs.json()[0]["status"] == "failed"
        assert jobs.json()[0]["attempts"] == 2
        assert jobs.json()[0]["error"] == "permanent parse failure"
    finally:
        app.dependency_overrides.clear()


def test_ask_endpoint_uses_cached_answer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = JsonStore(tmp_path)
    call_count = 0

    async def fake_answer_with_model(**_: object) -> ModelAnswerResult:
        nonlocal call_count
        call_count += 1
        return ModelAnswerResult(
            answer="Cached model answer",
            status="success",
            latency_ms=15,
            prompt_tokens=20,
            completion_tokens=5,
            total_tokens=25,
            estimated_cost_usd=0.00001,
        )

    monkeypatch.setattr("app.main.answer_with_model", fake_answer_with_model)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        deepseek_api_key="sk-test",
    )

    try:
        client = TestClient(app)
        upload = client.post(
            "/documents",
            files={
                "file": (
                    "rag.md",
                    b"Grounded answers require source citations and original text.",
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["id"]

        first_answer = client.post(
            f"/documents/{document_id}/ask",
            json={"question": "What requires source citations?"},
        )
        second_answer = client.post(
            f"/documents/{document_id}/ask",
            json={"question": "What requires source citations?"},
        )
        logs = client.get("/llm/logs")

        assert first_answer.status_code == 200
        assert second_answer.status_code == 200
        assert first_answer.json()["cache_hit"] is False
        assert second_answer.json()["cache_hit"] is True
        assert first_answer.json()["answer"] == second_answer.json()["answer"]
        assert call_count == 1
        assert logs.status_code == 200
        assert logs.json()[0]["cache_hit"] is True
        assert logs.json()[1]["total_tokens"] == 25
    finally:
        app.dependency_overrides.clear()


def test_notes_endpoint_saves_document_note(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        upload = client.post(
            "/documents",
            files={
                "file": (
                    "notes.md",
                    "\u8fd9\u7bc7\u6587\u6863\u8ba8\u8bba\u9605\u8bfb\u7b14\u8bb0\u3002".encode(),
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["id"]

        created = client.post(
            f"/documents/{document_id}/notes",
            json={"content": "\u9700\u8981\u91cd\u70b9\u590d\u4e60\u5f15\u7528\u6eaf\u6e90"},
        )
        notes = client.get(f"/documents/{document_id}/notes")

        assert created.status_code == 200
        assert notes.status_code == 200
        assert notes.json()[0]["content"] == "\u9700\u8981\u91cd\u70b9\u590d\u4e60\u5f15\u7528\u6eaf\u6e90"
    finally:
        app.dependency_overrides.clear()
