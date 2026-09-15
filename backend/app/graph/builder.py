"""
Build a CodeGraph from persisted ORM data.

Called after ingestion has committed all Symbol + CodeRelationship rows.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.graph.store import CodeGraph, GraphEdge, GraphNode
from app.models.orm import CodeRelationship, Symbol

logger = get_logger(__name__)


def build_graph_from_db(db: Session, repository_id: str) -> CodeGraph:
    """Load all symbols and relationships for *repository_id* into a CodeGraph."""
    graph = CodeGraph(repository_id)

    symbols: list[Symbol] = (
        db.query(Symbol)
        .filter(Symbol.repository_id == repository_id)
        .all()
    )
    for sym in symbols:
        graph.add_node(
            GraphNode(
                id=sym.id,
                name=sym.qualified_name,
                symbol_type=sym.symbol_type,
                file_path=sym.file_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                language=sym.language,
            )
        )

    rels: list[CodeRelationship] = (
        db.query(CodeRelationship)
        .filter(CodeRelationship.repository_id == repository_id)
        .all()
    )
    for rel in rels:
        src = rel.source_symbol_id or rel.source_name
        tgt = rel.target_symbol_id or rel.target_name
        if src and tgt:
            graph.add_edge(
                GraphEdge(
                    source=src,
                    target=tgt,
                    relation_type=rel.relation_type,
                    confidence=rel.confidence,
                    evidence=rel.evidence,
                )
            )

    logger.info(
        "graph_built",
        extra={
            "repository_id": repository_id,
            "nodes": graph.node_count(),
            "edges": graph.edge_count(),
        },
    )
    return graph
