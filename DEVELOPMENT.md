# SYNTERA Development Guide

## Prerequisites

- Python 3.11+ (3.13 recommended)
- Node.js 18+
- Git

## Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

## Running the Backend

```bash
# From SYNTERA/backend/
uvicorn app.main:app --reload --port 8000
```

API documentation: http://localhost:8000/api/docs

## Running Tests

```bash
cd backend
pytest tests/ -v
pytest tests/integration/ -v   # integration tests only
```

## Type Checking

```bash
cd backend
# ruff check
ruff check app/
# type check (optional, mypy)
```

## Frontend Setup

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev        # dev server on :5173 with /api proxy to :8000
npm run build      # production build
```

## Adding a New Language

1. Install the tree-sitter grammar: `pip install tree-sitter-<language>`
2. Add it to `tree_sitter_parser.py::_load_language()`
3. Add the language name to `TreeSitterParser.supported_languages()`
4. Add suffix → language mapping in `ingestion/filters.py::SOURCE_SUFFIX_TO_LANGUAGE`
5. Run `pytest tests/test_parser.py` to verify

## Adding a New LLM Provider

1. Create `backend/app/llm/<provider>_provider.py` implementing `LLMProvider`
2. Add the provider name to `factory.py::get_llm_provider()`
3. Document the required environment variables in `.env.example`

## Adding a New Embedding Provider

Same pattern as LLM — implement `EmbeddingProvider`, add to `factory.py`.

## Project Conventions

- Business logic never goes in route handlers
- Every persisted entity includes `repository_id`
- Never fabricate citations, line numbers, or file paths
- One bad file must not abort repository ingestion
- All provider connections go through abstractions, not direct SDK calls in services
