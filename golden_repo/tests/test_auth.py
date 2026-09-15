"""Tests for authentication: password hashing, JWT tokens, AuthService."""
from __future__ import annotations

import pytest
from src.auth.password_service import PasswordService
from src.auth.jwt_service import JWTService


def test_password_hash_and_verify():
    svc = PasswordService()
    hashed = svc.hash_password("SecurePass1")
    assert hashed != "SecurePass1"
    assert svc.verify_password("SecurePass1", hashed)
    assert not svc.verify_password("WrongPass1", hashed)


def test_password_strength():
    svc = PasswordService()
    assert svc.is_strong_password("SecurePass1")
    assert not svc.is_strong_password("short1A")
    assert not svc.is_strong_password("alllowercase1")
    assert not svc.is_strong_password("ALLUPPERCASE1")
    assert not svc.is_strong_password("NoDigitsHere")


def test_jwt_access_token():
    svc = JWTService(
        secret_key="test-secret",
        algorithm="HS256",
        access_expiry_minutes=60,
        refresh_expiry_days=7,
    )
    token = svc.generate_access_token("user-123", "test@example.com", False)
    payload = svc.decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"


def test_jwt_refresh_token():
    svc = JWTService(
        secret_key="test-secret",
        algorithm="HS256",
        access_expiry_minutes=60,
        refresh_expiry_days=7,
    )
    token = svc.generate_refresh_token("user-456")
    payload = svc.decode_refresh_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_jwt_token_hash_stable():
    svc = JWTService(
        secret_key="test-secret",
        algorithm="HS256",
        access_expiry_minutes=60,
        refresh_expiry_days=7,
    )
    assert svc.hash_token("abc") == svc.hash_token("abc")
    assert svc.hash_token("abc") != svc.hash_token("def")
