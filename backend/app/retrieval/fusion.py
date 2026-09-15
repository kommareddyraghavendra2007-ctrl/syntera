"""
Reciprocal Rank Fusion (RRF) for combining ranked result lists.

RRF score: sum(1 / (k + rank_i)) for each ranked list i.

This is the standard approach for fusing incomparable score spaces
(e.g., cosine similarity from dense vectors vs. BM25 raw scores).
"""
from __future__ import annotations

_RRF_K = 60  # Standard constant from the original RRF paper


def reciprocal_rank_fusion(
    *ranked_lists: list[dict],
    k: int = _RRF_K,
) -> list[dict]:
    """
    Fuse multiple ranked result lists using RRF.

    Each list contains dicts with at minimum: {"id": str, "payload": dict}.
    Returns a unified ranked list sorted by descending RRF score.
    """
    rrf_scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            item_id = item["id"]
            rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + 1.0 / (k + rank)
            if item_id not in payloads:
                payloads[item_id] = item.get("payload", {})

    fused = [
        {"id": item_id, "score": score, "payload": payloads[item_id]}
        for item_id, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    ]
    return fused


def normalize_scores(results: list[dict]) -> list[dict]:
    """Min-max normalize scores to [0, 1] for display purposes only."""
    if not results:
        return results
    scores = [r["score"] for r in results]
    mn, mx = min(scores), max(scores)
    spread = mx - mn or 1.0
    return [
        {**r, "score": (r["score"] - mn) / spread}
        for r in results
    ]
