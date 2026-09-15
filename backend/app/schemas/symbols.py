"""Symbol API schemas."""
from __future__ import annotations

from pydantic import BaseModel


class SymbolRead(BaseModel):
    id: str
    repository_id: str
    file_path: str
    language: str | None
    symbol_type: str
    symbol_name: str
    qualified_name: str
    class_name: str | None
    start_line: int
    end_line: int

    model_config = {"from_attributes": True}


class SymbolDetailRead(SymbolRead):
    code: str
    documentation: str | None
    parent_symbol: str | None
    module_name: str | None

    model_config = {"from_attributes": True}


class FileRead(BaseModel):
    id: str
    repository_id: str
    path: str
    language: str | None
    classification: str
    parser_capability: str
    size_bytes: int
    is_binary: bool
    is_secret: bool

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    symbol_types: list[str] | None = None
    languages: list[str] | None = None
    top_k: int = 20


class SearchResult(BaseModel):
    symbol_id: str | None
    symbol_name: str | None
    qualified_name: str | None
    symbol_type: str | None
    file_path: str
    start_line: int | None
    end_line: int | None
    language: str | None
    score: float
    code_snippet: str | None
