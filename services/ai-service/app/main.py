import json
from pathlib import Path
from time import perf_counter
from typing import AsyncIterator
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .analyzer import build_document_insights
from .embeddings import embed_text
from .llm import ModelStreamError, answer_with_model, elapsed_ms, stream_answer_with_model
from .models import (
    AskRequest,
    AskResponse,
    Conversation,
    ConversationMessage,
    ConversationSummary,
    DocumentChunk,
    DocumentDetail,
    DocumentInsightResponse,
    DocumentNote,
    DocumentSummary,
    LlmCallLog,
    ModelStatusResponse,
    NoteRequest,
)
from .parser import build_summary, chunk_pages, parse_document, validate_extension
from .retrieval import build_extractive_answer, retrieve
from .runtime import get_model_status
from .settings import Settings, get_settings
from .storage import JsonStore, now_utc


def get_store(settings: Settings = Depends(get_settings)) -> JsonStore:
    return JsonStore(settings.ai_data_dir)


settings = get_settings()
app = FastAPI(title="PaperMind AI Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model/status", response_model=ModelStatusResponse)
def model_status(settings: Settings = Depends(get_settings)) -> ModelStatusResponse:
    return get_model_status(settings)


@app.get("/llm/logs", response_model=list[LlmCallLog])
def list_llm_logs(store: JsonStore = Depends(get_store)) -> list[LlmCallLog]:
    return store.list_llm_logs()


@app.get("/documents", response_model=list[DocumentSummary])
def list_documents(store: JsonStore = Depends(get_store)) -> list[DocumentSummary]:
    return store.list_documents()


@app.post("/documents", response_model=DocumentSummary)
async def create_document(
    file: UploadFile = File(...),
    store: JsonStore = Depends(get_store),
) -> DocumentSummary:
    filename = file.filename or "document"
    try:
        validate_extension(filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件不能超过 25MB")

    document_id = str(uuid4())
    now = now_utc()
    title = Path(filename).stem or "Untitled"
    upload_path = store.save_upload(document_id, filename, content)

    try:
        pages = parse_document(upload_path)
        if not pages:
            raise ValueError("未解析到可用文本")
        raw_chunks = chunk_pages(pages)
        chunks = [
            DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                index=index,
                text=text,
                page_number=page_number,
            )
            for index, (page_number, text) in enumerate(raw_chunks)
        ]
        vectors = {chunk.id: embed_text(chunk.text) for chunk in chunks}
        document = DocumentSummary(
            id=document_id,
            title=title,
            filename=filename,
            status="ready",
            created_at=now,
            updated_at=now_utc(),
            size_bytes=len(content),
            page_count=max((page.page_number or 1 for page in pages), default=1),
            chunk_count=len(chunks),
            summary=build_summary(pages),
        )
    except Exception as error:
        document = DocumentSummary(
            id=document_id,
            title=title,
            filename=filename,
            status="failed",
            created_at=now,
            updated_at=now_utc(),
            size_bytes=len(content),
            error=str(error),
        )
        chunks = []
        vectors = {}

    return store.save_document(document, chunks, vectors)


@app.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    store: JsonStore = Depends(get_store),
) -> DocumentDetail:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@app.get("/documents/{document_id}/insights", response_model=DocumentInsightResponse)
def get_document_insights(
    document_id: str,
    store: JsonStore = Depends(get_store),
) -> DocumentInsightResponse:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status != "ready":
        raise HTTPException(status_code=409, detail="文档尚未解析完成")
    return build_document_insights(document.chunks)


@app.get("/documents/{document_id}/notes", response_model=list[DocumentNote])
def list_document_notes(
    document_id: str,
    store: JsonStore = Depends(get_store),
) -> list[DocumentNote]:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return store.list_notes(document_id)


@app.post("/documents/{document_id}/notes", response_model=DocumentNote)
def create_document_note(
    document_id: str,
    request: NoteRequest,
    store: JsonStore = Depends(get_store),
) -> DocumentNote:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="笔记内容不能为空")
    now = now_utc()
    note = DocumentNote(
        id=str(uuid4()),
        document_id=document_id,
        content=content,
        created_at=now,
        updated_at=now,
    )
    return store.save_note(note)


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    store: JsonStore = Depends(get_store),
) -> dict[str, bool]:
    deleted = store.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True}


@app.get(
    "/documents/{document_id}/conversations",
    response_model=list[ConversationSummary],
)
def list_document_conversations(
    document_id: str,
    store: JsonStore = Depends(get_store),
) -> list[ConversationSummary]:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return store.list_conversations(document_id)


