# SYNTERA — Codebase Intelligence Platform

> Ask any natural-language question about a Git repository and receive evidence-grounded answers with exact source citations, architecture graphs, and impact analysis.

---

## What It Does

SYNTERA converts a code repository into a structured knowledge graph and answers developer questions about it. Every answer is grounded in retrieved source evidence with file paths, line numbers, and symbol references — not AI-generated guesses.

**Demo questions it answers correctly:**
- Where is authentication implemented?
- How does login work end-to-end?
- What could break if I change `AuthService`?
- Trace user registration from API to database.
- What environment variables does this project require?
- Explain the architecture to a new developer.

---

## Architecture

```
Repository URL / ZIP
       │
       ▼
  Ingestion Pipeline
  ├── Git clone / ZIP extract
  ├── File scan & classification
  ├── Tree-sitter AST parsing (Python, JS, TS, Java, Go, C, C++)
  ├── Symbol extraction (class, function, method, endpoint…)
  ├── Relationship graph (CALLS, IMPORTS, CONTAINS, ROUTES_TO…)
  ├── Secret detection & redaction
  └── Status: QUEUED → CLONING → … → READY
       │
       ▼
  Index Layer
  ├── Qdrant (dense semantic vectors)
  ├── BM25 (lexical / keyword)
  └── SQLite / PostgreSQL (metadata, symbols, relationships)
       │
       ▼
  Retrieval Engine (Hybrid)
  ├── Query understanding → intent classification
  ├── Query expansion → synonym/identifier expansion
  ├── Dense semantic search (Qdrant)
  ├── BM25 lexical search
  ├── Exact symbol DB search
  ├── RRF fusion (Reciprocal Rank Fusion)
  ├── Graph-based context expansion (NetworkX)
  ├── Rule-based reranking
  └── Token-budget-aware context builder
       │
       ▼
  LLM (OpenAI GPT-4o-mini)
  ├── Evidence-grounded answering
  ├── Hallucination guard (CONFIRMED / INFERRED / NOT FOUND)
  └── Structured response with citations
       │
       ▼
  React Frontend
  ├── Dashboard — repository management
  ├── Chat — ask questions, view citations
  ├── Architecture — React Flow graph visualization
  ├── Code Explorer — syntax-highlighted source with metadata
  └── Search — hybrid semantic + keyword search
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### 1. Clone & configure

```bash
git clone <this-repo>
cd SYNTERA
cp .env.example .env
# Edit .env — set LLM_API_KEY at minimum
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

### 3. Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

UI: http://localhost:5173

### 4. Docker (all services)

```bash
# Copy and edit .env first
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/docs
- Qdrant UI: http://localhost:6333/dashboard

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | **Yes** | — | OpenAI API key |
| `LLM_MODEL` | No | `gpt-4o-mini` | OpenAI model |
| `EMBEDDING_PROVIDER` | No | `hash` | `hash` (dev) or `openai` |
| `EMBEDDING_API_KEY` | If openai | — | Defaults to `LLM_API_KEY` |
| `QDRANT_URL` | No | local disk | Remote Qdrant URL |
| `DATABASE_URL` | No | SQLite | PostgreSQL for production |
| `MAX_REPOSITORY_SIZE_BYTES` | No | 80MB | Repository size limit |
| `TOP_K` | No | `20` | Dense retrieval top-K |
| `RERANK_TOP_K` | No | `12` | Results after reranking |

Full list in `.env.example`.

---

## How to Index a Repository

1. Open the Dashboard at http://localhost:5173
2. Click **Add Repository**
3. Paste a public GitHub URL (e.g. `https://github.com/owner/repo`)
4. Watch the indexing progress: CLONING → SCANNING → PARSING → … → READY
5. Click **Open Repository** and start asking questions

---

## Supported Languages

| Language | Parser | Notes |
|---|---|---|
| Python | Tree-sitter | Full AST |
| JavaScript | Tree-sitter | Full AST |
| TypeScript | Tree-sitter | Full AST |
| Java | Tree-sitter | Full AST |
| Go | Tree-sitter | Full AST |
| C | Tree-sitter | Full AST |
| C++ | Tree-sitter | Full AST |
| All others | Text fallback | Regex-based, degraded quality |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

## Running Evaluation

```bash
# Requires a running backend with the golden repo indexed
python -m evaluation.run --repository-id <id> --k 10
```

---

## Demo Repository (Golden Repo)

`golden_repo/` contains **ShopCore** — a realistic e-commerce backend with:
- JWT authentication (`src/auth/`)
- User management (`src/users/`)
- Order lifecycle (`src/orders/`)
- PostgreSQL ORM models (`src/database/`)
- FastAPI routes (`src/api/`)
- Configuration management (`src/config/`)
- Unit tests (`tests/`)

Use it to verify the demo flow described in EVALUATION.md.

---

## Limitations

- Repository size limit: 80MB (configurable)
- Call graph resolution is best-effort (dynamic dispatch is not resolved)
- Private repositories require git credentials configured in the environment
- Hash embedding provider (dev default) is not semantically meaningful — use OpenAI embeddings for production quality
