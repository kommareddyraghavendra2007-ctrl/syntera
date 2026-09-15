from urllib.parse import urlparse

ALLOWED_GIT_SCHEMES = {"https", "http", "git"}


def validate_git_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ALLOWED_GIT_SCHEMES:
        raise ValueError("Only http(s) git URLs are supported")
    if not parsed.netloc or not parsed.path:
        raise ValueError("Invalid repository URL")
    host = parsed.netloc.lower()
    if host not in {
        "github.com",
        "www.github.com",
        "gitlab.com",
        "www.gitlab.com",
        "bitbucket.org",
        "www.bitbucket.org",
    } and not host.endswith(".github.com"):
        # Allow other hosts but require https and no credentials in URL.
        if parsed.scheme != "https":
            raise ValueError("Non-GitHub git hosts must use HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in repository URLs are not allowed")
    return url.strip().rstrip("/")


def github_archive_url(repo_url: str, branch: str = "main") -> str | None:
    parsed = urlparse(repo_url)
    host = parsed.netloc.lower()
    if host not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        return None
    owner, name = parts[0], parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"
