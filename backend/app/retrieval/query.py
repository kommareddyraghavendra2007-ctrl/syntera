"""
Query understanding module.

Classifies intent and expands the query into useful search representations
without making intent classification a hard dependency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.enums import QueryIntent
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueryAnalysis:
    original: str
    intent: QueryIntent
    confidence: float  # 0–1; low confidence → use multiple strategies
    search_terms: list[str]  # key identifiers to search
    expanded_terms: list[str]  # semantically expanded search texts
    exact_symbol: str | None  # set if query is clearly about one exact symbol
    is_multi_hop: bool  # requires chain traversal
    focus_files: list[str] = field(default_factory=list)


# Keyword patterns for intent classification
_INTENT_RULES: list[tuple[list[str], QueryIntent]] = [
    (["where is", "find", "locate", "which file", "where are", "implementation of"], QueryIntent.LOCATION),
    (["what does", "explain", "describe", "how does", "what is"], QueryIntent.EXPLANATION),
    (["architecture", "overview", "structure", "main module", "components"], QueryIntent.ARCHITECTURE),
    (["flow", "trace", "end-to-end", "step by step", "journey", "from.*to"], QueryIntent.FLOW),
    (["depends on", "dependency", "dependencies", "which files depend", "who uses"], QueryIntent.DEPENDENCY),
    (["impact", "affect", "if i change", "if i modify", "what breaks", "what would break"], QueryIntent.IMPACT),
    (["error", "bug", "fail", "exception", "crash", "broken", "debug"], QueryIntent.DEBUGGING),
    (["config", "configuration", "environment variable", "env var", "setting", ".env"], QueryIntent.CONFIGURATION),
    (["implement", "definition of", "implemented in", "declared in"], QueryIntent.SYMBOL_LOOKUP),
    (["documentation", "comment", "docstring", "readme"], QueryIntent.DOCUMENTATION),
    (["new developer", "onboarding", "getting started", "first", "understand"], QueryIntent.ONBOARDING),
    (["compare", "difference between", "vs", "versus", "similar"], QueryIntent.COMPARISON),
]

# Auth / login expansion
_SEMANTIC_EXPANSIONS: dict[str, list[str]] = {
    "login": ["authenticate", "signin", "sign_in", "loginUser", "AuthService", "LoginController"],
    "authentication": ["auth", "authenticate", "jwt", "token", "AuthService", "login", "signIn"],
    "register": ["signup", "registration", "createUser", "UserRegistration", "sign_up"],
    "user": ["UserService", "UserRepository", "UserController", "account"],
    "order": ["OrderService", "OrderRepository", "OrderController", "cart", "purchase"],
    "payment": ["PaymentService", "transaction", "billing", "checkout", "stripe"],
    "database": ["db", "repository", "dao", "datasource", "connection", "orm", "entity"],
    "token": ["jwt", "jwtService", "generateToken", "validateToken", "bearer"],
    "password": ["hash", "bcrypt", "passwordEncoder", "checkPassword"],
    "config": ["settings", "environment", "env", ".env", "properties"],
}


class QueryAnalyzer:
    """Classify intent and expand queries for multi-strategy retrieval."""

    def analyze(self, query: str) -> QueryAnalysis:
        q_lower = query.lower().strip()

        intent, confidence = self._classify(q_lower)
        exact_symbol = self._extract_exact_symbol(query)
        search_terms = self._extract_search_terms(query, exact_symbol)
        expanded = self._expand(q_lower, search_terms)
        is_multi_hop = self._is_multi_hop(q_lower)

        result = QueryAnalysis(
            original=query,
            intent=intent,
            confidence=confidence,
            search_terms=search_terms,
            expanded_terms=expanded,
            exact_symbol=exact_symbol,
            is_multi_hop=is_multi_hop,
        )
        logger.info(
            "query_analyzed",
            extra={
                "intent": intent,
                "confidence": confidence,
                "exact_symbol": exact_symbol,
                "multi_hop": is_multi_hop,
                "terms": search_terms[:5],
            },
        )
        return result

    def _classify(self, q: str) -> tuple[QueryIntent, float]:
        scores: dict[QueryIntent, int] = {}
        for keywords, intent in _INTENT_RULES:
            hits = sum(1 for kw in keywords if re.search(kw, q))
            if hits:
                scores[intent] = scores.get(intent, 0) + hits

        if not scores:
            return QueryIntent.GENERAL_CODEBASE_QA, 0.4

        best = max(scores, key=lambda k: scores[k])
        total_hits = scores[best]
        confidence = min(0.4 + total_hits * 0.2, 0.95)
        return best, confidence

    def _extract_exact_symbol(self, query: str) -> str | None:
        """Detect PascalCase, camelCase, or dotted.symbols in the query."""
        # Explicit backtick-quoted
        bt = re.search(r"`([A-Za-z_][\w.]*)`", query)
        if bt:
            return bt.group(1)
        # Quoted string
        qt = re.search(r'"([A-Za-z_][\w.]*)"', query)
        if qt:
            return qt.group(1)
        # PascalCase or dotted qualified names e.g. AuthService.authenticateUser
        camel = re.search(r"\b([A-Z][A-Za-z0-9]*(?:\.[a-z][A-Za-z0-9]*)+)\b", query)
        if camel:
            return camel.group(1)
        # Single PascalCase word that looks like a class name
        pascal = re.search(r"\b([A-Z][A-Za-z]{3,}Service|[A-Z][A-Za-z]{3,}Controller|[A-Z][A-Za-z]{3,}Repository|[A-Z][A-Za-z]{3,}Handler|[A-Z][A-Za-z]{3,}Manager)\b", query)
        if pascal:
            return pascal.group(1)
        return None

    def _extract_search_terms(self, query: str, exact: str | None) -> list[str]:
        terms = []
        if exact:
            terms.append(exact)
        # Collect meaningful identifiers from the query
        words = re.findall(r"[A-Za-z_][\w]*", query)
        stop = {
            "where", "is", "are", "the", "a", "an", "how", "does", "what",
            "which", "files", "file", "function", "method", "class", "in",
            "of", "to", "and", "or", "it", "this", "that", "for", "on",
            "with", "all", "find", "me", "show", "explain",
        }
        for w in words:
            if w.lower() not in stop and len(w) > 2 and w not in terms:
                terms.append(w)
        return terms[:10]

    def _expand(self, q_lower: str, terms: list[str]) -> list[str]:
        expanded = list(terms)
        for base, synonyms in _SEMANTIC_EXPANSIONS.items():
            if base in q_lower:
                for s in synonyms:
                    if s not in expanded:
                        expanded.append(s)
        # Add full query as a semantic embedding target
        if q_lower not in expanded:
            expanded.append(q_lower)
        return expanded[:20]

    def _is_multi_hop(self, q: str) -> bool:
        patterns = [
            r"trace",
            r"from.*to",
            r"end.to.end",
            r"complete.*flow",
            r"full.*flow",
            r"what.*happen.*when",
            r"journey",
            r"chain",
            r"path",
            r"step.*by.*step",
        ]
        return any(re.search(p, q) for p in patterns)
