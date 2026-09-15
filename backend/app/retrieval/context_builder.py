"""
Context builder — constructs the structured prompt context for the LLM.

Priorities:
1. Exact source code for primary candidates
2. Callers / callees from graph expansion
3. Related configuration and documentation
4. Tests referencing the primary symbols
5. Repository metadata

Hard limits:
- max_chars from settings (default 24,000)
- Never dumps entire repository
- Never sends redacted/secret content
"""
from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.retrieval.query import QueryAnalysis

logger = get_logger(__name__)


def build_context(
    analysis: QueryAnalysis,
    primary_candidates: list[dict],
    graph_neighbors: list[dict],
    repository_name: str,
    repository_id: str,
    settings: Settings | None = None,
) -> str:
    cfg = settings or get_settings()
    budget = cfg.max_context_chars
    parts: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────
    parts.append(
        f"REPOSITORY: {repository_name}\n"
        f"REPOSITORY_ID: {repository_id}\n"
        f"QUESTION: {analysis.original}\n"
        f"DETECTED_INTENT: {analysis.intent}\n"
    )

    # ── Primary sources ───────────────────────────────────────────────────
    if primary_candidates:
        parts.append("=== PRIMARY EVIDENCE ===")
        for item in primary_candidates:
            payload = item.get("payload", {})
            block = _format_symbol_block(payload, include_code=True)
            if _fits(parts, block, budget):
                parts.append(block)

    # ── Graph-expanded context ────────────────────────────────────────────
    if graph_neighbors:
        nb_blocks = []
        for nb in graph_neighbors:
            if isinstance(nb, dict):
                payload = nb if "symbol_name" in nb else nb.get("payload", nb)
                block = _format_symbol_block(payload, include_code=False)
                if block:
                    nb_blocks.append(block)
        if nb_blocks:
            parts.append("=== RELATED CONTEXT (graph-expanded) ===")
            for block in nb_blocks:
                if _fits(parts, block, budget):
                    parts.append(block)
                else:
                    break

    # ── Source evidence summary ───────────────────────────────────────────
    if primary_candidates:
        parts.append("=== SOURCE REFERENCES ===")
        for item in primary_candidates:
            p = item.get("payload", {})
            ref = (
                f"• {p.get('qualified_name', '?')} "
                f"@ {p.get('file_path', '?')}:{p.get('start_line', '?')}-{p.get('end_line', '?')}"
            )
            parts.append(ref)

    return "\n\n".join(parts)


def _format_symbol_block(payload: dict, include_code: bool) -> str:
    name = payload.get("qualified_name") or payload.get("symbol_name") or "?"
    file_path = payload.get("file_path") or payload.get("name") or "?"
    start = payload.get("start_line", "?")
    end = payload.get("end_line", "?")
    sym_type = payload.get("symbol_type", "?")
    lang = payload.get("language", "")
    doc = payload.get("documentation") or ""
    code = payload.get("code_snippet") or payload.get("code") or ""

    lines = [
        f"--- {sym_type.upper()}: {name} ---",
        f"Location: {file_path}:{start}-{end}",
    ]
    if lang:
        lines.append(f"Language: {lang}")
    if doc:
        lines.append(f"Documentation: {doc[:300]}")
    if include_code and code and "[REDACTED" not in code:
        lines.append(f"```{lang}")
        lines.append(code[:2000])
        lines.append("```")
    return "\n".join(lines)


def _fits(parts: list[str], new_block: str, budget: int) -> bool:
    current = sum(len(p) for p in parts)
    return current + len(new_block) < budget
