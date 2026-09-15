"""
Retrieval quality metrics.

Implements:
  - Recall@K: fraction of expected symbols found in top-K results
  - Precision@K: fraction of top-K results that are relevant
  - MRR: Mean Reciprocal Rank of first relevant result
  - Citation accuracy: fraction of expected files found in citations
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class QuestionResult:
    question: str
    category: str
    intent: str
    recall_at_k: float
    precision_at_k: float
    mrr: float
    citation_accuracy: float
    retrieved_symbols: list[str]
    retrieved_files: list[str]
    expected_symbols: list[str]
    expected_files: list[str]
    latency_ms: float
    error: str | None = None


@dataclass
class EvaluationReport:
    total_questions: int
    by_category: dict[str, dict] = field(default_factory=dict)
    overall_recall_at_k: float = 0.0
    overall_precision_at_k: float = 0.0
    overall_mrr: float = 0.0
    overall_citation_accuracy: float = 0.0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    results: list[QuestionResult] = field(default_factory=list)


def recall_at_k(expected: list[str], retrieved: list[str], k: int) -> float:
    """Fraction of expected items found in top-K retrieved."""
    if not expected:
        return 1.0  # vacuously true
    top_k = set(retrieved[:k])
    expected_lower = {e.lower() for e in expected}
    hits = sum(1 for e in expected_lower if any(e in r.lower() for r in top_k))
    return hits / len(expected)


def precision_at_k(expected: list[str], retrieved: list[str], k: int) -> float:
    """Fraction of top-K retrieved that are relevant."""
    if not retrieved or k == 0:
        return 0.0
    top_k = retrieved[:k]
    expected_lower = {e.lower() for e in expected}
    hits = sum(1 for r in top_k if any(e in r.lower() for e in expected_lower))
    return hits / min(k, len(top_k))


def mean_reciprocal_rank(expected: list[str], retrieved: list[str]) -> float:
    """MRR: 1/rank of first relevant result."""
    if not expected:
        return 1.0
    expected_lower = {e.lower() for e in expected}
    for rank, item in enumerate(retrieved, start=1):
        if any(e in item.lower() for e in expected_lower):
            return 1.0 / rank
    return 0.0


def citation_accuracy(expected_files: list[str], cited_files: list[str]) -> float:
    """Fraction of expected files that appear in citations."""
    if not expected_files:
        return 1.0
    cited_lower = {f.lower() for f in cited_files}
    hits = sum(1 for ef in expected_files if any(ef.lower() in cf for cf in cited_lower))
    return hits / len(expected_files)


def aggregate_results(results: list[QuestionResult]) -> EvaluationReport:
    if not results:
        return EvaluationReport(total_questions=0)

    report = EvaluationReport(total_questions=len(results), results=results)
    report.overall_recall_at_k = sum(r.recall_at_k for r in results) / len(results)
    report.overall_precision_at_k = sum(r.precision_at_k for r in results) / len(results)
    report.overall_mrr = sum(r.mrr for r in results) / len(results)
    report.overall_citation_accuracy = sum(r.citation_accuracy for r in results) / len(results)
    report.avg_latency_ms = sum(r.latency_ms for r in results) / len(results)
    report.error_rate = sum(1 for r in results if r.error) / len(results)

    # Group by category
    categories: dict[str, list[QuestionResult]] = {}
    for r in results:
        categories.setdefault(r.category, []).append(r)
    for cat, cat_results in categories.items():
        report.by_category[cat] = {
            "count": len(cat_results),
            "recall_at_k": sum(r.recall_at_k for r in cat_results) / len(cat_results),
            "mrr": sum(r.mrr for r in cat_results) / len(cat_results),
            "citation_accuracy": sum(r.citation_accuracy for r in cat_results) / len(cat_results),
        }
    return report
