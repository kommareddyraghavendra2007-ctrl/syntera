"""Repository provider abstraction — fetch source code from various origins."""
from __future__ import annotations

import shutil
import subprocess
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings
from app.core.logging import get_logger
from app.security.paths import zip_member_is_safe
from app.security.urls import validate_git_url

logger = get_logger(__name__)


class RepositoryProvider(ABC):
    """Abstract base for fetching a repository to a local work directory."""

    @abstractmethod
    def fetch(self, destination: Path, settings: Settings) -> dict:
        """Fetch the repository into *destination* and return metadata dict.

        Returned dict keys (all optional):
          - commit_sha: str
          - branch: str
          - name: str
        """


class GitProvider(RepositoryProvider):
    """Clone a public Git repository via HTTPS."""

    def __init__(self, url: str, branch: str | None = None) -> None:
        self.url = validate_git_url(url)
        self.branch = branch

    def fetch(self, destination: Path, settings: Settings) -> dict:
        destination.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", "--single-branch"]
        if self.branch:
            cmd += ["--branch", self.branch]
        cmd += [self.url, str(destination)]

        logger.info(
            "git_clone_start",
            extra={"url": self.url, "branch": self.branch, "dest": str(destination)},
        )
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.clone_timeout_seconds,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git clone failed (exit {result.returncode}): {result.stderr[:500]}"
            )

        meta: dict = {}
        # Resolve branch name
        branch_res = subprocess.run(  # noqa: S603
            ["git", "-C", str(destination), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if branch_res.returncode == 0:
            meta["branch"] = branch_res.stdout.strip()

        # Resolve commit SHA
        sha_res = subprocess.run(  # noqa: S603
            ["git", "-C", str(destination), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if sha_res.returncode == 0:
            meta["commit_sha"] = sha_res.stdout.strip()

        # Derive name from URL
        meta["name"] = self.url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        logger.info("git_clone_done", extra={"meta": meta})
        return meta


class ZipProvider(RepositoryProvider):
    """Extract an uploaded ZIP archive."""

    def __init__(self, zip_path: Path, name: str) -> None:
        self.zip_path = zip_path
        self.name = name

    def fetch(self, destination: Path, settings: Settings) -> dict:
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.zip_path, "r") as zf:
            members = zf.infolist()
            if len(members) > settings.max_zip_files:
                raise ValueError(
                    f"ZIP contains {len(members)} entries, limit is {settings.max_zip_files}"
                )
            total_size = sum(m.file_size for m in members)
            if total_size > settings.max_repository_size_bytes:
                raise ValueError(
                    f"ZIP uncompressed size {total_size} exceeds limit"
                )
            for member in members:
                if not zip_member_is_safe(member.filename):
                    logger.warning(
                        "zip_unsafe_member_skipped",
                        extra={"member": member.filename},
                    )
                    continue
                zf.extract(member, destination)

        # If the ZIP wraps a single top-level directory, collapse it
        entries = list(destination.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            inner = entries[0]
            tmp = destination.parent / (destination.name + "_inner")
            inner.rename(tmp)
            shutil.rmtree(destination)
            tmp.rename(destination)

        logger.info("zip_extracted", extra={"dest": str(destination), "repo_name": self.name})
        return {"name": self.name}
