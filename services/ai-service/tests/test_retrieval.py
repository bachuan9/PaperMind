from app.models import DocumentChunk
from app.models import Citation
from app.retrieval import build_extractive_answer, retrieve


def test_retrieve_returns_relevant_chunk() -> None:
    chunks = [
        DocumentChunk(
            id="1",
            document_id="doc",
            index=0,
            text="\u672c\u6587\u4ecb\u7ecd\u5411\u91cf\u68c0\u7d22\u548c\u5f15\u7528\u6eaf\u6e90\u3002",
            page_number=1,
        ),
        DocumentChunk(
            id="2",
            document_id="doc",
            index=1,
            text="\u8fd9\u91cc\u8ba8\u8bba\u524d\u7aef\u5e03\u5c40\u3002",
            page_number=2,
        ),
    ]

    result = retrieve("\u4ec0\u4e48\u662f\u5f15\u7528\u6eaf\u6e90", chunks)

    assert result
    assert result[0].chunk_id == "1"


def test_retrieve_uses_document_context_for_vague_question() -> None:
    chunks = [
        DocumentChunk(
            id="1",
            document_id="doc",
            index=0,
            text="\u4e0d\u8981\u8bd5\u7740\u9884\u5224\u5e02\u573a\uff0c\u8981\u8ddf\u7740\u5e02\u573a\u8d70\u3002",
            page_number=None,
        )
    ]

    result = retrieve("\u4ec0\u4e48\u610f\u601d", chunks)

    assert result
    assert result[0].chunk_id == "1"


def test_vague_question_gets_plain_explanation() -> None:
    answer = build_extractive_answer(
        "\u4ec0\u4e48\u610f\u601d",
        [
            Citation(
                chunk_id="1",
                page_number=None,
                text=(
                    "\u4e0d\u8981\u8bd5\u7740\u9884\u5224\u5e02\u573a\uff0c"
                    "\u8981\u8ddf\u7740\u5e02\u573a\u8d70\u3002"
                    "\u5f53\u4f9d\u636e\u4e0d\u8db3\u65f6\u8981\u660e\u786e\u8bf4\u660e\u3002"
                ),
                score=0.01,
            )
        ],
    )

    assert "\u7b80\u5355\u8bf4" in answer
    assert "\u53ef\u4ee5\u62c6\u6210\u51e0\u4e2a\u8981\u70b9" in answer
    assert "## \u6587\u6863\u4f9d\u636e" in answer
    assert "## \u8fb9\u754c\u548c\u4e0d\u786e\u5b9a\u6027" in answer
    assert "2. " in answer
