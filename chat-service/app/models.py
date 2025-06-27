from __future__ import annotations

from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str = Field(sa_column_kwargs={"nullable": False})
    embedding: list[float] = Field(sa_column=Column(Vector(768)))
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class DialogHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str  # "user" | "assistant"
    content: str
    ts: datetime = Field(default_factory=datetime.utcnow, nullable=False) 