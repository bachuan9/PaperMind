from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal["ready", "failed", "processing"]
MessageRole = Literal["user", "assistant"]


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
    conversation_id: str | None = Field(default=None, max_length=80)


class Citation(BaseModel):
    chunk_id: str
    page_number: int | None = None
    text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    conversation_id: str
    mode: Literal["model", "extractive"]
    provider: str = "local"
    model: str | None = None
    fallback_reason: str | None = None


class Conversation(BaseModel):
    id: str
    document_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationSummary(Conversation):
    message_count: int = 0


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    citations: list[Citation] = Field(default_factory=list)
    mode: Literal["model", "extractive"] | None = None
    provider: str | None = None
    model: str | None = None


class InsightSection(BaseModel):
    title: str
    summary: str


class DocumentInsightResponse(BaseModel):
    summary: str
    short_summary: str
    detailed_summary: str
    keywords: list[str]
    sections: list[InsightSection]
    suggested_questions: list[str]
    mode: Literal["model", "extractive"]


class NoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class DocumentNote(BaseModel):
    id: str
    document_id: str
    content: str
    created_at: datetime
    updated_at: datetime


class ModelStatusResponse(BaseModel):
    provider: str
    model: str
    base_url: str
    configured: bool


class LlmCallLog(BaseModel):
    id: str
    created_at: datetime
    document_id: str
    question_preview: str
    provider: str
    model: str
    mode: Literal["model", "extractive"]
    status: Literal["success", "skipped", "failed"]
    latency_ms: int
    citation_count: int
    error: str | None = None
