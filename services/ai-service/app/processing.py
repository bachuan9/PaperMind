from pathlib import Path
from uuid import uuid4

from .embeddings import embed_text
from .models import DocumentChunk, DocumentSummary, ProcessingJob
from .parser import ParsedPage, build_summary, chunk_pages, parse_document
from .settings import Settings
from .storage import JsonStore, now_utc


def parse_document_with_retries(
    path: Path,
    *,
    max_attempts: int,
) -> tuple[list[ParsedPage], int]:
    last_error: Exception | None = None
    attempts = max(max_attempts, 1)
    for attempt in range(1, attempts + 1):
        try:
            pages = parse_document(path)
            if not pages:
                raise ValueError("未解析到可用文本")
            return pages, attempt
        except Exception as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise ValueError("未解析到可用文本")


def process_document(
    *,
    store: JsonStore,
    document: DocumentSummary,
    job: ProcessingJob,
    upload_path: Path,
    settings: Settings,
) -> DocumentSummary:
    document = DocumentSummary.model_validate(document.model_dump(exclude={"chunks"}))
    parse_attempts = 0
    try:
        pages, parse_attempts = parse_document_with_retries(
            upload_path,
            max_attempts=job.max_attempts,
        )
        raw_chunks = chunk_pages(pages)
        chunks = [
            DocumentChunk(
                id=str(uuid4()),
                document_id=document.id,
                index=index,
                text=text,
                page_number=page_number,
            )
            for index, (page_number, text) in enumerate(raw_chunks)
        ]
        vectors = {chunk.id: embed_text(chunk.text) for chunk in chunks}
        finished_at = now_utc()
        ready_document = document.model_copy(
            update={
                "status": "ready",
                "updated_at": finished_at,
                "page_count": max(
                    (page.page_number or 1 for page in pages),
                    default=1,
                ),
                "chunk_count": len(chunks),
                "summary": build_summary(pages),
                "error": None,
            }
        )
        finished_job = job.model_copy(
            update={
                "status": "succeeded",
                "attempts": parse_attempts,
                "updated_at": finished_at,
                "finished_at": finished_at,
                "error": None,
            }
        )
    except Exception as error:
        finished_at = now_utc()
        ready_document = document.model_copy(
            update={
                "status": "failed",
                "updated_at": finished_at,
                "error": str(error),
            }
        )
        finished_job = job.model_copy(
            update={
                "status": "failed",
                "attempts": parse_attempts or job.max_attempts,
                "updated_at": finished_at,
                "finished_at": finished_at,
                "error": str(error),
            }
        )
        chunks = []
        vectors = {}

    store.save_processing_job(finished_job)
    return store.save_document(ready_document, chunks, vectors)
