"""
Reranker — re-scores and re-orders retrieval candidates.

MVP implementation: rule-based reranking using signal boosting.
Production upgrade path: cross-encoder model (e.g. cross-encoder/ms-marco-MiniLM).

Signals applied:
1. Exact symbol name match → major boost
2. Qualified name contains all query terms → boost
3. Symbol type relevance (function/method/endpoint ranked higher for action queries)
4. Short file path (root-level files) → slight boost for architecture questions
5. Code documentation presence → small boost
"""
from __future__ import annotations

import re

from app.core.enums import QueryIntent, SymbolType
from app.retrieval.query import QueryAnalysis

# Symbol types preferred for each intent
_INTENT_TYPE_PREFERENCE: dict[str, list[str]] = {
    QueryIntent.SYMBOL_LOOKUP: [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS],
    QueryIntent.LOCATION: [SymbolType.FUNCTION, SymbolType.METHOD, SymbolType.CLASS, SymbolType.ENDPOINT],
    QueryIntent.FLOW: [SymbolType.ENDPOINT, SymbolType.METHOD, SymbolType.FUNCTION],
    QueryIntent.ARCHITECTURE: [SymbolType.CLASS, SymbolType.MODULE, SymbolType.FILE],
    QueryIntent.CONFIGURATION: [SymbolType.CONFIGURATION, SymbolType.FILE],
    QueryIntent.EXPLANATION: [SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.METHOD],
    QueryIntent.IMPACT: [SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.METHOD],
}


def rerank(
    candidates: list[dict],
    analysis: QueryAnalysis,
    top_k: int = 12,
) -> list[dict]:
    """Score and trim a candidate list to *top_k*."""
    if not candidates:
        return []

    preferred_types = _INTENT_TYPE_PREFERENCE.get(analysis.intent, [])
    terms_lower = [t.lower() for t in analysis.search_terms]

    scored = []
    for item in candidates:
        base = item.get("score", 0.0)
        payload = item.get("payload", {})
        boost = _compute_boost(payload, analysis, preferred_types, terms_lower)
        scored.append({**item, "rerank_score": base + boost})

    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[:top_k]


def _compute_boost(
    payload: dict,
    analysis: QueryAnalysis,
    preferred_types: list[str],
    terms_lower: list[str],
) -> float:
    boost = 0.0
    symbol_name: str = (payload.get("symbol_name") or "").lower()
    qualified: str = (payload.get("qualified_name") or "").lower()
    symbol_type: str = payload.get("symbol_type") or ""
    has_doc: bool = bool(payload.get("documentation"))

    # Exact symbol name match
    if analysis.exact_symbol and analysis.exact_symbol.lower() == symbol_name:
        boost += 1.5
    elif analysis.exact_symbol and analysis.exact_symbol.lower() in qualified:
        boost += 0.8

    # All search terms in qualified name
    if terms_lower and all(t in qualified for t in terms_lower):
        boost += 0.6
    elif terms_lower and any(t in symbol_name for t in terms_lower):
        boost += 0.3

    # Symbol type preference
    if symbol_type in preferred_types:
        idx = preferred_types.index(symbol_type)
        boost += 0.4 - idx * 0.05  # first preferred type gets most boost

    # Documentation present
    if has_doc:
        boost += 0.1

    return boost
