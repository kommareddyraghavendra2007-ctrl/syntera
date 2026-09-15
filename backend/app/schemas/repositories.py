"""Repository API schemas."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RepositoryCreate(BaseModel):
    """Request body for creating a repository from a URL."""

    url: str = Field(..., description="HTTPS Git repository URL")
    branch: str | None = Field(None, description="Branch name (defaults to default branch)")
    name: str | None = Field(None, max_length=255, description="Display name override")


class RepositoryRead(BaseModel):
    """Full repository record."""

    id: str
    name: str
    source_type: str
    source_url: str | None
    branch: str | None
    commit_sha: str | None
    status: str
    status_detail: str | None
    error_message: str | None
    file_count: int
    symbol_count: int
    relationship_count: int
    languages: dict[str, int]
    indexing_started_at: datetime | None
    indexing_finished_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_languages(cls, repo) -> "RepositoryRead":
        langs: dict[str, int] = {}
        if repo.languages_json:
            try:
                langs = json.loads(repo.languages_json)
            except Exception:
                langs = {}
        return cls(
            id=repo.id,
            name=repo.name,
            source_type=repo.source_type,
            source_url=repo.source_url,
            branch=repo.branch,
            commit_sha=repo.commit_sha,
            status=repo.status,
            status_detail=repo.status_detail,
            error_message=repo.error_message,
            file_count=repo.file_count,
            symbol_count=repo.symbol_count,
            relationship_count=repo.relationship_count,
            languages=langs,
            indexing_started_at=repo.indexing_started_at,
            indexing_finished_at=repo.indexing_finished_at,
            created_at=repo.created_at,
        )


class RepositoryStatusRead(BaseModel):
    """Lightweight status-only read for polling."""

    id: str
    name: str
    status: str
    status_detail: str | None
    error_message: str | None
    file_count: int
    symbol_count: int
    relationship_count: int

    model_config = {"from_attributes": True}


class RepositoryListRead(BaseModel):
    """Summary list item."""

    id: str
    name: str
    source_url: str | None
    status: str
    file_count: int
    symbol_count: int
    languages: dict[str, int]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_languages(cls, repo) -> "RepositoryListRead":
        langs: dict[str, int] = {}
        if repo.languages_json:
            try:
                langs = json.loads(repo.languages_json)
            except Exception:
                langs = {}
        return cls(
            id=repo.id,
            name=repo.name,
            source_url=repo.source_url,
            status=repo.status,
            file_count=repo.file_count,
            symbol_count=repo.symbol_count,
            languages=langs,
            created_at=repo.created_at,
        )
