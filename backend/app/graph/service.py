"""
GraphService — thread-safe graph cache keyed by repository_id.

Graphs are built lazily on first access and invalidated on re-index.
"""
from __future__ import annotations

import threading

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.graph.builder import build_graph_from_db
from app.graph.store import CodeGraph

logger = get_logger(__name__)

_lock = threading.Lock()
_cache: dict[str, CodeGraph] = {}


def get_graph(db: Session, repository_id: str, refresh: bool = False) -> CodeGraph:
    """Return the cached graph for *repository_id*, building it if necessary."""
    with _lock:
        if not refresh and repository_id in _cache:
            return _cache[repository_id]
        graph = build_graph_from_db(db, repository_id)
        _cache[repository_id] = graph
        return graph


def invalidate_graph(repository_id: str) -> None:
    """Remove cached graph — called when repository is re-indexed."""
    with _lock:
        _cache.pop(repository_id, None)
        logger.info("graph_cache_invalidated", extra={"repository_id": repository_id})
