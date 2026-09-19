import asyncio
import logging
from pathlib import Path

from app.models import ProcessingJob
from app.processing import process_document
from app.queue import QueueUnavailable, RedisTaskQueue
from app.settings import get_settings
from app.storage import JsonStore, now_utc


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("papermind.worker")


async def run_worker() -> None:
    settings = get_settings()
    if settings.ai_queue_backend != "redis":
        raise RuntimeError("AI_QUEUE_BACKEND must be redis when starting the worker")

    store = JsonStore(settings.ai_data_dir)
    queue = RedisTaskQueue(
        redis_url=settings.ai_redis_url,
        queue_name=settings.ai_redis_queue_name,
    )
    logger.info("document worker started")

    try:
        while True:
            try:
                task = await queue.dequeue(
                    timeout_seconds=settings.ai_queue_poll_timeout_seconds,
                )
            except QueueUnavailable as error:
                logger.error("%s", error)
                await asyncio.sleep(2)
                continue

            if task is None:
                continue
            process_task(task.document_id, store, settings)
    finally:
        await queue.close()
        logger.info("document worker stopped")


def process_task(document_id: str, store: JsonStore, settings) -> None:
    document = store.get_document(document_id)
    if document is None:
        logger.warning("document %s was removed before processing", document_id)
        return
    if document.status != "processing":
        logger.info("document %s is already %s", document_id, document.status)
        return

    job = get_pending_job(document_id, store)
    if job is None:
        logger.warning("document %s has no pending processing job", document_id)
        return

    started_at = now_utc()
    processing_job = job.model_copy(
        update={
            "status": "processing",
            "updated_at": started_at,
            "started_at": started_at,
        }
    )
    store.save_processing_job(processing_job)
    upload_path = store.upload_dir / (
        f"{document.id}{Path(document.filename).suffix.lower()}"
    )
    logger.info("processing document %s", document_id)
    process_document(
        store=store,
        document=document,
        job=processing_job,
        upload_path=upload_path,
        settings=settings,
    )


def get_pending_job(document_id: str, store: JsonStore) -> ProcessingJob | None:
    jobs = store.list_processing_jobs(document_id)
    for job in jobs:
        if job.status in {"queued", "processing"}:
            return job
    return None


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass
