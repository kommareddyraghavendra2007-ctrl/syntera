from __future__ import annotations

from pathlib import Path, PurePosixPath

DEFAULT_IGNORE_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    ".coverage",
    "vendor",
    ".next",
    "out",
    "bin",
    "obj",
}

DEFAULT_IGNORE_FILE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".o",
    ".obj",
    ".bin",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".lock",
}

ALWAYS_KEEP_NAMES = {
    "readme",
    "readme.md",
    "readme.rst",
    "license",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "requirements.txt",
    "pipfile",
    "poetry.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "go.sum",
    "cargo.toml",
    "cargo.lock",
    "makefile",
    "cmakelists.txt",
}

ALWAYS_KEEP_SUFFIXES = {
    ".md",
    ".rst",
    ".toml",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
    ".conf",
    ".json",
    ".sql",
    ".graphql",
    ".proto",
}

SOURCE_SUFFIX_TO_LANGUAGE = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
}

CONFIG_NAMES = {
    ".env.example",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pom.xml",
    "build.gradle",
    "go.mod",
}


def normalize_relpath(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix().lstrip("/")


def detect_language(path: str) -> str | None:
    suffix = Path(path).suffix.lower()
    return SOURCE_SUFFIX_TO_LANGUAGE.get(suffix)


def classify_file(path: str) -> str:
    name = Path(path).name.lower()
    posix = normalize_relpath(path).lower()
    if name in {".env", ".env.local"} or name.endswith(".pem") or name.endswith(".key"):
        return "secret"
    if "test" in posix or posix.startswith("tests/"):
        return "test"
    if name in ALWAYS_KEEP_NAMES or Path(path).suffix.lower() in ALWAYS_KEEP_SUFFIXES:
        if detect_language(path):
            return "source"
        return "config" if name in CONFIG_NAMES or Path(path).suffix.lower() in {".yml", ".yaml", ".toml", ".json", ".ini"} else "documentation"
    if detect_language(path):
        return "source"
    if Path(path).suffix.lower() in {".sql"}:
        return "sql"
    return "other"


def should_ignore_relative_path(relpath: str, extra_ignore_dirs: set[str] | None = None) -> bool:
    posix = normalize_relpath(relpath)
    if not posix or posix == ".":
        return True
    parts = posix.split("/")
    ignore_dirs = DEFAULT_IGNORE_DIR_NAMES | (extra_ignore_dirs or set())
    if any(part in ignore_dirs for part in parts):
        return True
    name = parts[-1].lower()
    if name in ALWAYS_KEEP_NAMES:
        return False
    suffix = Path(name).suffix.lower()
    if suffix in ALWAYS_KEEP_SUFFIXES:
        return False
    if suffix in DEFAULT_IGNORE_FILE_SUFFIXES:
        return True
    if name.startswith(".") and name not in {".env.example", ".gitignore", ".dockerignore"}:
        if suffix in SOURCE_SUFFIX_TO_LANGUAGE or suffix in ALWAYS_KEEP_SUFFIXES:
            return False
        if name in {".env", ".env.local"}:
            return False
        return True
    return False


def is_probably_binary(sample: bytes) -> bool:
    if not sample:
        return False
    if b"\x00" in sample[:8192]:
        return True
    return False
