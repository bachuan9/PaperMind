import pytest

from app.queue import DocumentProcessingTask


def test_document_processing_task_round_trips_json() -> None:
    task = DocumentProcessingTask(
        document_id="doc-1",
        enqueued_at="2026-09-19T00:00:00+00:00",
    )

    parsed = DocumentProcessingTask.from_json(task.to_json())

    assert parsed == task


def test_document_processing_task_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError):
        DocumentProcessingTask.from_json("{}")
