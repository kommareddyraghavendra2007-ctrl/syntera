"""
NetworkX-backed code relationship graph.

Abstraction layer: all callers use CodeGraph. The underlying engine
(NetworkX today, Neo4j later) is an implementation detail.

Node attributes  : id, name, symbol_type, file_path, start_line, end_line, language
Edge attributes  : relation_type, confidence, source (evidence string)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from app.core.enums import RelationType
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GraphNode:
    id: str
    name: str
    symbol_type: str
    file_path: str
    start_line: int
    end_line: int
    language: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relation_type: str
    confidence: float = 1.0
    evidence: str | None = None


class CodeGraph:
    """In-memory directed graph for one repository revision.

    Designed to be built once per repository and cached by the GraphService.
    """

    def __init__(self, repository_id: str) -> None:
        self.repository_id = repository_id
        self._g: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        self._g.add_node(
            node.id,
            name=node.name,
            symbol_type=node.symbol_type,
            file_path=node.file_path,
            start_line=node.start_line,
            end_line=node.end_line,
            language=node.language,
            **node.extra,
        )

    def add_edge(self, edge: GraphEdge) -> None:
        if not self._g.has_node(edge.source):
            self._g.add_node(edge.source, name=edge.source)
        if not self._g.has_node(edge.target):
            self._g.add_node(edge.target, name=edge.target)
        self._g.add_edge(
            edge.source,
            edge.target,
            relation_type=edge.relation_type,
            confidence=edge.confidence,
            evidence=edge.evidence,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return self._g.number_of_nodes()

    def edge_count(self) -> int:
        return self._g.number_of_edges()

    def get_node(self, node_id: str) -> dict | None:
        if not self._g.has_node(node_id):
            return None
        return {"id": node_id, **self._g.nodes[node_id]}

    def find_nodes_by_name(self, name: str) -> list[dict]:
        """Exact or partial name match across all nodes."""
        results = []
        name_lower = name.lower()
        for nid, data in self._g.nodes(data=True):
            node_name: str = data.get("name", "")
            if name_lower in node_name.lower():
                results.append({"id": nid, **data})
        return results

    def callers(self, node_id: str) -> list[dict]:
        """Return all nodes that CALL this node."""
        results = []
        for src, _, data in self._g.in_edges(node_id, data=True):
            if data.get("relation_type") == RelationType.CALLS:
                node = self.get_node(src)
                if node:
                    results.append(node)
        return results

    def callees(self, node_id: str) -> list[dict]:
        """Return all nodes that this node CALLS."""
        results = []
        for _, tgt, data in self._g.out_edges(node_id, data=True):
            if data.get("relation_type") == RelationType.CALLS:
                node = self.get_node(tgt)
                if node:
                    results.append(node)
        return results

    def dependents(self, node_id: str, rel_types: set[str] | None = None) -> list[dict]:
        """Nodes that directly depend on (point to) this node."""
        rel_types = rel_types or {
            RelationType.CALLS,
            RelationType.IMPORTS,
            RelationType.USES,
            RelationType.REFERENCES,
        }
        results = []
        for src, _, data in self._g.in_edges(node_id, data=True):
            if data.get("relation_type") in rel_types:
                node = self.get_node(src)
                if node:
                    results.append(node)
        return results

    def dependencies(self, node_id: str, rel_types: set[str] | None = None) -> list[dict]:
        """Nodes that this node directly depends on."""
        rel_types = rel_types or {
            RelationType.CALLS,
            RelationType.IMPORTS,
            RelationType.USES,
            RelationType.REFERENCES,
        }
        results = []
        for _, tgt, data in self._g.out_edges(node_id, data=True):
            if data.get("relation_type") in rel_types:
                node = self.get_node(tgt)
                if node:
                    results.append(node)
        return results

    def bounded_neighborhood(
        self,
        node_id: str,
        depth: int = 2,
        limit: int = 24,
        rel_types: set[str] | None = None,
    ) -> list[dict]:
        """BFS expansion up to *depth* hops, capped at *limit* nodes.

        Returns neighboring nodes (excluding the seed itself).
        """
        if not self._g.has_node(node_id):
            return []

        visited: set[str] = {node_id}
        frontier: list[str] = [node_id]
        results: list[dict] = []

        for _ in range(depth):
            next_frontier: list[str] = []
            for nid in frontier:
                for neighbor in list(self._g.successors(nid)) + list(self._g.predecessors(nid)):
                    if neighbor in visited:
                        continue
                    edge_data = (
                        self._g.get_edge_data(nid, neighbor)
                        or self._g.get_edge_data(neighbor, nid)
                        or {}
                    )
                    if rel_types and edge_data.get("relation_type") not in rel_types:
                        continue
                    visited.add(neighbor)
                    node = self.get_node(neighbor)
                    if node:
                        results.append(node)
                        next_frontier.append(neighbor)
                    if len(results) >= limit:
                        return results
            frontier = next_frontier
            if not frontier:
                break

        return results

    def impact_set(
        self,
        node_id: str,
        depth: int = 3,
        limit: int = 30,
    ) -> dict[str, list[dict]]:
        """Return direct + indirect dependents for impact analysis."""
        direct = self.dependents(node_id)
        indirect: list[dict] = []
        seen = {node_id} | {n["id"] for n in direct}

        frontier = [n["id"] for n in direct]
        for _ in range(depth - 1):
            next_frontier = []
            for nid in frontier:
                for dep in self.dependents(nid):
                    if dep["id"] not in seen:
                        seen.add(dep["id"])
                        indirect.append(dep)
                        next_frontier.append(dep["id"])
                        if len(indirect) >= limit:
                            break
                if len(indirect) >= limit:
                    break
            frontier = next_frontier

        return {"direct": direct, "indirect": indirect}

    def subgraph_for_visualization(
        self,
        root_ids: list[str],
        depth: int = 2,
        limit: int = 60,
    ) -> dict:
        """Return {nodes, edges} suitable for React Flow rendering."""
        collected: set[str] = set()
        frontier = list(root_ids)
        for nid in frontier:
            if self._g.has_node(nid):
                collected.add(nid)

        for _ in range(depth):
            next_f = []
            for nid in frontier:
                for nb in list(self._g.successors(nid)) + list(self._g.predecessors(nid)):
                    if nb not in collected:
                        collected.add(nb)
                        next_f.append(nb)
                    if len(collected) >= limit:
                        break
                if len(collected) >= limit:
                    break
            frontier = next_f
            if not frontier or len(collected) >= limit:
                break

        nodes = []
        for nid in collected:
            data = self._g.nodes.get(nid, {})
            nodes.append({
                "id": nid,
                "label": data.get("name", nid),
                "symbol_type": data.get("symbol_type", "unknown"),
                "file_path": data.get("file_path", ""),
                "start_line": data.get("start_line", 0),
                "language": data.get("language"),
            })

        edges = []
        for src, tgt, data in self._g.edges(data=True):
            if src in collected and tgt in collected:
                edges.append({
                    "source": src,
                    "target": tgt,
                    "relation_type": data.get("relation_type", ""),
                    "confidence": data.get("confidence", 1.0),
                })

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "repository_id": self.repository_id,
            "node_count": self.node_count(),
            "edge_count": self.edge_count(),
        }
