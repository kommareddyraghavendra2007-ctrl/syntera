"""Repository management API endpoints."""
from __future__ import annotations

import concurrent.futures
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_repository_or_404
from app.core.config import get_settings
from app.core.database import get_db
from app.core.enums import IndexStatus
from app.core.logging import get_logger
from app.ingestion.pipeline import run_ingestion
from app.ingestion.providers import GitProvider, ZipProvider
from app.models.orm import Repository
from app.schemas.repositories import RepositoryCreate, RepositoryListRead, RepositoryRead, RepositoryStatusRead
from app.security.urls import validate_git_url

router = APIRouter(prefix="/repositories", tags=["repositories"])
logger = get_logger(__name__)

# Thread pool for background ingestion
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="ingestion")


def _run_in_background(repo_id: str, provider, settings) -> None:
    """Run ingestion in a background thread with its own DB session."""
    from app.core.database import SessionLocal  # noqa: PLC0415

    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            run_ingestion(db, repo, provider, settings)
    finally:
        db.close()
        # Clean up the uploaded ZIP temp directory after ingestion completes
        if isinstance(provider, ZipProvider):
            try:
                zip_tmp_dir = provider.zip_path.parent
                if zip_tmp_dir.exists():
                    shutil.rmtree(zip_tmp_dir, ignore_errors=True)
            except Exception:
                pass


@router.get("", response_model=list[RepositoryListRead])
def list_repositories(db: Session = Depends(get_db)):
    repos = db.query(Repository).order_by(Repository.created_at.desc()).all()
    return [RepositoryListRead.from_orm_with_languages(r) for r in repos]


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def create_repository(
    body: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    cfg = get_settings()

    try:
        validated_url = validate_git_url(body.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Derive name
    name = body.name or validated_url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")

    repo = Repository(
        name=name,
        source_type="git",
        source_url=validated_url,
        branch=body.branch,
        status=IndexStatus.QUEUED,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    provider = GitProvider(url=validated_url, branch=body.branch)
    _executor.submit(_run_in_background, repo.id, provider, cfg)

    logger.info("repository_created", extra={"repository_id": repo.id, "url": validated_url})
    return RepositoryRead.from_orm_with_languages(repo)


@router.post("/upload", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def upload_zip_repository(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    cfg = get_settings()

    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    # Save upload to temp location
    tmp = Path(tempfile.mkdtemp()) / "upload.zip"
    try:
        content = await file.read()
        if len(content) > cfg.max_repository_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"ZIP file exceeds size limit ({cfg.max_repository_size_bytes} bytes)",
            )
        tmp.write_bytes(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    safe_name = name[:255].strip() or "uploaded-repo"

    repo = Repository(
        name=safe_name,
        source_type="zip",
        source_url=None,
        status=IndexStatus.QUEUED,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    provider = ZipProvider(zip_path=tmp, name=safe_name)
    _executor.submit(_run_in_background, repo.id, provider, cfg)

    return RepositoryRead.from_orm_with_languages(repo)


@router.get("/{repository_id}", response_model=RepositoryRead)
def get_repository(
    repo: Repository = Depends(get_repository_or_404),
):
    return RepositoryRead.from_orm_with_languages(repo)


@router.get("/{repository_id}/status", response_model=RepositoryStatusRead)
def get_repository_status(
    repo: Repository = Depends(get_repository_or_404),
):
    return repo


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repository_id: str,
    repo: Repository = Depends(get_repository_or_404),
    db: Session = Depends(get_db),
):
    # Remove from vector store
    try:
        from app.indexing.vector_store import QdrantVectorStore  # noqa: PLC0415
        from app.graph.service import invalidate_graph  # noqa: PLC0415
        from app.indexing.lexical import invalidate_bm25_index  # noqa: PLC0415

        QdrantVectorStore().delete_by_repository(repository_id)
        invalidate_graph(repository_id)
        invalidate_bm25_index(repository_id)
    except Exception as exc:
        logger.warning("cleanup_error_on_delete", extra={"error": str(exc)})

    db.delete(repo)
    db.commit()
    logger.info("repository_deleted", extra={"repository_id": repository_id})


@router.post("/{repository_id}/reindex", response_model=RepositoryStatusRead)
def reindex_repository(
    repository_id: str,
    repo: Repository = Depends(get_repository_or_404),
    db: Session = Depends(get_db),
):
    if repo.status in {IndexStatus.CLONING, IndexStatus.PARSING, IndexStatus.INDEXING}:
        raise HTTPException(status_code=409, detail="Repository is currently being indexed")
    if not repo.source_url:
        raise HTTPException(status_code=400, detail="Cannot reindex a ZIP repository without re-upload")

    # Clean existing data
    try:
        from app.indexing.vector_store import QdrantVectorStore  # noqa: PLC0415
        from app.graph.service import invalidate_graph  # noqa: PLC0415
        from app.indexing.lexical import invalidate_bm25_index  # noqa: PLC0415

        QdrantVectorStore().delete_by_repository(repository_id)
        invalidate_graph(repository_id)
        invalidate_bm25_index(repository_id)
    except Exception as exc:
        logger.warning("cleanup_error_on_reindex", extra={"error": str(exc)})

    # Clear existing DB records
    from app.models.orm import CodeFile, CodeRelationship, Symbol  # noqa: PLC0415

    db.query(CodeRelationship).filter(CodeRelationship.repository_id == repository_id).delete()
    db.query(Symbol).filter(Symbol.repository_id == repository_id).delete()
    db.query(CodeFile).filter(CodeFile.repository_id == repository_id).delete()

    repo.status = IndexStatus.QUEUED
    repo.status_detail = "Reindexing queued"
    repo.error_message = None
    repo.file_count = 0
    repo.symbol_count = 0
    repo.relationship_count = 0
    repo.commit_sha = None
    db.commit()
    db.refresh(repo)

    cfg = get_settings()
    provider = GitProvider(url=repo.source_url, branch=repo.branch)
    _executor.submit(_run_in_background, repo.id, provider, cfg)

    return repo
