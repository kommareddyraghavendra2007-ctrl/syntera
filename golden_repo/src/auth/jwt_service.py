"""
JWTService — JSON Web Token generation and validation.

Responsibilities:
- Generate short-lived access tokens (15–60 min)
- Generate long-lived refresh tokens (7 days)
- Decode and validate both token types
- Hash tokens for safe database storage

Called by: AuthService
"""
from __future__ import annotations
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from src.config import settings


class JWTService:
    """Handles JWT creation and validation."""

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = None,
        access_expiry_minutes: int = None,
        refresh_expiry_days: int = None,
    ) -> None:
        self._secret = secret_key or settings.jwt_secret_key
        self._algorithm = algorithm or settings.jwt_algorithm
        self._access_expiry = access_expiry_minutes or settings.jwt_access_expiry_minutes
        self._refresh_expiry = refresh_expiry_days or settings.jwt_refresh_expiry_days

    def generate_access_token(self, user_id: str, email: str, is_admin: bool) -> str:
        """Generate a signed JWT access token."""
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "email": email,
            "is_admin": is_admin,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self._access_expiry),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def generate_refresh_token(self, user_id: str) -> str:
        """Generate a signed JWT refresh token."""
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self._refresh_expiry),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> dict:
        """Decode and validate an access token. Raises jwt.InvalidTokenError on failure."""
        payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Token is not an access token")
        return payload

    def decode_refresh_token(self, token: str) -> dict:
        """Decode and validate a refresh token. Raises jwt.InvalidTokenError on failure."""
        payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Token is not a refresh token")
        return payload

    def hash_token(self, token: str) -> str:
        """Return a SHA-256 hex digest of the token for safe DB storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def refresh_expiry_datetime(self) -> datetime:
        """Return the expiry datetime for a new refresh token."""
        return datetime.now(UTC) + timedelta(days=self._refresh_expiry)


jwt_service = JWTService()
