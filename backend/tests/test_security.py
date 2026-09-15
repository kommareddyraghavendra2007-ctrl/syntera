"""Tests for security utilities."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from app.security.paths import safe_join, zip_member_is_safe
from app.security.secrets import find_secrets, looks_like_secret_file, redact_text
from app.security.urls import validate_git_url


def test_safe_join_normal(tmp_path):
    result = safe_join(tmp_path, "src/auth/service.py")
    assert str(result).startswith(str(tmp_path))


def test_safe_join_traversal(tmp_path):
    with pytest.raises(ValueError, match="escapes"):
        safe_join(tmp_path, "../../etc/passwd")


def test_zip_safe():
    assert zip_member_is_safe("src/auth/service.py")
    assert zip_member_is_safe("README.md")


def test_zip_unsafe():
    assert not zip_member_is_safe("../../../etc/passwd")
    assert not zip_member_is_safe("/etc/passwd")


def test_detect_api_key():
    assert find_secrets('api_key = "sk-abcdef1234567890abcd"')


def test_clean_code():
    assert not find_secrets("def authenticate_user(email, password):\n    return True\n")


def test_redact():
    redacted = redact_text('api_key = "my-super-secret-key-1234"')
    assert "my-super-secret-key-1234" not in redacted
    assert "REDACTED" in redacted


def test_secret_file_detection():
    assert looks_like_secret_file(".env")
    assert looks_like_secret_file("private.pem")
    assert not looks_like_secret_file("service.py")


def test_valid_git_url():
    url = validate_git_url("https://github.com/owner/repo")
    assert "github.com" in url


def test_rejects_credentials_in_url():
    with pytest.raises(ValueError):
        validate_git_url("https://user:pass@github.com/owner/repo")


def test_rejects_bad_scheme():
    with pytest.raises(ValueError):
        validate_git_url("ftp://github.com/repo")
