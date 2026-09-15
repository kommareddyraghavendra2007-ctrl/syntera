"""
Integration tests: full ingestion pipeline on a small temp repo.
No network or external services required — uses hash embeddings.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.enums import IndexStatus


@pytest.fixture()
def mem_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    # Import all ORM models to register them with Base.metadata
    import app.models.orm  # noqa: F401
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()


@pytest.fixture()
def mini_repo(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth_service.py").write_text(
        'class AuthService:\n    """Handles auth."""\n    def login(self, email, password):\n        return "tok"\n',
        encoding="utf-8",
    )
    (src / "user_repository.py").write_text(
        'class UserRepository:\n    def find_by_email(self, email):\n        return None\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Mini Repo", encoding="utf-8")
    return tmp_path


def test_scan_finds_source_files(mini_repo: Path):
    from app.ingestion.scanner import scan_repository_files
    files = scan_repository_files(mini_repo)
    paths = {f.path for f in files}
    assert "src/auth_service.py" in paths
    assert "README.md" in paths


def test_parse_extracts_class_and_method(mini_repo: Path):
    from app.parsing import parse_source
    source = (mini_repo / "src" / "auth_service.py").read_text(encoding="utf-8")
    result = parse_source("src/auth_service.py", source, "python")
    names = {s.qualified_name for s in result.symbols}
    assert "AuthService" in names
    assert "AuthService.login" in names


def test_pipeline_reaches_ready(mini_repo: Path, mem_db, tmp_path: Path):
    from app.core.config import Settings
    from app.models.orm import Repository
    from app.ingestion.pipeline import run_ingestion
    import tempfile

    work_dir = Path(tempfile.mkdtemp())
    qdrant_dir = Path(tempfile.mkdtemp())

    with patch("app.indexing.symbol_indexer.SymbolIndexer") as MockIdx:
        mock_idx = MagicMock()
        mock_idx.index_repository.return_value = 5
        MockIdx.return_value = mock_idx

        repo = Repository(name="mini", source_type="local", status=IndexStatus.QUEUED)
        mem_db.add(repo)
        mem_db.commit()
        mem_db.refresh(repo)

        source_repo = mini_repo  # captured in closure

        class LocalProvider:
            def fetch(self, destination, settings):
                import shutil
                shutil.copytree(str(source_repo), str(destination), dirs_exist_ok=True)
                return {"name": "mini"}

        cfg = Settings(
            database_url="sqlite:///:memory:",
            qdrant_path=str(qdrant_dir),
            work_dir=str(work_dir),
            embedding_provider="hash",
        )

        with patch("app.indexing.vector_store.QdrantVectorStore"):
            run_ingestion(mem_db, repo, LocalProvider(), cfg)

    mem_db.refresh(repo)
    if repo.status != IndexStatus.READY:
        pytest.fail(f"Expected READY, got {repo.status}: {repo.error_message}")
    assert repo.file_count > 0
    assert repo.symbol_count > 0


def test_repository_isolation(mem_db):
    """Symbols from repo-A must never appear in repo-B queries."""
    from app.models.orm import CodeFile, Repository, Symbol
    from app.core.ids import file_id, symbol_id
    from app.parsing.types import ExtractedSymbol

    repo_a = Repository(name="repo-a", source_type="git", status="READY")
    repo_b = Repository(name="repo-b", source_type="git", status="READY")
    mem_db.add_all([repo_a, repo_b])
    mem_db.flush()

    fid = file_id(repo_a.id, "src/service_a.py")
    mem_db.add(CodeFile(
        id=fid, repository_id=repo_a.id, path="src/service_a.py",
        language="python", classification="source",
        parser_capability="tree_sitter", content_hash="abc", size_bytes=100,
    ))
    sym = ExtractedSymbol(
        symbol_type="class", symbol_name="ServiceA", qualified_name="ServiceA",
        start_line=1, end_line=10, code="class ServiceA: pass",
    )
    sid = symbol_id(repo_a.id, "src/service_a.py", sym)
    mem_db.add(Symbol(
        id=sid, repository_id=repo_a.id, file_id=fid,
        file_path="src/service_a.py", symbol_type="class",
        symbol_name="ServiceA", qualified_name="ServiceA",
        start_line=1, end_line=10, code="class ServiceA: pass", content_hash="abc",
    ))
    mem_db.commit()

    # Query repo-b — must not find repo-a symbols
    results = mem_db.query(Symbol).filter(
        Symbol.repository_id == repo_b.id,
        Symbol.symbol_name == "ServiceA",
    ).all()
    assert results == [], "ISOLATION VIOLATED: repo-b returned repo-a symbols"