@app.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ConversationMessage],
)
def list_conversation_messages(
    conversation_id: str,
    store: JsonStore = Depends(get_store),
) -> list[ConversationMessage]:
    conversation = store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return store.list_messages(conversation_id)


@app.post("/documents/{document_id}/ask", response_model=AskResponse)
async def ask_document(
    document_id: str,
    request: AskRequest,
    settings: Settings = Depends(get_settings),
    store: JsonStore = Depends(get_store),
) -> AskResponse:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status != "ready":
        raise HTTPException(status_code=409, detail="文档尚未解析完成")

    conversation, history = prepare_conversation(
        store=store,
        document_id=document_id,
        question=request.question,
        conversation_id=request.conversation_id,
    )
    citations = retrieve(
        request.question,
        document.chunks,
        vectors=load_document_vectors(store, document_id, document.chunks),
    )
    model_result = await answer_with_model(
        settings=settings,
        question=request.question,
        citations=citations,
        history=history,
    )
    if model_result.answer:
        store.append_message(
            build_assistant_message(
                conversation_id=conversation.id,
                content=model_result.answer,
                citations=citations,
                mode="model",
                provider="SiliconFlow",
                model=settings.llm_model,
            )
        )
        store.append_llm_log(
            build_llm_log(
                document_id=document_id,
                question=request.question,
                settings=settings,
                mode="model",
                status=model_result.status,
                latency_ms=model_result.latency_ms,
                citation_count=len(citations),
                error=None,
            )
        )
        return AskResponse(
            answer=model_result.answer,
            citations=citations,
            conversation_id=conversation.id,
            mode="model",
            provider="SiliconFlow",
            model=settings.llm_model,
        )

    fallback_answer = build_extractive_answer(request.question, citations)
    store.append_message(
        build_assistant_message(
            conversation_id=conversation.id,
            content=fallback_answer,
            citations=citations,
            mode="extractive",
            provider="local",
            model=None,
        )
    )
    store.append_llm_log(
        build_llm_log(
            document_id=document_id,
            question=request.question,
            settings=settings,
            mode="extractive",
            status=model_result.status,
            latency_ms=model_result.latency_ms,
            citation_count=len(citations),
            error=model_result.error,
        )
    )
    return AskResponse(
        answer=fallback_answer,
        citations=citations,
        conversation_id=conversation.id,
        mode="extractive",
        provider="local",
        model=None,
        fallback_reason=model_result.error,
    )


@app.post("/documents/{document_id}/ask/stream")
async def ask_document_stream(
    document_id: str,
    request: AskRequest,
    settings: Settings = Depends(get_settings),
    store: JsonStore = Depends(get_store),
) -> StreamingResponse:
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status != "ready":
        raise HTTPException(status_code=409, detail="文档尚未解析完成")

    conversation, history = prepare_conversation(
        store=store,
        document_id=document_id,
        question=request.question,
        conversation_id=request.conversation_id,
    )
    citations = retrieve(
        request.question,
        document.chunks,
        vectors=load_document_vectors(store, document_id, document.chunks),
    )

    return StreamingResponse(
        stream_answer_events(
            document_id=document_id,
            question=request.question,
            citations=citations,
            conversation_id=conversation.id,
            history=history,
            settings=settings,
            store=store,
        ),
        media_type="application/x-ndjson",
    )


def build_llm_log(
    *,
    document_id: str,
    question: str,
    settings: Settings,
    mode: str,
    status: str,
    latency_ms: int,
    citation_count: int,
    error: str | None,
) -> LlmCallLog:
    return LlmCallLog(
        id=str(uuid4()),
        created_at=now_utc(),
        document_id=document_id,
        question_preview=question[:120],
        provider="SiliconFlow" if mode == "model" else "local",
        model=settings.llm_model,
        mode=mode,
        status=status,
        latency_ms=latency_ms,
        citation_count=citation_count,
        error=error,
    )


def load_document_vectors(
    store: JsonStore,
    document_id: str,
    chunks: list[DocumentChunk],
) -> dict[str, list[float]]:
    vectors = store.get_document_vectors(document_id)
    missing_vectors = {
        chunk.id: embed_text(chunk.text)
        for chunk in chunks
        if chunk.id not in vectors
    }
    if missing_vectors:
        vectors.update(missing_vectors)
        store.save_document_vectors(document_id, vectors)
    return vectors


