from pathlib import Path, PurePosixPath


def safe_join(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError("Path escapes repository root")
    return candidate


def zip_member_is_safe(name: str) -> bool:
    posix = PurePosixPath(name.replace("\\", "/"))
    if posix.is_absolute() or str(posix).startswith("/") or posix.parts[:1] == ("..",):
        return False
    if any(part == ".." for part in posix.parts):
        return False
    return True
