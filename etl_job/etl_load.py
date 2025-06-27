"""Simple ETL loader for Mini-MVP.

Reads CSV/TSV or plain text files with credit documents, splits into chunks,
calculates sentence-transformers embeddings and stores them in Postgres table
`document` with pgvector column.

Usage inside container (see Dockerfile CMD):
    python etl_load.py /data/source.csv

Env vars required:
    DATABASE_URL – same format as in docker-compose

Optional env vars:
    DATA_PATH – path to input file (overrides CLI)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Iterable, List
from datetime import datetime

import pandas as pd
from pgvector.sqlalchemy import Vector
from sentence_transformers import SentenceTransformer
from sqlalchemy import Column, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "")

INPUT_FILE = os.getenv("DATA_PATH") or (sys.argv[1] if len(sys.argv) > 1 else "data/source.csv")

CHUNK_SIZE_WORDS = 512  # rough heuristic
EMBEDDING_DIM = 768

# ---------------------------------------------------------------------------
# Models (duplicated from chat-service)
# ---------------------------------------------------------------------------


class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    text: str = Field(sa_column_kwargs={"nullable": False})
    embedding: List[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Singleton embedding model with 768-dim output."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")  # 768 dims
    return _embedding_model


def chunk_text(text: str, max_words: int = CHUNK_SIZE_WORDS) -> Iterable[str]:
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i : i + max_words])


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(SQLModel.metadata.create_all)


async def insert_documents(chunks: list[str], session_maker: sessionmaker) -> None:
    model = get_embedding_model()
    embeddings = model.encode(chunks, normalize_embeddings=True)

    async with session_maker() as session:
        session.add_all(
            [
                Document(text=text, embedding=emb.tolist())
                for text, emb in zip(chunks, embeddings)
            ]
        )
        await session.commit()


async def etl(file_path: Path) -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL env variable is required for ETL run")

    print(f"[ETL] Reading source file: {file_path}")
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    if file_path.suffix.lower() in {".csv", ".tsv"}:
        df = pd.read_csv(file_path, sep="," if file_path.suffix == ".csv" else "\t")
        # Expect column named 'text'. Fallback to first column.
        if "text" not in df.columns:
            df.columns = ["text", *df.columns[1:]]
        texts = df["text"].dropna().astype(str).tolist()
    else:
        texts = [file_path.read_text(encoding="utf-8")]

    print(f"[ETL] Loaded {len(texts)} raw documents")

    # Chunking
    chunks: list[str] = []
    for doc in texts:
        chunks.extend(list(chunk_text(doc)))
    print(f"[ETL] Produced {len(chunks)} chunks (<= {CHUNK_SIZE_WORDS} words)")

    # DB engine
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)
    session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    await init_db(engine)
    await insert_documents(chunks, session_maker)
    await engine.dispose()
    print("[ETL] Done – data inserted.")


if __name__ == "__main__":
    asyncio.run(etl(Path(INPUT_FILE))) 