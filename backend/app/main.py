"""
SYNTERA — Codebase Intelligence Platform
FastAPI application entry point.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()

    # ── Ensure required directories exist (handles /tmp paths on Render) ──
    from pathlib import Path  # noqa: PLC0415
    Path(cfg.work_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.qdrant_path).mkdir(parents=True, exist_ok=True)
    # Ensure SQLite parent dir exists
    db_url = cfg.database_url
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "").lstrip("/")
        if not db_path.startswith("/"):
            db_path = "/" + db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "syntera_startup",
        extra={
            "env": cfg.environment,
            "embedding_provider": cfg.embedding_provider,
            "llm_provider": cfg.llm_provider,
            "db": cfg.database_url[:40],
        },
    )
    # Ensure DB tables exist
    init_db()

    # Warm up vector store collection
    try:
        from app.embeddings.factory import get_embedding_provider  # noqa: PLC0415
        from app.indexing.vector_store import QdrantVectorStore  # noqa: PLC0415

        embedder = get_embedding_provider(cfg)
        store = QdrantVectorStore(cfg)
        store.ensure_collection(embedder.dimensions)
        logger.info("qdrant_ready", extra={"dimensions": embedder.dimensions})
    except Exception as exc:
        logger.warning("qdrant_warmup_failed", extra={"error": str(exc)})

    # Warm up BM25 for all READY repositories
    try:
        _warm_all_bm25()
    except Exception as exc:
        logger.warning("bm25_startup_warmup_failed", extra={"error": str(exc)})

    yield
    logger.info("syntera_shutdown")


def _warm_all_bm25() -> None:
    """On startup, rebuild BM25 indexes for all READY repositories."""
    from app.core.database import SessionLocal  # noqa: PLC0415
    from app.core.enums import IndexStatus  # noqa: PLC0415
    from app.indexing.symbol_indexer import SymbolIndexer  # noqa: PLC0415
    from app.models.orm import Repository, Symbol  # noqa: PLC0415

    db = SessionLocal()
    try:
        ready_repos = (
            db.query(Repository)
            .filter(Repository.status == IndexStatus.READY)
            .all()
        )
        if not ready_repos:
            return
        cfg = get_settings()
        indexer = SymbolIndexer(cfg)
        for repo in ready_repos:
            try:
                symbols = (
                    db.query(Symbol)
                    .filter(Symbol.repository_id == repo.id)
                    .all()
                )
                indexer.rebuild_bm25_from_db(repo.id, symbols)
                logger.info(
                    "bm25_warmup_done",
                    extra={"repository_id": repo.id, "symbols": len(symbols)},
                )
            except Exception as exc:
                logger.warning(
                    "bm25_warmup_repo_failed",
                    extra={"repository_id": repo.id, "error": str(exc)},
                )
    finally:
        db.close()


def create_app() -> FastAPI:
    cfg = get_settings()

    app = FastAPI(
        title="SYNTERA — Codebase Intelligence Platform",
        description=(
            "Production-grade RAG system for natural-language querying of any Git repository. "
            "Hybrid retrieval: dense + BM25 + symbol search + graph expansion + reranking."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            # Local development
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            # Production Vercel deployments
            "https://sytera.vercel.app",
            "https://syntera.vercel.app",
            "https://syntera-git-main.vercel.app",
            "https://syntera-kommareddyraghavendra2007-ctrl.vercel.app",
        ],
        allow_origin_regex=r"https://syntera.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global error handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "unhandled_exception",
            extra={"path": request.url.path, "error": str(exc)},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    # ── Routers ───────────────────────────────────────────────────────────
    prefix = cfg.api_prefix
    from app.api.repositories import router as repo_router  # noqa: PLC0415
    from app.api.query import router as query_router  # noqa: PLC0415
    from app.api.symbols import router as symbols_router  # noqa: PLC0415
    from app.api.graph import router as graph_router  # noqa: PLC0415

    app.include_router(repo_router, prefix=prefix)
    app.include_router(query_router, prefix=prefix)
    app.include_router(symbols_router, prefix=prefix)
    app.include_router(graph_router, prefix=prefix)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "SYNTERA"}

    return app


app = create_app()
