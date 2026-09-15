"""
RetrievalEngine — the core of SYNTERA's intelligence.

Pipeline:
  query
  → QueryAnalyzer (intent + expansion)
  → dense semantic search (Qdrant)
  → BM25 lexical search
  → exact symbol search (DB)
  → RRF fusion
  → graph-expansion (bounded BFS)
  → reranking
  → context construction
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.embeddings.factory import get_embedding_provider
from app.graph.service import get_graph
from app.indexing.lexical import get_bm25_index
from app.indexing.vector_store import QdrantVectorStore
from app.retrieval.context_builder import build_context
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.query import QueryAnalysis, QueryAnalyzer
from app.retrieval.reranker import rerank

logger = get_logger(__name__)


class RetrievalResult:
    """Structured output from the retrieval engine."""

    def __init__(
        self,
        analysis: QueryAnalysis,
        candidates: list[dict],
        graph_neighbors: list[dict],
        context: str,
        stats: dict,
    ) -> None:
        self.analysis = analysis
        self.candidates = candidates
        self.graph_neighbors = graph_neighbors
        self.context = context
        self.stats = stats

    def citations(self) -> list[dict]:
        """Return citation dicts for the answer response."""
        seen: set[str] = set()
        result = []
        for item in self.candidates:
            p = item.get("payload", {})
            key = f"{p.get('file_path')}:{p.get('start_line')}"
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    "symbol_id": p.get("symbol_id"),
                    "symbol_name": p.get("qualified_name") or p.get("symbol_name"),
                    "symbol_type": p.get("symbol_type"),
                    "file_path": p.get("file_path"),
                    "start_line": p.get("start_line"),
                    "end_line": p.get("end_line"),
                    "language": p.get("language"),
                    "score": item.get("rerank_score") or item.get("score"),
                }
            )
        return result


class RetrievalEngine:
    def __init__(self, settings: Settings | None = None) -> None:
        self._cfg = settings or get_settings()
        self._analyzer = QueryAnalyzer()
        self._embedder = get_embedding_provider(self._cfg)
        self._vector_store = QdrantVectorStore(self._cfg)

    def retrieve(
        self,
        db: Session,
        repository_id: str,
        query: str,
        repository_name: str = "",
    ) -> RetrievalResult:
        """Full retrieval pipeline. Returns RetrievalResult."""

        stats: dict = {
            "query": query,
            "repository_id": repository_id,
            "dense_hits": 0,
            "sparse_hits": 0,
            "symbol_hits": 0,
            "fused_hits": 0,
            "graph_expansion_hits": 0,
            "reranked_hits": 0,
        }

        # ── Step 1: Query understanding ──────────────────────────────────
        analysis = self._analyzer.analyze(query)

        # ── Step 2: Dense semantic search ───────────────────────────────
        dense_results: list[dict] = []
        try:
            query_vector = self._embedder.embed_one(query)
            dense_results = self._vector_store.search(
                query_vector=query_vector,
                repository_id=repository_id,
                top_k=self._cfg.top_k,
            )
            stats["dense_hits"] = len(dense_results)
        except Exception as exc:
            logger.warning("dense_search_failed", extra={"error": str(exc)})

        # ── Step 3: BM25 lexical search ──────────────────────────────────
        sparse_results: list[dict] = []
        bm25 = get_bm25_index(repository_id)
        if bm25 is None:
            # Attempt to warm up BM25 from DB if not in memory (e.g. after restart)
            bm25 = self._warm_bm25(db, repository_id)
        if bm25:
            # Search with both original query and expanded terms
            search_text = " ".join([query] + analysis.search_terms[:5])
            try:
                sparse_results = bm25.search(search_text, top_k=self._cfg.sparse_top_k)
                stats["sparse_hits"] = len(sparse_results)
            except Exception as exc:
                logger.warning("bm25_search_failed", extra={"error": str(exc)})

        # ── Step 4: Exact symbol search ──────────────────────────────────
        symbol_results: list[dict] = []
        if analysis.exact_symbol or analysis.search_terms:
            symbol_results = self._exact_symbol_search(
                db,
                repository_id,
                analysis.exact_symbol or analysis.search_terms[0],
            )
            stats["symbol_hits"] = len(symbol_results)

        # ── Step 5: RRF fusion ───────────────────────────────────────────
        # Normalise IDs — dense results use Qdrant UUIDs, DB results use symbol IDs
        # We harmonise on symbol_id from payload
        dense_norm = _normalise_qdrant_results(dense_results)
        fused = reciprocal_rank_fusion(dense_norm, sparse_results, symbol_results)
        stats["fused_hits"] = len(fused)

        # ── Step 6: Graph expansion ──────────────────────────────────────
        graph_neighbors: list[dict] = []
        try:
            graph = get_graph(db, repository_id)
            primary_ids = [
                item.get("payload", {}).get("symbol_id") or item["id"]
                for item in fused[: self._cfg.rerank_top_k]
            ]
            seen_nb: set[str] = set(primary_ids)
            for pid in primary_ids[:5]:  # expand top-5 primaries
                if not pid:
                    continue
                nb = graph.bounded_neighborhood(
                    pid,
                    depth=self._cfg.graph_expansion_depth,
                    limit=self._cfg.graph_expansion_limit // 5,
                )
                for n in nb:
                    if n["id"] not in seen_nb:
                        seen_nb.add(n["id"])
                        graph_neighbors.append(n)
            stats["graph_expansion_hits"] = len(graph_neighbors)
        except Exception as exc:
            logger.warning("graph_expansion_failed", extra={"error": str(exc)})

        # ── Step 7: Reranking ────────────────────────────────────────────
        ranked = rerank(fused, analysis, top_k=self._cfg.rerank_top_k)
        stats["reranked_hits"] = len(ranked)

        # ── Step 8: Context construction ─────────────────────────────────
        context = build_context(
            analysis=analysis,
            primary_candidates=ranked,
            graph_neighbors=graph_neighbors,
            repository_name=repository_name,
            repository_id=repository_id,
            settings=self._cfg,
        )

        logger.info("retrieval_complete", extra=stats)

        return RetrievalResult(
            analysis=analysis,
            candidates=ranked,
            graph_neighbors=graph_neighbors,
            context=context,
            stats=stats,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _warm_bm25(self, db: Session, repository_id: str):
        """Warm up BM25 from DB on cache miss (e.g., after restart)."""
        try:
            from app.indexing.symbol_indexer import SymbolIndexer  # noqa: PLC0415
            from app.models.orm import Symbol  # noqa: PLC0415

            symbols = (
                db.query(Symbol)
                .filter(Symbol.repository_id == repository_id)
                .all()
            )
            if symbols:
                indexer = SymbolIndexer(self._cfg)
                indexer.rebuild_bm25_from_db(repository_id, symbols)
                from app.indexing.lexical import get_bm25_index  # noqa: PLC0415

                return get_bm25_index(repository_id)
        except Exception as exc:
            logger.warning("bm25_warmup_failed", extra={"error": str(exc)})
        return None

    def _exact_symbol_search(
        self, db: Session, repository_id: str, name: str
    ) -> list[dict]:
        """Query the DB for exact or prefix symbol name matches."""
        try:
            from app.models.orm import Symbol  # noqa: PLC0415

            rows = (
                db.query(Symbol)
                .filter(
                    Symbol.repository_id == repository_id,
                    Symbol.symbol_name.ilike(f"%{name}%"),
                )
                .limit(self._cfg.symbol_top_k)
                .all()
            )
            return [
                {
                    "id": row.id,
                    "score": 1.0,
                    "payload": {
                        "symbol_id": row.id,
                        "repository_id": row.repository_id,
                        "symbol_name": row.symbol_name,
                        "qualified_name": row.qualified_name,
                        "symbol_type": row.symbol_type,
                        "file_path": row.file_path,
                        "start_line": row.start_line,
                        "end_line": row.end_line,
                        "language": row.language,
                        "documentation": row.documentation,
                        "code_snippet": row.code[:600] if row.code else "",
                    },
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("exact_symbol_search_failed", extra={"error": str(exc)})
            return []


def _normalise_qdrant_results(results: list[dict]) -> list[dict]:
    """Ensure Qdrant results use symbol_id as the unified 'id' field."""
    normalised = []
    for item in results:
        payload = item.get("payload", {})
        unified_id = payload.get("symbol_id") or item["id"]
        normalised.append({**item, "id": unified_id})
    return normalised
