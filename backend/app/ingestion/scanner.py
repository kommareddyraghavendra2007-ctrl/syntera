from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from app.core.config import Settings, get_settings
from app.ingestion.filters import (
    classify_file,
    detect_language,
    is_probably_binary,
    normalize_relpath,
    should_ignore_relative_path,
)


@dataclass(frozen=True)
class ScannedFile:
    path: str
    absolute_path: Path
    language: str | None
    classification: str
    size_bytes: int
    content_hash: str
    is_binary: bool


def scan_repository_files(
    root: Path,
    settings: Settings | None = None,
    extra_ignore_dirs: set[str] | None = None,
) -> list[ScannedFile]:
    settings = settings or get_settings()
    root = root.resolve()
    results: list[ScannedFile] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = normalize_relpath(str(path.relative_to(root)))
        if should_ignore_relative_path(rel, extra_ignore_dirs):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > settings.max_file_size_bytes:
            continue
        try:
            sample = path.read_bytes()[:8192]
        except OSError:
            continue
        binary = is_probably_binary(sample)
        classification = classify_file(rel)
        if binary and classification not in {"config", "documentation"}:
            continue
        digest = sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 64), b""):
                    digest.update(chunk)
        except OSError:
            continue
        results.append(
            ScannedFile(
                path=rel,
                absolute_path=path,
                language=detect_language(rel),
                classification=classification,
                size_bytes=size,
                content_hash=digest.hexdigest(),
                is_binary=binary,
            )
        )
    results.sort(key=lambda item: item.path)
    return results
