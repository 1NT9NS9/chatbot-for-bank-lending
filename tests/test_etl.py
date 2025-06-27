import pytest

from etl_job.etl_load import chunk_text, get_embedding_model


def test_chunk_text_splits():
    text = "word " * 1200  # 1200 words
    chunks = list(chunk_text(text, max_words=512))
    assert len(chunks) == 3
    assert all(len(c.split()) <= 512 for c in chunks)


@pytest.mark.asyncio
async def test_embedding_dimension():
    model = get_embedding_model()
    vec = model.encode(["test"])[0]
    assert len(vec) == 768 