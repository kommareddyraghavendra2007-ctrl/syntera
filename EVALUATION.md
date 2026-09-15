# SYNTERA Evaluation

## Overview

SYNTERA includes a retrieval quality evaluation framework that measures how accurately the hybrid retrieval pipeline finds relevant code when answering natural-language questions.

## Metrics

| Metric | Definition |
|---|---|
| **Recall@K** | Fraction of expected symbols found in the top-K retrieved results |
| **Precision@K** | Fraction of top-K results that are relevant |
| **MRR** | Mean Reciprocal Rank — 1/rank of the first relevant result |
| **Citation Accuracy** | Fraction of expected file paths appearing in citations |
| **Avg Latency** | Mean end-to-end query latency in milliseconds |

## Running the Evaluation

```bash
# 1. Start the backend
cd backend && uvicorn app.main:app --port 8000

# 2. Index the golden repository via the UI or API:
curl -X POST http://localhost:8000/api/repositories \
  -H "Content-Type: application/json" \
  -d '{"url": "file:///path/to/SYNTERA/golden_repo"}'
# Or upload golden_repo as a ZIP

# 3. Run evaluation (replace <id> with the repository ID from step 2)
cd backend
python -m evaluation.run --repository-id <id> --k 10

# 4. Save results
python -m evaluation.run --repository-id <id> --k 10 --output results.json
```

## Benchmark Questions

The benchmark (`evaluation/benchmark.py`) contains 17 labeled questions against the ShopCore golden repository:

| Category | Count |
|---|---|
| location | 3 |
| flow | 4 |
| configuration | 2 |
| dependency | 3 |
| explanation | 1 |
| architecture | 1 |
| symbol_lookup | 1 |
| onboarding | 1 |
| impact | 1 |

## Expected Performance

With OpenAI embeddings (`text-embedding-3-small`) and the golden repository:

- Recall@10 ≥ 0.70
- MRR ≥ 0.60
- Citation Accuracy ≥ 0.65

With hash embeddings (development default), semantic retrieval quality is lower but BM25 and exact symbol search compensate for exact identifier queries.

**Important:** Do not report performance numbers without actually running the benchmark. Numbers above are targets, not claims.

## Demo Flow (Hackathon)

1. Add ShopCore golden repository
2. Wait for READY status (watch progress bar)
3. Ask: "Where is authentication implemented?" → verify `src/auth/auth_service.py` cited
4. Ask: "Explain the complete login flow" → verify multi-step chain with citations
5. Ask: "What could be affected if AuthService changes?" → verify impact analysis
6. Ask: "I'm new to this repository. What should I understand first?" → verify onboarding overview
7. Open Architecture graph → verify nodes for AuthService, UserRepository, etc.
8. Open Code Explorer → click AuthService → verify source code and line numbers
