import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from .models import DocumentChunk, DocumentDetail, DocumentSummary


class JsonStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.upload_dir = data_dir / "uploads"
        self.store_path = data_dir / "store.json"
        self._lock = threading.Lock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._write({"documents": {}, "chunks": {}})

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
    ) -> DocumentSummary:
        with self._lock:
            data = self._read()
            data.setdefault("documents", {})[document.id] = document.model_dump(mode="json")
            data.setdefault("chunks", {})[document.id] = [
                chunk.model_dump(mode="json") for chunk in chunks
            ]
            self._write(data)
        return document

    def delete_document(self, document_id: str) -> bool:
        with self._lock:
            data = self._read()
            existed = document_id in data.get("documents", {})
            data.get("documents", {}).pop(document_id, None)
            data.get("chunks", {}).pop(document_id, None)
            self._write(data)
        return existed

    def save_upload(self, document_id: str, filename: str, content: bytes) -> Path:
        extension = Path(filename).suffix.lower()
        target = self.upload_dir / f"{document_id}{extension}"
        target.write_bytes(content)
        return target

    def _read(self) -> dict:
        try:
            return json.loads(self.store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = self.store_path.with_suffix(f".{now_utc().timestamp():.0f}.broken.json")
            self.store_path.replace(backup)
            self._write({"documents": {}, "chunks": {}})
            return {"documents": {}, "chunks": {}}

    def _write(self, data: dict) -> None:
        self.store_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
