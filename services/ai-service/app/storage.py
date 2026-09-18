import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import (
    Conversation,
    ConversationMessage,
    ConversationSummary,
    DocumentChunk,
    DocumentDetail,
    DocumentNote,
    DocumentSummary,
    LlmCallLog,
)


class JsonStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.upload_dir = data_dir / "uploads"
        self.store_path = data_dir / "store.json"
        self._lock = threading.Lock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._write(empty_store())

    def list_documents(self) -> list[DocumentSummary]:
        data = self._read()
        documents = [
            DocumentSummary.model_validate(document)
            for document in data.get("documents", {}).values()
        ]
        return sorted(documents, key=lambda item: item.created_at, reverse=True)

    def get_document(self, document_id: str) -> DocumentDetail | None:
        data = self._read()
        raw_document = data.get("documents", {}).get(document_id)
        if raw_document is None:
            return None
        chunks = [
            DocumentChunk.model_validate(chunk)
            for chunk in data.get("chunks", {}).get(document_id, [])
        ]
        return DocumentDetail(**raw_document, chunks=chunks)

    def save_document(
        self,
        document: DocumentSummary,
        chunks: list[DocumentChunk],
        vectors: dict[str, list[float]] | None = None,
    ) -> DocumentSummary:
        with self._lock:
            data = self._read()
            data.setdefault("documents", {})[document.id] = document.model_dump(mode="json")
            data.setdefault("chunks", {})[document.id] = [
                chunk.model_dump(mode="json") for chunk in chunks
            ]
            data.setdefault("vectors", {})[document.id] = vectors or {}
            self._write(data)
        return document

    def get_document_vectors(self, document_id: str) -> dict[str, list[float]]:
        data = self._read()
        raw_vectors = data.get("vectors", {}).get(document_id, {})
        return {
            chunk_id: [float(value) for value in vector]
            for chunk_id, vector in raw_vectors.items()
        }

    def save_document_vectors(
        self,
        document_id: str,
        vectors: dict[str, list[float]],
    ) -> None:
        with self._lock:
            data = self._read()
            if document_id not in data.get("documents", {}):
                return
            data.setdefault("vectors", {})[document_id] = vectors
            self._write(data)

    def delete_document(self, document_id: str) -> bool:
        with self._lock:
            data = self._read()
            existed = document_id in data.get("documents", {})
            data.get("documents", {}).pop(document_id, None)
            data.get("chunks", {}).pop(document_id, None)
            data.get("vectors", {}).pop(document_id, None)
            data.get("notes", {}).pop(document_id, None)
            conversation_ids = [
                conversation_id
                for conversation_id, conversation in data.get("conversations", {}).items()
                if conversation.get("document_id") == document_id
            ]
            for conversation_id in conversation_ids:
                data.get("conversations", {}).pop(conversation_id, None)
                data.get("messages", {}).pop(conversation_id, None)
            self._write(data)
        return existed

    def save_upload(self, document_id: str, filename: str, content: bytes) -> Path:
        extension = Path(filename).suffix.lower()
        target = self.upload_dir / f"{document_id}{extension}"
        target.write_bytes(content)
        return target

    def append_llm_log(self, log: LlmCallLog, limit: int = 100) -> LlmCallLog:
        with self._lock:
            data = self._read()
            logs = data.setdefault("llm_logs", [])
            logs.insert(0, log.model_dump(mode="json"))
            data["llm_logs"] = logs[:limit]
            self._write(data)
        return log

    def list_llm_logs(self, limit: int = 30) -> list[LlmCallLog]:
        data = self._read()
        logs = [
            LlmCallLog.model_validate(item)
            for item in data.get("llm_logs", [])[:limit]
        ]
        return logs

    def create_conversation(self, document_id: str, title: str) -> Conversation:
        conversation = Conversation(
            id=str(uuid4()),
            document_id=document_id,
            title=title,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        with self._lock:
            data = self._read()
            data.setdefault("conversations", {})[conversation.id] = conversation.model_dump(
                mode="json"
            )
            data.setdefault("messages", {})[conversation.id] = []
            self._write(data)
        return conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        data = self._read()
        raw_conversation = data.get("conversations", {}).get(conversation_id)
        if raw_conversation is None:
            return None
        return Conversation.model_validate(raw_conversation)

    def list_conversations(self, document_id: str) -> list[ConversationSummary]:
        data = self._read()
        conversations: list[ConversationSummary] = []
        for raw_conversation in data.get("conversations", {}).values():
            if raw_conversation.get("document_id") != document_id:
                continue
            conversation_id = raw_conversation["id"]
            message_count = len(data.get("messages", {}).get(conversation_id, []))
            conversations.append(
                ConversationSummary(
                    **raw_conversation,
                    message_count=message_count,
                )
            )
        return sorted(
            conversations,
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def append_message(self, message: ConversationMessage) -> ConversationMessage:
        with self._lock:
            data = self._read()
            if message.conversation_id not in data.get("conversations", {}):
                raise KeyError(f"conversation not found: {message.conversation_id}")
            data.setdefault("messages", {}).setdefault(message.conversation_id, []).append(
                message.model_dump(mode="json")
            )
            conversation = data["conversations"][message.conversation_id]
            conversation["updated_at"] = message.created_at.isoformat()
            self._write(data)
        return message

    def list_messages(self, conversation_id: str) -> list[ConversationMessage]:
        data = self._read()
        return [
            ConversationMessage.model_validate(item)
            for item in data.get("messages", {}).get(conversation_id, [])
        ]

    def list_notes(self, document_id: str) -> list[DocumentNote]:
        data = self._read()
        notes = [
            DocumentNote.model_validate(item)
            for item in data.get("notes", {}).get(document_id, [])
        ]
        return sorted(notes, key=lambda item: item.created_at, reverse=True)

    def save_note(self, note: DocumentNote) -> DocumentNote:
        with self._lock:
            data = self._read()
            data.setdefault("notes", {}).setdefault(note.document_id, []).insert(
                0,
                note.model_dump(mode="json"),
            )
            self._write(data)
        return note

    def _read(self) -> dict:
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            for key, default in empty_store().items():
                data.setdefault(key, default.copy() if isinstance(default, dict) else [])
            return data
        except json.JSONDecodeError:
            backup = self.store_path.with_suffix(f".{now_utc().timestamp():.0f}.broken.json")
            self.store_path.replace(backup)
            data = empty_store()
            self._write(data)
            return data

    def _write(self, data: dict) -> None:
        self.store_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def empty_store() -> dict:
    return {
        "documents": {},
        "chunks": {},
        "vectors": {},
        "llm_logs": [],
        "conversations": {},
        "messages": {},
        "notes": {},
    }
