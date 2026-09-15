"""Graph and architecture API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ready_repository
from app.graph.service import get_graph
from app.models.orm import Repository
from app.schemas.graph import GraphData, GraphEdgeData, GraphNodeData

router = APIRouter(prefix="/repositories/{repository_id}", tags=["graph"])


@router.get("/graph", response_model=GraphData)
def get_repository_graph(
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
    root_symbol: str | None = Query(None, description="Qualified name to root the graph on"),
    depth: int = Query(2, ge=1, le=4),
    limit: int = Query(60, ge=5, le=200),
):
    """Return a subgraph for visualization."""
    graph = get_graph(db, repo.id)

    if root_symbol:
        # Find matching nodes
        matching = graph.find_nodes_by_name(root_symbol)
        if not matching:
            raise HTTPException(status_code=404, detail=f"Symbol '{root_symbol}' not found in graph")
        root_ids = [n["id"] for n in matching[:3]]
    else:
        # Return a representative top-level subgraph
        # Find class and function nodes as roots
        from app.core.enums import SymbolType  # noqa: PLC0415

        all_nodes = list(graph._g.nodes(data=True))
        class_nodes = [
            nid for nid, data in all_nodes
            if data.get("symbol_type") in {SymbolType.CLASS, SymbolType.MODULE, SymbolType.FILE}
        ][:10]
        root_ids = class_nodes or [nid for nid, _ in all_nodes[:5]]

    raw = graph.subgraph_for_visualization(root_ids, depth=depth, limit=limit)

    nodes = [
        GraphNodeData(
            id=n["id"],
            label=n.get("label", n["id"]),
            symbol_type=n.get("symbol_type", "unknown"),
            file_path=n.get("file_path", ""),
            start_line=n.get("start_line", 0),
            language=n.get("language"),
        )
        for n in raw.get("nodes", [])
    ]
    edges = [
        GraphEdgeData(
            source=e["source"],
            target=e["target"],
            relation_type=e.get("relation_type", ""),
            confidence=e.get("confidence", 1.0),
        )
        for e in raw.get("edges", [])
    ]

    return GraphData(
        nodes=nodes,
        edges=edges,
        repository_id=repo.id,
        root_symbol=root_symbol,
    )


@router.get("/graph/impact/{symbol_id}", response_model=dict)
def get_impact_analysis(
    symbol_id: str,
    repo: Repository = Depends(get_ready_repository),
    db: Session = Depends(get_db),
):
    """Return impact analysis for a symbol — what might be affected by changing it."""
    graph = get_graph(db, repo.id)
    impact = graph.impact_set(symbol_id, depth=3, limit=30)

    return {
        "symbol_id": symbol_id,
        "repository_id": repo.id,
        "direct_dependents": impact["direct"],
        "indirect_dependents": impact["indirect"],
        "note": "POTENTIAL IMPACT — not guaranteed breakage. Static analysis only.",
    }
