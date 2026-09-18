from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import build_document_insights
from .llm import answer_with_model
from .models import (
    AskRequest,
    AskResponse,
    DocumentChunk,
    DocumentDetail,
    DocumentInsightResponse,
    DocumentSummary,
    LlmCallLog,
    ModelStatusResponse,
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

    return store.save_document(document, chunks)


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


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    store: JsonStore = Depends(get_store),
) -> dict[str, bool]:
    deleted = store.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"ok": True}


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

    citations = retrieve(request.question, document.chunks)
    model_result = await answer_with_model(
        settings=settings,
        question=request.question,
        citations=citations,
    )
    if model_result.answer:
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
            mode="model",
            provider="SiliconFlow",
            model=settings.llm_model,
        )

    fallback_answer = build_extractive_answer(request.question, citations)
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
        mode="extractive",
        provider="local",
        model=None,
        fallback_reason=model_result.error,
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
