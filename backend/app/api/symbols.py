"""Symbol and code exploration API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ready_repository
from app.core.config import get_settings
from app.models.orm import CodeFile, Repository, Symbol
from app.retrieval.engine import RetrievalEngine
from app.schemas.symbols import (
    FileRead,
    SearchRequest,
    SearchResult,
    SymbolDetailRead,
    SymbolRead,
)

router = APIRouter(prefix="/repositories/{repository_id}", tags=["symbols"])


@router.get("/files", response_model=list[FileRead])
def list_files(
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
    limit: int = 200,
    offset: int = 0,
    language: str | None = None,
):
    q = db.query(CodeFile).filter(CodeFile.repository_id == repo.id)
    if language:
        q = q.filter(CodeFile.language == language)
    return q.order_by(CodeFile.path).offset(offset).limit(limit).all()


@router.get("/symbols", response_model=list[SymbolRead])
def list_symbols(
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    symbol_type: str | None = None,
    file_path: str | None = None,
):
    q = db.query(Symbol).filter(Symbol.repository_id == repo.id)
    if symbol_type:
        q = q.filter(Symbol.symbol_type == symbol_type)
    if file_path:
        q = q.filter(Symbol.file_path == file_path)
    return q.order_by(Symbol.file_path, Symbol.start_line).offset(offset).limit(limit).all()


@router.get("/symbols/{symbol_id}", response_model=SymbolDetailRead)
def get_symbol(
    symbol_id: str,
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
):
    sym = (
        db.query(Symbol)
        .filter(Symbol.id == symbol_id, Symbol.repository_id == repo.id)
        .first()
    )
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return sym


@router.post("/search", response_model=list[SearchResult])
def search_repository(
    body: SearchRequest,
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
):
    cfg = get_settings()
    engine = RetrievalEngine(cfg)
    result = engine.retrieve(
        db=db,
        repository_id=repo.id,
        query=body.query,
        repository_name=repo.name,
    )

    search_results = []
    for item in result.candidates[: body.top_k]:
        p = item.get("payload", {})
        # Filter by type/language if requested
        if body.symbol_types and p.get("symbol_type") not in body.symbol_types:
            continue
        if body.languages and p.get("language") not in body.languages:
            continue
        search_results.append(
            SearchResult(
                symbol_id=p.get("symbol_id"),
                symbol_name=p.get("symbol_name"),
                qualified_name=p.get("qualified_name"),
                symbol_type=p.get("symbol_type"),
                file_path=p.get("file_path", ""),
                start_line=p.get("start_line"),
                end_line=p.get("end_line"),
                language=p.get("language"),
                score=item.get("rerank_score") or item.get("score", 0.0),
                code_snippet=p.get("code_snippet"),
            )
        )
    return search_results
