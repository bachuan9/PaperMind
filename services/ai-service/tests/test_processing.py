from pathlib import Path

from app.models import DocumentSummary, ProcessingJob
from app.parser import ParsedPage
from app.processing import process_document
from app.settings import Settings
from app.storage import JsonStore, now_utc


def test_process_document_accepts_document_detail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = JsonStore(tmp_path)
    upload_path = store.save_upload("doc-1", "notes.md", b"hello")
    document = DocumentSummary(
        id="doc-1",
        title="Notes",
        filename="notes.md",
        status="processing",
        created_at=now_utc(),
        updated_at=now_utc(),
        size_bytes=5,
    )
    job = ProcessingJob(
        id="job-1",
        document_id="doc-1",
        status="processing",
        attempts=0,
        max_attempts=1,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    store.save_document(document, [], {})
    store.save_processing_job(job)

    monkeypatch.setattr(
        "app.processing.parse_document",
        lambda _: [ParsedPage(page_number=None, text="Worker parsed text.")],
    )

    detail = store.get_document("doc-1")
    assert detail is not None

    processed = process_document(
        store=store,
        document=detail,
        job=job,
        upload_path=upload_path,
        settings=Settings(ai_data_dir=tmp_path),
    )

    assert processed.status == "ready"
    assert store.get_document("doc-1") is not None
