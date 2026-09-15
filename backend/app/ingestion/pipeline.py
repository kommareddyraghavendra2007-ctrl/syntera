"""
Ingestion pipeline orchestrator.

Stages:
  QUEUED → CLONING → SCANNING → PARSING → EXTRACTING_SYMBOLS →
  BUILDING_GRAPH → GENERATING_EMBEDDINGS → INDEXING → VALIDATING → READY

One bad file never aborts the whole run.
"""
from __future__ import annotations

import concurrent.futures
import shutil
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.enums import IndexStatus, ParserCapability, RelationType, SymbolType
from app.core.ids import file_id as make_file_id
from app.core.ids import symbol_id as make_symbol_id
from app.core.logging import get_logger
from app.ingestion.providers import RepositoryProvider
from app.ingestion.scanner import scan_repository_files
from app.models.orm import CodeFile, CodeRelationship, Repository, Symbol
from app.parsing import parse_source
from app.security.secrets import find_secrets, looks_like_secret_file

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def _set_status(
    db: Session,
    repo: Repository,
    status: IndexStatus,
    detail: str | None = None,
) -> None:
    repo.status = status
    repo.status_detail = detail
    db.commit()
    logger.info(
        "ingestion_status",
        extra={"repository_id": repo.id, "status": status, "detail": detail},
    )


def _fail(db: Session, repo: Repository, message: str) -> None:
    repo.status = IndexStatus.FAILED
    repo.error_message = message[:2000]
    repo.indexing_finished_at = datetime.now(UTC)
    db.commit()
    logger.error(
        "ingestion_failed",
        extra={"repository_id": repo.id, "error": message},
    )


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

def run_ingestion(
    db: Session,
    repo: Repository,
    provider: RepositoryProvider,
    settings: Settings | None = None,
) -> None:
    """Run the full ingestion pipeline synchronously.

    Designed to be called from a background thread/process.
    """
    cfg = settings or get_settings()
    work_root = Path(cfg.work_dir) / repo.id
    try:
        _pipeline(db, repo, provider, cfg, work_root)
    except Exception as exc:
        logger.exception(
            "ingestion_unhandled_error",
            extra={"repository_id": repo.id, "error": str(exc)},
        )
        _fail(db, repo, str(exc))
    finally:
        # Clean up cloned sources — they are fully indexed now
        if work_root.exists():
            shutil.rmtree(work_root, ignore_errors=True)


