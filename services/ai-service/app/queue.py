import json
from dataclasses import dataclass
from datetime import datetime, timezone


DOCUMENT_QUEUE_NAME = "papermind:document-processing"


class QueueUnavailable(RuntimeError):
    """Raised when the configured Redis queue cannot be reached."""


@dataclass(frozen=True)
class DocumentProcessingTask:
    document_id: str
    enqueued_at: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "document_id": self.document_id,
                "enqueued_at": self.enqueued_at,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, payload: str) -> "DocumentProcessingTask":
        raw_task = json.loads(payload)
        document_id = raw_task.get("document_id")
        enqueued_at = raw_task.get("enqueued_at")
        if not isinstance(document_id, str) or not document_id:
            raise ValueError("document processing task is missing document_id")
        if not isinstance(enqueued_at, str) or not enqueued_at:
            raise ValueError("document processing task is missing enqueued_at")
        return cls(document_id=document_id, enqueued_at=enqueued_at)


class RedisTaskQueue:
    def __init__(
        self,
        *,
        redis_url: str,
        queue_name: str = DOCUMENT_QUEUE_NAME,
    ):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._client = None

    async def enqueue(self, document_id: str) -> DocumentProcessingTask:
        task = DocumentProcessingTask(
            document_id=document_id,
            enqueued_at=datetime.now(timezone.utc).isoformat(),
        )
        client = await self._get_client()
        try:
            await client.rpush(self.queue_name, task.to_json())
        except Exception as error:
            raise QueueUnavailable(f"Redis 入队失败: {error}") from error
        return task

    async def dequeue(
        self,
        *,
        timeout_seconds: int = 5,
    ) -> DocumentProcessingTask | None:
        client = await self._get_client()
        try:
            result = await client.blpop(
                self.queue_name,
                timeout=max(timeout_seconds, 1),
            )
        except Exception as error:
            raise QueueUnavailable(f"Redis 出队失败: {error}") from error
        if result is None:
            return None
        _, payload = result
        return DocumentProcessingTask.from_json(payload)

    async def close(self) -> None:
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None

    async def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import redis.asyncio as redis
        except ImportError as error:
            raise QueueUnavailable(
                "Redis 队列已启用，但 Python redis 依赖未安装"
            ) from error
        self._client = redis.from_url(
            self.redis_url,
            decode_responses=True,
        )
        return self._client
