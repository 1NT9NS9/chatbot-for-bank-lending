from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

DATABASE_URL = os.getenv("DATABASE_URL")

assert DATABASE_URL, "DATABASE_URL env variable is required"

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)

# `sessionmaker` with `class_=AsyncSession` is compatible with SQLAlchemy 1.4+
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create tables and ensure pgvector extension."""
    async with engine.begin() as conn:
        # Raw SQL needs exec_driver_sql to be executable
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.run_sync(SQLModel.metadata.create_all) 