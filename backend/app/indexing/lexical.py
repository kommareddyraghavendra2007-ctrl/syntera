"""
BM25 lexical index — in-memory, per-repository.

Built from indexed symbols and stored in a thread-safe registry.
Supports token-level keyword search for exact identifiers, method names,
file names, and technical terms that semantic search may miss.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi

from app.core.logging import get_logger

logger = get_logger(__name__)

_TOKENIZE = re.compile(r"[A-Za-z][a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z][a-z]*|\d+")


def tokenize(text: str) -> list[str]:
    """Split camelCase/snake_case identifiers and normal words into tokens."""
    tokens = []
    for part in re.split(r"[\s_/\.\-]+", text):
        tokens.extend(t.lower() for t in _TOKENIZE.findall(part) if t)
    return tokens or [text.lower()]


@dataclass
class BM25Document:
    symbol_id: str
    repository_id: str
    symbol_name: str
    qualified_name: str
    symbol_type: str
    file_path: str
    start_line: int
    end_line: int
    language: str | None
    text: str  # raw text used for tokenization


class BM25Index:
    """BM25 index for a single repository."""

    def __init__(self, repository_id: str) -> None:
        self.repository_id = repository_id
        self._docs: list[BM25Document] = []
        self._bm25: BM25Okapi | None = None

    def build(self, docs: list[BM25Document]) -> None:
        self._docs = docs
        if not docs:
            self._bm25 = None
            return
        corpus = [tokenize(d.text) for d in docs]
        self._bm25 = BM25Okapi(corpus)
        logger.info(
            "bm25_index_built",
            extra={"repository_id": self.repository_id, "docs": len(docs)},
        )

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        if self._bm25 is None or not self._docs:
            return []
        # Use both split tokens AND the raw lowercased query as a token
        # so exact camelCase names like "AuthService" still match
        tokens = tokenize(query)
        raw_lower = query.strip().lower()
        if raw_lower and raw_lower not in tokens:
            tokens = [raw_lower] + tokens
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]
        results = []
        for idx, score in ranked:
            if score <= 0:
                break
            doc = self._docs[idx]
            results.append(
                {
                    "id": doc.symbol_id,
                    "score": float(score),
                    "payload": {
                        "repository_id": doc.repository_id,
                        "symbol_name": doc.symbol_name,
                        "qualified_name": doc.qualified_name,
                        "symbol_type": doc.symbol_type,
                        "file_path": doc.file_path,
                        "start_line": doc.start_line,
                        "end_line": doc.end_line,
                        "language": doc.language,
                    },
                }
            )
        return results


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_registry: dict[str, BM25Index] = {}


def get_bm25_index(repository_id: str) -> BM25Index | None:
    with _lock:
        return _registry.get(repository_id)


def set_bm25_index(index: BM25Index) -> None:
    with _lock:
        _registry[index.repository_id] = index


def invalidate_bm25_index(repository_id: str) -> None:
    with _lock:
        _registry.pop(repository_id, None)
