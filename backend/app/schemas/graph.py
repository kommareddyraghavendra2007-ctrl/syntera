"""Graph visualization schemas."""
from __future__ import annotations

from pydantic import BaseModel


class GraphNodeData(BaseModel):
    id: str
    label: str
    symbol_type: str
    file_path: str
    start_line: int
    language: str | None = None


class GraphEdgeData(BaseModel):
    source: str
    target: str
    relation_type: str
    confidence: float = 1.0


class GraphData(BaseModel):
    nodes: list[GraphNodeData]
    edges: list[GraphEdgeData]
    repository_id: str
    root_symbol: str | None = None
