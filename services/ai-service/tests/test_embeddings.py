from app.embeddings import VECTOR_DIMENSION, cosine_similarity, embed_text


def test_embed_text_returns_stable_unit_vector() -> None:
    first = embed_text("引用溯源需要展示原文依据")
    second = embed_text("引用溯源需要展示原文依据")

    assert len(first) == VECTOR_DIMENSION
    assert first == second
    assert round(cosine_similarity(first, second), 4) == 1.0


def test_related_text_has_higher_similarity() -> None:
    query = embed_text("如何进行引用溯源")
    related = embed_text("引用溯源需要展示原文片段")
    unrelated = embed_text("前端页面布局和按钮样式")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)