def _pipeline(
    db: Session,
    repo: Repository,
    provider: RepositoryProvider,
    cfg: Settings,
    work_root: Path,
) -> None:
    repo.indexing_started_at = datetime.now(UTC)
    db.commit()

    # ── Stage 1: CLONING ──────────────────────────────────────────────────
    _set_status(db, repo, IndexStatus.CLONING, "Fetching repository source")
    work_root.mkdir(parents=True, exist_ok=True)
    try:
        meta = provider.fetch(work_root, cfg)
    except Exception as exc:
        _fail(db, repo, f"Failed to fetch repository: {exc}")
        return

    if not repo.commit_sha and "commit_sha" in meta:
        repo.commit_sha = meta["commit_sha"]
    if not repo.branch and "branch" in meta:
        repo.branch = meta["branch"]
    if repo.name in {"", None} and "name" in meta:
        repo.name = meta["name"]
    db.commit()

    # ── Stage 2: SCANNING ─────────────────────────────────────────────────
    _set_status(db, repo, IndexStatus.SCANNING, "Scanning repository files")
    scanned = scan_repository_files(work_root, cfg)
    if not scanned:
        _fail(db, repo, "No indexable files found in repository")
        return

    # ── Stage 3: PARSING ──────────────────────────────────────────────────
    _set_status(db, repo, IndexStatus.PARSING, f"Parsing {len(scanned)} files")

    file_records: list[CodeFile] = []
    all_symbols: list[Symbol] = []
    all_relationships: list[CodeRelationship] = []
    language_counts: dict[str, int] = {}

    # Process files with bounded concurrency
    results = _parse_files_concurrent(scanned, work_root, repo.id, cfg)

    # ── Stage 4: EXTRACTING_SYMBOLS ───────────────────────────────────────
    _set_status(db, repo, IndexStatus.EXTRACTING_SYMBOLS, "Extracting code symbols")

    for scanned_file, parse_result, file_rec, symbols in results:
        # Secret detection
        is_secret = looks_like_secret_file(scanned_file.path)
        if not is_secret and not scanned_file.is_binary:
            try:
                raw = scanned_file.absolute_path.read_text(encoding="utf-8", errors="replace")
                findings = find_secrets(raw)
                if findings:
                    is_secret = True
                    logger.info(
                        "secret_detected",
                        extra={
                            "repository_id": repo.id,
                            "file": scanned_file.path,
                            "count": len(findings),
                        },
                    )
            except Exception:
                pass

        file_rec.is_secret = is_secret
        file_records.append(file_rec)

        if parse_result:
            for sym in symbols:
                # Redact code in secret files
                if is_secret:
                    sym.code = "[REDACTED — secret file]"
                all_symbols.append(sym)

        if scanned_file.language:
            language_counts[scanned_file.language] = (
                language_counts.get(scanned_file.language, 0) + 1
            )

    # Bulk-insert files
    try:
        db.bulk_save_objects(file_records)
        db.flush()
    except Exception as exc:
        logger.error("db_file_insert_error", extra={"repository_id": repo.id, "error": str(exc)})
        db.rollback()
        _fail(db, repo, f"Database error persisting files: {exc}")
        return

    # Bulk-insert symbols (deduplicate by primary key)
    seen_ids: set[str] = set()
    deduped: list[Symbol] = []
    for sym in all_symbols:
        if sym.id not in seen_ids:
            seen_ids.add(sym.id)
            deduped.append(sym)

    try:
        db.bulk_save_objects(deduped)
        db.flush()
    except Exception as exc:
        logger.error("db_symbol_insert_error", extra={"repository_id": repo.id, "error": str(exc)})
        db.rollback()
        _fail(db, repo, f"Database error persisting symbols: {exc}")
        return

    # ── Stage 5: BUILDING_GRAPH ───────────────────────────────────────────
    _set_status(db, repo, IndexStatus.BUILDING_GRAPH, "Building code relationship graph")
    symbol_map = {s.qualified_name: s.id for s in deduped}
    all_relationships = _build_relationships(repo.id, results, symbol_map)

    try:
        db.bulk_save_objects(all_relationships)
        db.flush()
    except Exception as exc:
        logger.error("db_rel_insert_error", extra={"repository_id": repo.id, "error": str(exc)})
        db.rollback()
        # Non-fatal — relationships are enhancement, not core
        all_relationships = []

    db.commit()

    # ── Stages 6–8: EMBEDDINGS / INDEXING / VALIDATING ────────────────────
    # These stages are handled by the IndexingService which is called after
    # the pipeline inserts all DB records. The pipeline itself sets the
    # intermediate statuses so the UI reflects progress.

    _set_status(db, repo, IndexStatus.GENERATING_EMBEDDINGS, "Generating embeddings")
    _set_status(db, repo, IndexStatus.INDEXING, "Indexing into vector store")

    # Lazy import to avoid circular dependency
    from app.indexing.symbol_indexer import SymbolIndexer  # noqa: PLC0415

    indexer = SymbolIndexer(cfg)
    try:
        indexed = indexer.index_repository(repo.id, deduped)
        logger.info(
            "indexing_done",
            extra={"repository_id": repo.id, "indexed": indexed},
        )
    except Exception as exc:
        logger.error(
            "indexing_error",
            extra={"repository_id": repo.id, "error": str(exc)},
        )
        # Non-fatal for MVP — log and continue to READY

    # ── Stage 9: VALIDATING / READY ────────────────────────────────────────
    _set_status(db, repo, IndexStatus.VALIDATING, "Validating index")

    import json

    repo.file_count = len(file_records)
    repo.symbol_count = len(deduped)
    repo.relationship_count = len(all_relationships)
    repo.languages_json = json.dumps(language_counts)
    repo.status = IndexStatus.READY
    repo.status_detail = (
        f"{repo.file_count} files · {repo.symbol_count} symbols · "
        f"{repo.relationship_count} relationships"
    )
    repo.indexing_finished_at = datetime.now(UTC)
    db.commit()

    logger.info(
        "ingestion_complete",
        extra={
            "repository_id": repo.id,
            "files": repo.file_count,
            "symbols": repo.symbol_count,
            "relationships": repo.relationship_count,
        },
    )


# ---------------------------------------------------------------------------
# Concurrent file parsing
# ---------------------------------------------------------------------------

def _parse_files_concurrent(
    scanned,
    work_root: Path,
    repository_id: str,
    cfg: Settings,
) -> list:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.parse_concurrency) as pool:
        futures = {
            pool.submit(_process_single_file, sf, work_root, repository_id): sf
            for sf in scanned
        }
        for future in concurrent.futures.as_completed(futures):
            sf = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                logger.warning(
                    "file_parse_error",
                    extra={"file": sf.path, "error": str(exc)},
                )
    return results


