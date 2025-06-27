from __future__ import annotations

import os
import uuid
from typing import Sequence

import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sqlmodel import select

from .db import async_session
from .models import Document, DialogHistory

# init generative ai
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
assert GEMINI_API_KEY, "GEMINI_API_KEY env variable is required"

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        # 768-размерный эмбеддер, чтобы совпадать с pgvector Vector(768)
        _embedding_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    return _embedding_model


async def embed(text: str) -> list[float]:
    model = get_embedding_model()
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()


async def get_relevant_chunks(question: str, k: int = 5) -> Sequence[Document]:
    vec = await embed(question)
    async with async_session() as session:
        stmt = (
            select(Document)
            .order_by(Document.embedding.l2_distance(vec))  # type: ignore[attr-defined]
            .limit(k)
        )
        result = await session.execute(stmt)
        return list(result.scalars())


async def log_dialog(session_id: str, role: str, content: str) -> None:
    async with async_session() as session:
        session.add(DialogHistory(session_id=session_id, role=role, content=content))
        await session.commit()


async def generate_answer(question: str, session_id: str | None = None) -> str:
    if not session_id:
        session_id = str(uuid.uuid4())

    # store user question
    await log_dialog(session_id, "user", question)

    chunks = await get_relevant_chunks(question)

    context_text = "\n".join(f"Документ {i+1}: {c.text}" for i, c in enumerate(chunks))
    prompt = (
        "You are a Sberbank assistant. Answer the client's question based on the documents provided. "
        "If the answer is not found in the context, say that there is no information.\n\n"
        f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
    )

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    answer = response.text

    await log_dialog(session_id, "assistant", answer)

    return answer, session_id 