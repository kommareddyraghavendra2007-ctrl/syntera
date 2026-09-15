"""Tests for CodeGraph store."""
from __future__ import annotations

import pytest
from app.graph.store import CodeGraph, GraphEdge, GraphNode
from app.core.enums import RelationType, SymbolType


def _make_graph() -> CodeGraph:
    g = CodeGraph("repo-test")
    g.add_node(GraphNode(id="auth-svc", name="AuthService", symbol_type=SymbolType.CLASS,
                         file_path="src/auth/auth_service.py", start_line=10, end_line=80))
    g.add_node(GraphNode(id="jwt-svc", name="JWTService", symbol_type=SymbolType.CLASS,
                         file_path="src/auth/jwt_service.py", start_line=1, end_line=60))
    g.add_node(GraphNode(id="user-repo", name="UserRepository", symbol_type=SymbolType.CLASS,
                         file_path="src/users/user_repository.py", start_line=1, end_line=50))
    g.add_node(GraphNode(id="login-fn", name="AuthService.login", symbol_type=SymbolType.METHOD,
                         file_path="src/auth/auth_service.py", start_line=40, end_line=60))
    g.add_edge(GraphEdge("login-fn", "jwt-svc", RelationType.CALLS, confidence=0.9))
    g.add_edge(GraphEdge("login-fn", "user-repo", RelationType.CALLS, confidence=0.85))
    g.add_edge(GraphEdge("auth-svc", "login-fn", RelationType.CONTAINS))
    return g


def test_node_count():
    assert _make_graph().node_count() == 4


def test_edge_count():
    assert _make_graph().edge_count() == 3


def test_find_nodes_by_name():
    g = _make_graph()
    results = g.find_nodes_by_name("AuthService")
    assert any(r["name"] == "AuthService" for r in results)


def test_callees():
    g = _make_graph()
    names = {c["name"] for c in g.callees("login-fn")}
    assert "JWTService" in names
    assert "UserRepository" in names


def test_callers():
    g = _make_graph()
    assert any(c["id"] == "login-fn" for c in g.callers("jwt-svc"))


def test_bounded_neighborhood():
    g = _make_graph()
    nb = g.bounded_neighborhood("login-fn", depth=2, limit=10)
    ids = {n["id"] for n in nb}
    assert "jwt-svc" in ids or "user-repo" in ids


def test_limit_respected():
    g = _make_graph()
    nb = g.bounded_neighborhood("auth-svc", depth=4, limit=1)
    assert len(nb) <= 1


def test_impact_set():
    g = _make_graph()
    impact = g.impact_set("jwt-svc")
    assert any(n["id"] == "login-fn" for n in impact["direct"])


def test_subgraph_visualization():
    g = _make_graph()
    viz = g.subgraph_for_visualization(["auth-svc"], depth=2, limit=20)
    assert "nodes" in viz and "edges" in viz
    assert any(n["id"] == "auth-svc" for n in viz["nodes"])


def test_missing_node_returns_none():
    assert _make_graph().get_node("does-not-exist") is None


def test_repository_isolation():
    g_a = CodeGraph("repo-a")
    g_b = CodeGraph("repo-b")
    g_a.add_node(GraphNode(id="n-a", name="ServiceA", symbol_type="class",
                           file_path="a.py", start_line=1, end_line=10))
    g_b.add_node(GraphNode(id="n-b", name="ServiceB", symbol_type="class",
                           file_path="b.py", start_line=1, end_line=10))
    assert g_a.find_nodes_by_name("ServiceB") == []
    assert g_b.find_nodes_by_name("ServiceA") == []
