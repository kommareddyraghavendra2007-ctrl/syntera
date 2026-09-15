"""Password hashing and verification using bcrypt."""
from __future__ import annotations
import bcrypt


class PasswordService:
    """Handles secure password hashing and verification."""

    def hash_password(self, plain_password: str) -> str:
        """Hash a plaintext password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    def is_strong_password(self, password: str) -> bool:
        """Validate password strength: min 8 chars, uppercase, lowercase, digit."""
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        return True


password_service = PasswordService()