def prepare_conversation(
    *,
    store: JsonStore,
    document_id: str,
    question: str,
    conversation_id: str | None,
) -> tuple[Conversation, list[ConversationMessage]]:
    if conversation_id:
        conversation = store.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        if conversation.document_id != document_id:
            raise HTTPException(status_code=400, detail="会话不属于当前文档")
    else:
        title = " ".join(question.split()).strip()[:80] or "新对话"
        conversation = store.create_conversation(document_id, title)

    history = store.list_messages(conversation.id)
    store.append_message(
        ConversationMessage(
            id=str(uuid4()),
            conversation_id=conversation.id,
            role="user",
            content=question,
            created_at=now_utc(),
        )
    )
    return conversation, history


def build_assistant_message(
    *,
    conversation_id: str,
    content: str,
    citations: list,
    mode: str,
    provider: str,
    model: str | None,
) -> ConversationMessage:
    return ConversationMessage(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        created_at=now_utc(),
        citations=citations,
        mode=mode,
        provider=provider,
        model=model,
    )


async def stream_answer_events(
    *,
    document_id: str,
    question: str,
    citations: list,
    conversation_id: str,
    history: list[ConversationMessage],
    settings: Settings,
    store: JsonStore,
) -> AsyncIterator[str]:
    if not settings.deepseek_api_key or not citations:
        reason = (
            "\u672a\u914d\u7f6e DEEPSEEK_API_KEY"
            if not settings.deepseek_api_key
            else "\u6ca1\u6709\u53ef\u7528\u5f15\u7528\u7247\u6bb5"
        )
        fallback_answer = build_extractive_answer(question, citations)
        store.append_message(
            build_assistant_message(
                conversation_id=conversation_id,
                content=fallback_answer,
                citations=citations,
                mode="extractive",
                provider="local",
                model=None,
            )
        )
        store.append_llm_log(
            build_llm_log(
                document_id=document_id,
                question=question,
                settings=settings,
                mode="extractive",
                status="skipped",
                latency_ms=0,
                citation_count=len(citations),
                error=reason,
            )
        )
        async for event in stream_fallback_answer(
            conversation_id=conversation_id,
            answer=fallback_answer,
            citations=citations,
            reason=reason,
        ):
            yield event
        return

    started = perf_counter()
    chunks: list[str] = []
    yield stream_event(
        "meta",
        {
            "conversation_id": conversation_id,
            "mode": "model",
            "provider": "SiliconFlow",
            "model": settings.llm_model,
            "fallback_reason": None,
            "citations": [citation.model_dump() for citation in citations],
        },
    )
    try:
        async for token in stream_answer_with_model(
            settings=settings,
            question=question,
            citations=citations,
            history=history,
        ):
            chunks.append(token)
            yield stream_event("token", {"token": token})
        answer = "".join(chunks)
        store.append_message(
            build_assistant_message(
                conversation_id=conversation_id,
                content=answer,
                citations=citations,
                mode="model",
                provider="SiliconFlow",
                model=settings.llm_model,
            )
        )
        store.append_llm_log(
            build_llm_log(
                document_id=document_id,
                question=question,
                settings=settings,
                mode="model",
                status="success",
                latency_ms=elapsed_ms(started),
                citation_count=len(citations),
                error=None,
            )
        )
        yield stream_event("done", {"answer": answer})
    except ModelStreamError as error:
        fallback_answer = build_extractive_answer(question, citations)
        store.append_message(
            build_assistant_message(
                conversation_id=conversation_id,
                content=fallback_answer,
                citations=citations,
                mode="extractive",
                provider="local",
                model=None,
            )
        )
        store.append_llm_log(
            build_llm_log(
                document_id=document_id,
                question=question,
                settings=settings,
                mode="extractive",
                status="failed",
                latency_ms=error.latency_ms or elapsed_ms(started),
                citation_count=len(citations),
                error=str(error),
            )
        )
        async for event in stream_fallback_answer(
            conversation_id=conversation_id,
            answer=fallback_answer,
            citations=citations,
            reason=str(error),
        ):
            yield event


async def stream_fallback_answer(
    *,
    conversation_id: str,
    answer: str,
    citations: list,
    reason: str,
) -> AsyncIterator[str]:
    yield stream_event(
        "meta",
        {
            "conversation_id": conversation_id,
            "mode": "extractive",
            "provider": "local",
            "model": None,
            "fallback_reason": reason,
            "citations": [citation.model_dump() for citation in citations],
        },
    )
    for chunk in chunk_text(answer):
        yield stream_event("token", {"token": chunk})
    yield stream_event("done", {"answer": answer})


def stream_event(event_type: str, payload: dict) -> str:
    return json.dumps(
        {"type": event_type, **payload},
        ensure_ascii=False,
    ) + "\n"


def chunk_text(text: str, size: int = 18) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)]
