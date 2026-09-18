from pathlib import Path
import asyncio

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.engineering import configure_engineering
from app.llm import post_json_with_retries
from app.main import app, get_store
from app.settings import Settings, get_settings
from app.storage import JsonStore


def test_http_errors_use_unified_shape(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store

    try:
        client = TestClient(app)
        response = client.get("/documents/missing-document")

        assert response.status_code == 404
        assert response.headers["x-request-id"]
        assert response.json()["detail"] == "文档不存在"
        assert response.json()["error"]["code"] == "not_found"
    finally:
        app.dependency_overrides.clear()


def test_upload_size_limit_uses_settings(tmp_path: Path) -> None:
    store = JsonStore(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_data_dir=tmp_path,
        ai_max_upload_mb=0,
        deepseek_api_key="",
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/documents",
            files={
                "file": (
                    "too-large.md",
                    b"content",
                    "text/markdown",
                )
            },
        )

        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"
    finally:
        app.dependency_overrides.clear()


def test_rate_limit_middleware_returns_429() -> None:
    test_app = FastAPI()
    configure_engineering(
        test_app,
        Settings(ai_rate_limit_per_minute=1, ai_request_log_enabled=False),
    )

    @test_app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "true"}

    client = TestClient(test_app)
    assert client.get("/ping").status_code == 200
    limited = client.get("/ping")

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert limited.headers["retry-after"]


def test_model_request_retries_server_errors(monkeypatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    original_client = httpx.AsyncClient

    class MockAsyncClient(original_client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, transport=httpx.MockTransport(handler), **kwargs)

    async def run_request() -> dict:
        return await post_json_with_retries(
            settings=Settings(
                deepseek_api_key="sk-test",
                llm_max_retries=1,
                llm_timeout_seconds=1,
            ),
            url="https://example.test/chat/completions",
            headers={},
            payload={},
        )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    data = asyncio.run(run_request())

    assert calls == 2
    assert data["choices"][0]["message"]["content"] == "ok"
