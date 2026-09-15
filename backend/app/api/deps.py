"""FastAPI dependency injection helpers."""
from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.orm import Repository


def get_repository_or_404(
    repository_id: str,
    db: Session = Depends(get_db),
) -> Repository:
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found",
        )
    return repo


def get_ready_repository(
    repository_id: str,
    db: Session = Depends(get_db),
) -> Repository:
    repo = get_repository_or_404(repository_id, db)
    if repo.status != "READY":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository is not ready for queries (status: {repo.status})",
        )
    return repo
