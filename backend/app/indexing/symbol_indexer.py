"""
SymbolIndexer — coordinates embedding generation, Qdrant upsert, and BM25 build.

Called by the ingestion pipeline after all symbols are persisted to the DB.
Also used for incremental re-indexing of individual files.
"""
from __future__ import annotations

import uuid

from app.core.config import Settings, get_settings
from app.core.enums import SymbolType
from app.core.logging import get_logger
from app.embeddings.factory import get_embedding_provider
from app.indexing.lexical import BM25Document, BM25Index, set_bm25_index
from app.indexing.vector_store import QdrantVectorStore
from app.models.orm import Symbol

logger = get_logger(__name__)

# Symbol types that are high-value for retrieval — include all
_INDEXABLE_TYPES = {
    SymbolType.CLASS,
    SymbolType.INTERFACE,
    SymbolType.STRUCT,
    SymbolType.ENUM,
    SymbolType.FUNCTION,
    SymbolType.METHOD,
    SymbolType.ENDPOINT,
    SymbolType.CONFIGURATION,
    SymbolType.DOCUMENTATION,
    SymbolType.TEST,
    SymbolType.FILE,
    SymbolType.MODULE,
    SymbolType.VARIABLE,
    SymbolType.CONSTANT,
    SymbolType.UNKNOWN,
}


def _symbol_text(sym: Symbol) -> str:
    """Compose the text that will be embedded for a symbol."""
    parts = [
        f"{sym.symbol_type}: {sym.qualified_name}",
        f"file: {sym.file_path}",
    ]
    if sym.documentation:
        parts.append(sym.documentation[:500])
    if sym.code:
        parts.append(sym.code[:1200])
    return "\n".join(parts)


def _qdrant_id(symbol_id: str) -> str:
    """Convert arbitrary symbol ID to a valid Qdrant point ID (UUID format)."""
    try:
        uuid.UUID(symbol_id)
        return symbol_id
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, symbol_id))


class SymbolIndexer:
    def __init__(self, settings: Settings | None = None) -> None:
        self._cfg = settings or get_settings()
        self._embedder = get_embedding_provider(self._cfg)
        self._vector_store = QdrantVectorStore(self._cfg)
        self._vector_store.ensure_collection(self._embedder.dimensions)

    def index_repository(
        self,
        repository_id: str,
        symbols: list[Symbol],
    ) -> int:
        """Index all symbols for a repository. Returns number of vectors upserted."""
        indexable = [s for s in symbols if s.symbol_type in _INDEXABLE_TYPES]
        if not indexable:
            logger.warning("no_indexable_symbols", extra={"repository_id": repository_id})
            return 0

        # ── Vector indexing ──────────────────────────────────────────────
        texts = [_symbol_text(s) for s in indexable]
        vectors = self._embedder.embed_texts(texts)

        points = []
        for sym, vec in zip(indexable, vectors):
            points.append(
                {
                    "id": _qdrant_id(sym.id),
                    "vector": vec,
                    "payload": {
                        "symbol_id": sym.id,
                        "repository_id": repository_id,
                        "symbol_name": sym.symbol_name,
                        "qualified_name": sym.qualified_name,
                        "symbol_type": sym.symbol_type,
                        "file_path": sym.file_path,
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                        "language": sym.language,
                        "class_name": sym.class_name,
                        "module_name": sym.module_name,
                        "documentation": sym.documentation,
                        "code_snippet": sym.code[:600] if sym.code else "",
                    },
                }
            )
        upserted = self._vector_store.upsert_points(points)

        # ── BM25 lexical index ────────────────────────────────────────────
        bm25_docs = [
            BM25Document(
                symbol_id=sym.id,
                repository_id=repository_id,
                symbol_name=sym.symbol_name,
                qualified_name=sym.qualified_name,
                symbol_type=sym.symbol_type,
                file_path=sym.file_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                language=sym.language,
                text=f"{sym.qualified_name} {sym.symbol_name} {sym.file_path} "
                     f"{sym.documentation or ''} {sym.code[:400] if sym.code else ''}",
            )
            for sym in indexable
        ]
        bm25 = BM25Index(repository_id)
        bm25.build(bm25_docs)
        set_bm25_index(bm25)

        logger.info(
            "symbol_indexer_done",
            extra={
                "repository_id": repository_id,
                "symbols_indexed": upserted,
                "bm25_docs": len(bm25_docs),
            },
        )
        return upserted

    def rebuild_bm25_from_db(self, repository_id: str, symbols: list[Symbol]) -> None:
        """Rebuild only the BM25 index (e.g., after startup when Qdrant is populated)."""
        indexable = [s for s in symbols if s.symbol_type in _INDEXABLE_TYPES]
        bm25_docs = [
            BM25Document(
                symbol_id=sym.id,
                repository_id=repository_id,
                symbol_name=sym.symbol_name,
                qualified_name=sym.qualified_name,
                symbol_type=sym.symbol_type,
                file_path=sym.file_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                language=sym.language,
                text=f"{sym.qualified_name} {sym.symbol_name} {sym.file_path} "
                     f"{sym.documentation or ''} {sym.code[:400] if sym.code else ''}",
            )
            for sym in indexable
        ]
        bm25 = BM25Index(repository_id)
        bm25.build(bm25_docs)
        set_bm25_index(bm25)
        logger.info(
            "bm25_rebuilt_from_db",
            extra={"repository_id": repository_id, "docs": len(bm25_docs)},
        )
