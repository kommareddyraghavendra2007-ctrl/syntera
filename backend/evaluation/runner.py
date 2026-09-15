"""
Evaluation runner — evaluates retrieval quality against the golden benchmark.

Usage:
  python -m evaluation.run --repository-id <id> [--k 10]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from evaluation.benchmark import GOLDEN_BENCHMARK
from evaluation.metrics import (
    EvaluationReport,
    QuestionResult,
    aggregate_results,
    citation_accuracy,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def run_evaluation(
    repository_id: str,
    k: int = 10,
    backend_url: str = "http://localhost:8000",
) -> EvaluationReport:
    """Run all benchmark questions against a live SYNTERA backend."""
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx required. pip install httpx", file=sys.stderr)
        sys.exit(1)

    results: list[QuestionResult] = []
    client = httpx.Client(base_url=backend_url, timeout=60)

    print(f"\nSYNTERA Evaluation — Repository: {repository_id}")
    print(f"Questions: {len(GOLDEN_BENCHMARK)}  |  K={k}")
    print("=" * 60)

    for i, bq in enumerate(GOLDEN_BENCHMARK, start=1):
        label = bq.question[:55]
        print(f"[{i:2d}/{len(GOLDEN_BENCHMARK)}] {label:<55}", end=" ", flush=True)

        start = time.monotonic()
        error: str | None = None
        retrieved_symbols: list[str] = []
        retrieved_files: list[str] = []

        try:
            resp = client.post(
                f"/api/repositories/{repository_id}/query",
                json={"question": bq.question},
            )
            resp.raise_for_status()
            data = resp.json()
            citations = data.get("citations", [])
            retrieved_symbols = [
                c.get("symbol_name") or c.get("qualified_name") or ""
                for c in citations
            ]
            retrieved_files = [c.get("file_path", "") for c in citations]
        except Exception as exc:
            error = str(exc)
            print(f"ERROR: {exc}")

        latency_ms = (time.monotonic() - start) * 1000

        r_at_k = recall_at_k(bq.expected_symbols, retrieved_symbols, k)
        p_at_k = precision_at_k(bq.expected_symbols, retrieved_symbols, k)
        mrr = mean_reciprocal_rank(bq.expected_symbols, retrieved_symbols)
        cit_acc = citation_accuracy(bq.expected_files, retrieved_files)

        if not error:
            print(f"R@{k}={r_at_k:.2f}  MRR={mrr:.2f}  Cit={cit_acc:.2f}  {latency_ms:.0f}ms")

        results.append(
            QuestionResult(
                question=bq.question,
                category=bq.category,
                intent=bq.intent,
                recall_at_k=r_at_k,
                precision_at_k=p_at_k,
                mrr=mrr,
                citation_accuracy=cit_acc,
                retrieved_symbols=retrieved_symbols,
                retrieved_files=retrieved_files,
                expected_symbols=bq.expected_symbols,
                expected_files=bq.expected_files,
                latency_ms=latency_ms,
                error=error,
            )
        )

    report = aggregate_results(results)
    _print_report(report, k)
    return report


def _print_report(report: EvaluationReport, k: int) -> None:
    print("\n" + "=" * 60)
    print("SYNTERA EVALUATION REPORT")
    print("=" * 60)
    print(f"Total questions : {report.total_questions}")
    print(f"Recall@{k:<4}     : {report.overall_recall_at_k:.3f}")
    print(f"Precision@{k:<2}   : {report.overall_precision_at_k:.3f}")
    print(f"MRR             : {report.overall_mrr:.3f}")
    print(f"Citation Acc    : {report.overall_citation_accuracy:.3f}")
    print(f"Avg latency     : {report.avg_latency_ms:.0f}ms")
    print(f"Error rate      : {report.error_rate:.1%}")
    print()
    print("By category:")
    for cat, metrics in sorted(report.by_category.items()):
        print(
            f"  {cat:20s}  R@K={metrics['recall_at_k']:.2f}"
            f"  MRR={metrics['mrr']:.2f}"
            f"  Cit={metrics['citation_accuracy']:.2f}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SYNTERA Retrieval Evaluation")
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--output", help="Save JSON report to this path")
    args = parser.parse_args()

    report = run_evaluation(
        repository_id=args.repository_id,
        k=args.k,
        backend_url=args.backend_url,
    )

    if args.output:
        out = {
            "total_questions": report.total_questions,
            "overall_recall_at_k": report.overall_recall_at_k,
            "overall_mrr": report.overall_mrr,
            "overall_citation_accuracy": report.overall_citation_accuracy,
            "avg_latency_ms": report.avg_latency_ms,
            "by_category": report.by_category,
        }
        Path(args.output).write_text(json.dumps(out, indent=2))
        print(f"\nReport saved → {args.output}")
