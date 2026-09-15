"""Query / answer API schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    symbol_id: str | None = None
    symbol_name: str | None = None
    symbol_type: str | None = None
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    language: str | None = None
    score: float | None = None


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None
    include_graph: bool = False


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    intent: str
    confidence: str
    conversation_id: str | None = None
    retrieval_stats: dict = Field(default_factory=dict)
    graph_data: dict | None = None


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class ConversationRead(BaseModel):
    id: str
    repository_id: str
    title: str

    model_config = {"from_attributes": True}


class MessageRead(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)

    model_config = {"from_attributes": True}