def _process_single_file(scanned_file, work_root: Path, repository_id: str):
    """Parse one file and return (scanned_file, parse_result, file_record, symbols)."""
    fid = make_file_id(repository_id, scanned_file.path)

    capability = (
        ParserCapability.SKIPPED
        if scanned_file.is_binary
        else ParserCapability.TEXT_FALLBACK
    )

    file_rec = CodeFile(
        id=fid,
        repository_id=repository_id,
        path=scanned_file.path,
        language=scanned_file.language,
        classification=scanned_file.classification,
        parser_capability=capability,
        content_hash=scanned_file.content_hash,
        size_bytes=scanned_file.size_bytes,
        is_binary=scanned_file.is_binary,
        is_secret=False,
        redacted=False,
    )

    if scanned_file.is_binary or scanned_file.classification == "secret":
        return scanned_file, None, file_rec, []

    try:
        source = scanned_file.absolute_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return scanned_file, None, file_rec, []

    if not scanned_file.language:
        # Non-source file — index as a single FILE unit for documentation search
        sym_id = make_symbol_id(
            repository_id,
            scanned_file.path,
            type("_S", (), {
                "symbol_type": SymbolType.FILE,
                "qualified_name": scanned_file.path,
                "start_line": 1,
                "end_line": max(1, source.count("\n") + 1),
            })(),
        )
        doc_sym = Symbol(
            id=sym_id,
            repository_id=repository_id,
            file_id=fid,
            file_path=scanned_file.path,
            language=scanned_file.language,
            symbol_type=SymbolType.FILE,
            symbol_name=scanned_file.path.rsplit("/", 1)[-1],
            qualified_name=scanned_file.path,
            module_name=scanned_file.path,
            start_line=1,
            end_line=max(1, source.count("\n") + 1),
            code=source[:4000],
            content_hash=sha256(source[:4000].encode()).hexdigest(),
        )
        file_rec.parser_capability = ParserCapability.TEXT_FALLBACK
        return scanned_file, None, file_rec, [doc_sym]

    parse_result = parse_source(scanned_file.path, source, scanned_file.language)
    file_rec.parser_capability = parse_result.parser_capability

    symbols: list[Symbol] = []
    for extracted in parse_result.symbols:
        sid = make_symbol_id(repository_id, scanned_file.path, extracted)
        sym = Symbol(
            id=sid,
            repository_id=repository_id,
            file_id=fid,
            file_path=scanned_file.path,
            language=extracted.language or scanned_file.language,
            symbol_type=extracted.symbol_type,
            symbol_name=extracted.symbol_name,
            qualified_name=extracted.qualified_name,
            class_name=extracted.class_name,
            module_name=extracted.module_name or scanned_file.path,
            start_line=extracted.start_line,
            end_line=extracted.end_line,
            start_column=extracted.start_column,
            end_column=extracted.end_column,
            code=extracted.code,
            documentation=extracted.documentation,
            parent_symbol=extracted.parent_symbol,
            content_hash=sha256(extracted.code.encode("utf-8", errors="replace")).hexdigest(),
        )
        symbols.append(sym)

    return scanned_file, parse_result, file_rec, symbols


# ---------------------------------------------------------------------------
# Relationship building
# ---------------------------------------------------------------------------

def _build_relationships(
    repository_id: str,
    results: list,
    symbol_map: dict[str, str],
) -> list[CodeRelationship]:
    from uuid import uuid4

    rels: list[CodeRelationship] = []
    seen: set[tuple[str, str, str]] = set()

    def add(src: str, tgt: str, rel_type: str, confidence: float = 1.0) -> None:
        key = (src, tgt, rel_type)
        if key in seen:
            return
        seen.add(key)
        rels.append(
            CodeRelationship(
                id=str(uuid4()),
                repository_id=repository_id,
                source_symbol_id=symbol_map.get(src),
                target_symbol_id=symbol_map.get(tgt),
                source_name=src,
                target_name=tgt,
                relation_type=rel_type,
                confidence=confidence,
            )
        )

    for scanned_file, parse_result, _file_rec, symbols in results:
        if parse_result is None:
            continue

        # CONTAINS: file → symbol
        file_sym_name = scanned_file.path
        for sym in symbols:
            add(file_sym_name, sym.qualified_name, RelationType.CONTAINS)

        # IMPORTS relationships
        for imp in parse_result.imports:
            for sym in symbols:
                add(sym.qualified_name, imp.module, RelationType.IMPORTS, confidence=0.9)
                break  # one import edge per module per file is sufficient

        # CALLS relationships (best-effort, confidence < 1.0)
        for call in parse_result.calls:
            callee = call.callee
            # Find which symbol in this file is the most likely caller
            # (use the last function/method symbol before the call line)
            best_caller: str | None = None
            best_line = -1
            for sym in symbols:
                if sym.symbol_type in {SymbolType.FUNCTION, SymbolType.METHOD}:
                    if sym.start_line <= call.start_line and sym.start_line > best_line:
                        best_line = sym.start_line
                        best_caller = sym.qualified_name
            if best_caller and callee:
                add(best_caller, callee, RelationType.CALLS, confidence=call.confidence)

        # ROUTES_TO: endpoint → handler
        for route in parse_result.routes:
            if route.handler:
                endpoint_name = f"{route.method} {route.path}"
                add(endpoint_name, route.handler, RelationType.ROUTES_TO)

    return rels
