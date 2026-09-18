from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal["ready", "failed", "processing"]


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    index: int
    text: str
    page_number: int | None = None


class DocumentSummary(BaseModel):
    id: str
    title: str
    filename: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    size_bytes: int
    page_count: int = 0
    chunk_count: int = 0
    summary: str = ""
    error: str | None = None


class DocumentDetail(DocumentSummary):
    chunks: list[DocumentChunk] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1200)


class Citation(BaseModel):
    chunk_id: str
    page_number: int | None = None
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    mode: Literal["model", "extractive"]
