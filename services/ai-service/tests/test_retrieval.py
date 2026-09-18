from app.models import DocumentChunk
from app.retrieval import retrieve


def test_retrieve_returns_relevant_chunk() -> None:
    chunks = [
        DocumentChunk(
            id="1",
            document_id="doc",
            index=0,
            text="本文介绍向量检索和引用溯源。",
            page_number=1,
        ),
        DocumentChunk(
            id="2",
            document_id="doc",
            index=1,
            text="这里讨论前端布局。",
            page_number=2,
        ),
    ]

    result = retrieve("什么是引用溯源", chunks)

    assert result
    assert result[0].chunk_id == "1"
