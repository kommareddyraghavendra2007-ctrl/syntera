# SYNTERA Architecture

## Backend Layer Map

```
app/
├── api/            Route handlers (thin — no business logic)
│   ├── repositories.py   POST /repositories, GET, DELETE, reindex
│   ├── query.py          POST /repositories/{id}/query, conversations
│   ├── symbols.py        GET files, symbols, search
│   └── graph.py          GET graph, impact analysis
│
├── core/           Cross-cutting concerns
│   ├── config.py         Pydantic-settings, all env vars
│   ├── database.py       SQLAlchemy engine + session factory
│   ├── enums.py          IndexStatus, SymbolType, RelationType, QueryIntent
│   ├── ids.py            Deterministic UUID5 for symbols and files
│   └── logging.py        Structured logging config
│
├── models/orm.py   SQLAlchemy ORM: Repository, CodeFile, Symbol,
│                   CodeRelationship, Conversation, Message
│
├── schemas/        Pydantic v2 request/response contracts
│
├── ingestion/      Repository acquisition and parsing orchestration
│   ├── providers.py      GitProvider, ZipProvider (RepositoryProvider ABC)
│   ├── pipeline.py       9-stage ingestion orchestrator
│   ├── scanner.py        File tree walk with classification and hashing
│   └── filters.py        Ignore rules, language detection, classification
│
├── parsing/        AST-aware code unit extraction
│   ├── base.py           CodeParser ABC
│   ├── tree_sitter_parser.py   Tree-sitter walker (7 languages)
│   ├── fallback.py       Regex fallback for unsupported languages
│   └── types.py          ExtractedSymbol, ParseResult, ExtractedImport…
│
├── graph/          Code relationship graph
│   ├── store.py          CodeGraph (NetworkX DiGraph wrapper)
│   ├── builder.py        ORM → CodeGraph
│   └── service.py        Thread-safe graph cache + invalidation
│
├── embeddings/     Vector embedding abstraction
│   ├── base.py           EmbeddingProvider ABC
│   ├── hash_provider.py  384-dim deterministic (dev, zero dependencies)
│   ├── openai_provider.py  OpenAI text-embedding-3-*
│   └── factory.py        Provider selection from EMBEDDING_PROVIDER env
│
├── indexing/       Storage layer
│   ├── vector_store.py   Qdrant wrapper (local disk or remote)
│   ├── lexical.py        BM25Okapi index per repository, registry
│   └── symbol_indexer.py Orchestrates embed + upsert + BM25 build
│
├── retrieval/      The core intelligence layer
│   ├── query.py          QueryAnalyzer: intent classification + expansion
│   ├── fusion.py         Reciprocal Rank Fusion
│   ├── reranker.py       Rule-based signal boosting
│   ├── context_builder.py  Token-budget-aware LLM context assembly
│   └── engine.py         RetrievalEngine: full 8-step pipeline
│
├── llm/            LLM provider abstraction
│   ├── base.py           LLMProvider ABC, LLMResponse
│   ├── openai_provider.py  OpenAI chat completions
│   ├── factory.py        Provider selection from LLM_PROVIDER env
│   └── answering.py      Evidence-grounded answer generation
│
└── security/       Security utilities
    ├── paths.py          safe_join, zip traversal protection
    ├── secrets.py        Secret detection and redaction
    └── urls.py           Git URL validation and allowlist
```

## Retrieval Pipeline (Detail)

```
User question
     │
     ▼ QueryAnalyzer
     ├── Intent classification (LOCATION, FLOW, IMPACT, ARCHITECTURE…)
     ├── Exact symbol extraction (PascalCase, dotted names, quoted)
     └── Query expansion (auth → authenticate, AuthService, signIn…)
     │
     ├──▶ Dense search    → Qdrant cosine similarity (top-K)
     ├──▶ Lexical search  → BM25Okapi (top-K)
     └──▶ Symbol search   → DB ILIKE match (top-K)
               │
               ▼ RRF Fusion (1/(k+rank) per list)
               │
               ▼ Graph expansion (bounded BFS, depth=2, limit=24)
               │   callers, callees, imports, related config/tests
               │
               ▼ Reranking
               │   exact name match boost, intent-aware type preference
               │
               ▼ Context builder (max_context_chars=24000)
               │   structured prompt with source evidence
               │
               ▼ LLM (gpt-4o-mini, temp=0.05)
               │   system prompt enforces evidence grounding
               │
               ▼ Response
                   answer + citations + intent + confidence level
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| RRF instead of score addition | Dense cosine and BM25 scores are incomparable; RRF normalizes rank position |
| Hash embeddings as default | Zero API cost for local dev; switch to OpenAI for production retrieval quality |
| NetworkX graph | Sufficient for prototype; abstracted behind `CodeGraph` to allow Neo4j migration |
| Repository-scoped all queries | Security requirement; every DB, Qdrant, and graph query filters by `repository_id` |
| Lazy SymbolIndexer import | Breaks circular dependency between ingestion and indexing modules |
| BM25 in-memory per repo | Rebuilt on startup and after indexing; fast for repositories up to ~100K symbols |
| Tree-sitter fallback to text | Never crash on unsupported language; degrade to regex extraction |
| `source_symbol_id` nullable | Relationship targets may reference external symbols not in the index |
