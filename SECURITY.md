# SYNTERA Security

## Secrets

- All API keys, DB credentials, and Qdrant keys live in backend environment variables only.
- The frontend never receives or transmits any secret. All LLM/Qdrant calls are backend-only.
- `.env` is in `.gitignore` and must never be committed.
- `.env.example` contains only placeholder values — no real secrets.

## Secret Detection

Before indexing, every file is scanned for likely secrets using pattern matching:
- API key patterns (`api_key = "..."`, `sk-...`, `AKIA...`)
- JWT tokens (eyJ... pattern)
- Private key material (`-----BEGIN ... PRIVATE KEY-----`)
- AWS credentials

Files that match are marked `is_secret=True`. Their code is replaced with `[REDACTED — secret file]` before being sent to the LLM or stored as searchable content.

## Path Traversal Protection

- ZIP extraction: every member path is validated against `..` and absolute path components before extraction.
- File path joins use `safe_join()` which resolves and verifies the result stays under the repository root.

## URL Validation

- Git URLs are validated against an allowlist of schemes (`https`, `http`, `git`).
- Credentials embedded in URLs (`user:pass@host`) are explicitly rejected.
- Only HTTPS is allowed for non-major-hosting-provider URLs.
- No shell interpolation of user-provided URLs — subprocess receives args as a list.

## Repository Isolation

Every entity (file, symbol, relationship, Qdrant point, BM25 document, graph) is tagged with `repository_id`. All queries filter by this ID. Tests in `tests/integration/test_ingestion_integration.py::test_repository_isolation` verify this property.

## Code Execution

SYNTERA never executes repository code. It is a static analysis and text indexing system only. Git operations use the `git` CLI with a validated URL and a configurable timeout. No user input is ever interpolated into shell commands.

## Input Validation

- Repository URLs are validated before any operation.
- ZIP files are checked for entry count and uncompressed size limits.
- File size limit (`max_file_size_bytes`) prevents memory exhaustion from large files.
- Repository size limit (`max_repository_size_bytes`) prevents oversized ingestion.

## Configuration Inspection

By default, configuration file content is treated the same as source code. The `ALLOW_CONFIG_INSPECT` flag (default `false`) does not automatically expose secret values — it only allows querying configuration structure. Secret-pattern-matching still applies.
