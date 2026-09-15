"""Tests for retrieval: RRF fusion, query analysis, reranker."""
from __future__ import annotations

import pytest
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.query import QueryAnalyzer
from app.retrieval.reranker import rerank
from app.core.enums import QueryIntent


def _r(id: str, score: float, name: str = "", file: str = "", sym_type: str = "function") -> dict:
    return {
        "id": id, "score": score,
        "payload": {
            "symbol_id": id, "symbol_name": name, "qualified_name": name,
            "symbol_type": sym_type, "file_path": file, "start_line": 1, "end_line": 10,
        }
    }


# RRF -----------------------------------------------------------------------

def test_rrf_single_list_preserves_order():
    fused = reciprocal_rank_fusion([_r("a", 0.9), _r("b", 0.8)])
    assert fused[0]["id"] == "a"


def test_rrf_boosts_common_items():
    l1 = [_r("a", 0.9), _r("b", 0.7)]
    l2 = [_r("b", 0.95), _r("c", 0.8)]
    fused = reciprocal_rank_fusion(l1, l2)
    assert fused[0]["id"] == "b"  # "b" in both lists should win


def test_rrf_empty():
    assert reciprocal_rank_fusion([], []) == []


def test_rrf_positive_scores():
    fused = reciprocal_rank_fusion([_r(f"i{i}", float(i)) for i in range(5)])
    assert all(r["score"] > 0 for r in fused)


# Query analyzer ------------------------------------------------------------

def test_location_intent():
    a = QueryAnalyzer().analyze("Where is authentication implemented?")
    assert a.intent == QueryIntent.LOCATION
    assert a.confidence > 0.4


def test_flow_intent_and_multi_hop():
    a = QueryAnalyzer().analyze("Trace the complete login flow end-to-end")
    assert a.intent == QueryIntent.FLOW
    assert a.is_multi_hop is True


def test_impact_intent():
    a = QueryAnalyzer().analyze("What could be affected if I modify AuthService?")
    assert a.intent == QueryIntent.IMPACT


def test_exact_symbol_extraction():
    a = QueryAnalyzer().analyze("Find the implementation of AuthService.login")
    assert a.exact_symbol is not None
    assert "AuthService" in a.exact_symbol


def test_search_terms_extracted():
    a = QueryAnalyzer().analyze("Where is JWT validation performed?")
    terms_lower = [t.lower() for t in a.search_terms]
    assert any("jwt" in t for t in terms_lower)


def test_auth_expansion():
    a = QueryAnalyzer().analyze("How does authentication work?")
    expanded_lower = [t.lower() for t in a.expanded_terms]
    assert any("auth" in t for t in expanded_lower)


def test_unknown_falls_back_to_general():
    a = QueryAnalyzer().analyze("xyzzy frobble quux123")
    assert a.intent == QueryIntent.GENERAL_CODEBASE_QA


# Reranker ------------------------------------------------------------------

def test_rerank_exact_symbol_boost():
    from app.retrieval.query import QueryAnalysis
    analysis = QueryAnalysis(
        original="Find AuthService", intent=QueryIntent.SYMBOL_LOOKUP,
        confidence=0.9, search_terms=["AuthService"], expanded_terms=["AuthService"],
        exact_symbol="AuthService", is_multi_hop=False,
    )
    candidates = [
        _r("match", 0.5, name="AuthService", sym_type="class"),
        _r("other", 0.8, name="SomeOtherService", sym_type="class"),
    ]
    ranked = rerank(candidates, analysis, top_k=5)
    assert ranked[0]["id"] == "match"


def test_rerank_top_k_respected():
    from app.retrieval.query import QueryAnalysis
    analysis = QueryAnalysis(
        original="anything", intent=QueryIntent.GENERAL_CODEBASE_QA,
        confidence=0.4, search_terms=[], expanded_terms=[],
        exact_symbol=None, is_multi_hop=False,
    )
    candidates = [_r(f"i{n}", float(n)) for n in range(20)]
    assert len(rerank(candidates, analysis, top_k=5)) <= 5
