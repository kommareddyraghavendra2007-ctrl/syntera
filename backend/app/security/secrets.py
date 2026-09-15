from __future__ import annotations

import re
from dataclasses import dataclass

SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    re.compile(r"(?i)secret\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    re.compile(r"(?i)(?:aws|ghp|sk|xox)[_-][A-Za-z0-9]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PRIVATE )KEY-----"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"),
]


@dataclass(frozen=True)
class SecretFinding:
    line: int
    excerpt: str


def find_secrets(text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(line=index, excerpt=redact_text(line)))
                break
    return findings


def redact_text(text: str) -> str:
    redacted = text
    replacements = [
        (re.compile(r"(?i)((?:api[_-]?key|secret|password|token)\s*[:=]\s*)(['\"]?)[^'\"\s]+"), r"\1\2[REDACTED]"),
        (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED PRIVATE KEY]"),
        (re.compile(r"(?i)AKIA[0-9A-Z]{16}"), "[REDACTED AWS KEY]"),
        (re.compile(r"(?i)eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"), "[REDACTED JWT]"),
    ]
    for pattern, repl in replacements:
        redacted = pattern.sub(repl, redacted)
    return redacted


def looks_like_secret_file(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name in {".env", ".env.local", ".env.production"} or name.endswith((".pem", ".key", ".p12", ".pfx"))
