from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, get_store
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
