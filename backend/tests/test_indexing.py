"""Tests for BM25 indexing and lexical search."""
from __future__ import annotations

import pytest
from app.indexing.lexical import BM25Document, BM25Index, get_bm25_index, set_bm25_index, tokenize


def test_tokenize_camel():
    tokens = tokenize("authenticateUser")
    assert "authenticate" in tokens
    assert "user" in tokens


def test_tokenize_snake():
    tokens = tokenize("user_repository")
    assert "user" in tokens
    assert "repository" in tokens


def _doc(symbol_id: str, name: str, file: str, repo: str = "r1") -> BM25Document:
    return BM25Document(
        symbol_id=symbol_id, repository_id=repo, symbol_name=name,
        qualified_name=name, symbol_type="class", file_path=file,
        start_line=1, end_line=50, language="python",
        # Match the format used by SymbolIndexer: qualified_name + symbol_name + file_path
        text=f"{name} {name} {file} {name.lower()}",
    )


def test_search_finds_name():
    idx = BM25Index("r1")
    idx.build([
        _doc("a", "AuthService", "src/auth/auth_service.py"),
        _doc("b", "UserService", "src/users/user_service.py"),
        _doc("c", "OrderService", "src/orders/order_service.py"),
        _doc("d", "ProductRepository", "src/catalog/product_repo.py"),
    ])
    results = idx.search("AuthService", top_k=5)
    assert results, "Expected BM25 results for 'AuthService'"
    assert results[0]["payload"]["symbol_name"] == "AuthService"


def test_search_empty_index():
    idx = BM25Index("r1")
    idx.build([])
    assert idx.search("anything") == []


def test_repository_isolation():
    idx_a = BM25Index("repo-a")
    idx_a.build([_doc("s-a", "ServiceA", "a.py", repo="repo-a")])
    set_bm25_index(idx_a)

    idx_b = BM25Index("repo-b")
    idx_b.build([_doc("s-b", "ServiceB", "b.py", repo="repo-b")])
    set_bm25_index(idx_b)

    results_a = get_bm25_index("repo-a").search("ServiceA")
    assert all(r["payload"]["symbol_name"] != "ServiceB" for r in results_a)

    results_b = get_bm25_index("repo-b").search("ServiceB")
    assert all(r["payload"]["symbol_name"] != "ServiceA" for r in results_b)
