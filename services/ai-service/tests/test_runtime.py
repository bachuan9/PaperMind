from pathlib import Path

from app.models import LlmCallLog
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
