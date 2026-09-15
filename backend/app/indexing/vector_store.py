"""
Qdrant vector store abstraction.

Uses local on-disk storage when QDRANT_URL is not configured (dev default).
Switches to remote Qdrant when QDRANT_URL is provided.

Collection schema:
  - Single collection "syntera_code_units" shared across repositories
  - Every point carries a repository_id payload for strict filtering
  - Dense vector: "dense" (dimensions from embedding provider)
  - Sparse vectors not stored in Qdrant for the MVP — BM25 handled separately
"""
from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class QdrantVectorStore:
    """Thin wrapper around qdrant_client with SYNTERA-specific helpers."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._cfg = settings or get_settings()
        self._client = self._make_client()
        self._collection = self._cfg.qdrant_collection

    # ------------------------------------------------------------------
    # Client creation
    # ------------------------------------------------------------------

    def _make_client(self):
        try:
            from qdrant_client import QdrantClient  # noqa: PLC0415
        except ImportError as e:
            raise RuntimeError("qdrant-client is required. pip install qdrant-client") from e

        if self._cfg.qdrant_url:
            logger.info(
                "qdrant_remote_client",
                extra={"url": self._cfg.qdrant_url},
            )
            return QdrantClient(
                url=self._cfg.qdrant_url,
                api_key=self._cfg.qdrant_api_key,
                timeout=30,
            )

        import os  # noqa: PLC0415

        qdrant_path = self._cfg.qdrant_path
        os.makedirs(qdrant_path, exist_ok=True)
        logger.info("qdrant_local_client", extra={"path": qdrant_path})
        return QdrantClient(path=qdrant_path)

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def ensure_collection(self, dimensions: int) -> None:
        """Create the collection if it does not exist."""
        from qdrant_client.models import Distance, VectorParams  # noqa: PLC0415

        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection in existing:
            return

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
        )
        # Payload index for fast repository-scoped filtering
        from qdrant_client.models import PayloadSchemaType  # noqa: PLC0415

        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="repository_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info(
            "qdrant_collection_created",
            extra={"collection": self._collection, "dimensions": dimensions},
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_points(
        self,
        points: list[dict],
        batch_size: int = 64,
    ) -> int:
        """Upsert a list of point dicts: {id, vector, payload}."""
        from qdrant_client.models import PointStruct  # noqa: PLC0415

        total = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            structs = [
                PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                for p in batch
            ]
            self._client.upsert(collection_name=self._collection, points=structs)
            total += len(structs)

        logger.info("qdrant_upsert_done", extra={"count": total})
        return total

    def delete_by_repository(self, repository_id: str) -> None:
        """Remove all points belonging to a repository."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue  # noqa: PLC0415

        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="repository_id",
                        match=MatchValue(value=repository_id),
                    )
                ]
            ),
        )
        logger.info("qdrant_deleted_repository", extra={"repository_id": repository_id})

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        repository_id: str,
        top_k: int = 20,
        score_threshold: float = 0.0,
        symbol_types: list[str] | None = None,
    ) -> list[dict]:
        """Dense semantic search, repository-scoped."""
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue  # noqa: PLC0415

        must: list[Any] = [
            FieldCondition(key="repository_id", match=MatchValue(value=repository_id))
        ]
        if symbol_types:
            must.append(
                FieldCondition(key="symbol_type", match=MatchAny(any=symbol_types))
            )

        hits = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            query_filter=Filter(must=must),
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            {"id": hit.id, "score": hit.score, "payload": hit.payload}
            for hit in hits
        ]

    def collection_info(self) -> dict:
        try:
            info = self._client.get_collection(self._collection)
            return {
                "collection": self._collection,
                "vectors_count": info.vectors_count,
                "status": str(info.status),
            }
        except Exception as exc:
            return {"error": str(exc)}
