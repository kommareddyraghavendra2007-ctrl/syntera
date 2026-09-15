"""Tests for context builder and hallucination guards."""
from __future__ import annotations

import pytest
from app.retrieval.context_builder import _fits, build_context
from app.retrieval.query import QueryAnalysis
from app.core.enums import QueryIntent


def _analysis(q: str = "test?", intent: str = QueryIntent.LOCATION) -> QueryAnalysis:
    return QueryAnalysis(
        original=q, intent=intent, confidence=0.8,
        search_terms=["test"], expanded_terms=["test"],
        exact_symbol=None, is_multi_hop=False,
    )


def _candidate(name: str, file: str, start: int = 1, end: int = 10) -> dict:
    return {
        "id": name, "score": 0.9,
        "payload": {
            "symbol_id": name, "symbol_name": name, "qualified_name": name,
            "symbol_type": "function", "file_path": file,
            "start_line": start, "end_line": end, "language": "python",
            "code_snippet": f"def {name}(): pass",
        },
    }


def test_contains_repo_info():
    ctx = build_context(_analysis(), [], [], "MyRepo", "repo-999")
    assert "MyRepo" in ctx
    assert "repo-999" in ctx


def test_contains_question():
    ctx = build_context(_analysis("Where is auth?"), [], [], "R", "r1")
    assert "Where is auth?" in ctx


def test_contains_source_ref():
    candidates = [_candidate("AuthService", "src/auth/auth_service.py", 1, 50)]
    ctx = build_context(_analysis(), candidates, [], "R", "r1")
    assert "AuthService" in ctx
    assert "src/auth/auth_service.py" in ctx


def test_budget_respected():
    from app.core.config import Settings
    small = Settings(
        max_context_chars=300,
        database_url="sqlite:///test.db",
        qdrant_path="/tmp/q",
        work_dir="/tmp/w",
    )
    candidates = [_candidate(f"Sym{i}", f"file{i}.py") for i in range(30)]
    ctx = build_context(_analysis(), candidates, [], "R", "r1", settings=small)
    # Context should not massively exceed the budget
    assert len(ctx) < 300 * 5


def test_redacted_code_not_in_context():
    candidate = {
        "id": "s", "score": 0.9,
        "payload": {
            "symbol_id": "s", "symbol_name": "Cfg", "qualified_name": "Cfg",
            "symbol_type": "configuration", "file_path": ".env",
            "start_line": 1, "end_line": 2,
            "code_snippet": "[REDACTED — secret file]",
        },
    }
    ctx = build_context(_analysis(), [candidate], [], "R", "r1")
    assert "api_key =" not in ctx


def test_fits_helper():
    parts = ["x" * 100]
    assert _fits(parts, "y" * 50, 200)
    assert not _fits(parts, "y" * 200, 200)
