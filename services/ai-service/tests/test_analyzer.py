from app.analyzer import build_document_insights
from app.models import DocumentChunk


def test_build_document_insights_returns_summary_and_questions() -> None:
    chunks = [
        DocumentChunk(
            id="1",
            document_id="doc",
            index=0,
            text=(
                "\u5f15\u7528\u6eaf\u6e90\u662f\u964d\u4f4e\u5e7b\u89c9\u7684\u91cd\u8981\u7b56\u7565\u3002"
                "\u56de\u7b54\u4e2d\u9700\u8981\u5c55\u793a\u5f15\u7528\u7247\u6bb5\u3002"
            ),
            page_number=1,
        )
    ]

    insights = build_document_insights(chunks)

    assert insights.summary
    assert insights.keywords
    assert insights.sections
    assert insights.suggested_questions
