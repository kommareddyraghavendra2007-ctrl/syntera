from __future__ import annotations

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    start_column: int = 0
    end_column: int = 0


class ExtractedSymbol(BaseModel):
    symbol_type: str
    symbol_name: str
    qualified_name: str
    class_name: str | None = None
    module_name: str | None = None
    start_line: int
    end_line: int
    start_column: int = 0
    end_column: int = 0
    code: str = ""
    documentation: str | None = None
    parent_symbol: str | None = None
    language: str | None = None
    file_path: str = ""


class ExtractedImport(BaseModel):
    module: str
    names: list[str] = Field(default_factory=list)
    start_line: int = 1


class ExtractedCall(BaseModel):
    callee: str
    start_line: int
    confidence: float = 0.6


class ExtractedRoute(BaseModel):
    method: str
    path: str
    handler: str | None = None
    start_line: int
    framework: str | None = None


class ParseResult(BaseModel):
    file_path: str
    language: str
    parser_capability: str
    symbols: list[ExtractedSymbol] = Field(default_factory=list)
    imports: list[ExtractedImport] = Field(default_factory=list)
    calls: list[ExtractedCall] = Field(default_factory=list)
    routes: list[ExtractedRoute] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
