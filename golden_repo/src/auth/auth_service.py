"""
AuthService — core authentication logic.

Responsibilities:
- User registration with email uniqueness validation
- Login with credential verification
- JWT access + refresh token issuance
- Token refresh workflow
- Logout (refresh token revocation)

Called by: LoginController, RegisterController (api/auth.py)
Calls: UserRepository, JWTService, PasswordService
"""
from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy.orm import Session
from src.auth.jwt_service import JWTService, jwt_service
from src.auth.password_service import PasswordService, password_service
from src.database.models import RefreshToken, User
from src.users.user_repository import UserRepository


class AuthenticationError(Exception):
    """Raised when credentials are invalid."""


class RegistrationError(Exception):
    """Raised when registration fails due to validation."""


class AuthService:
    """Handles user authentication end-to-end."""

    def __init__(
        self,
        jwt: JWTService = jwt_service,
        pwd: PasswordService = password_service,
    ) -> None:
        self._jwt = jwt
        self._pwd = pwd

    def register(
        self,
        db: Session,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Register a new user. Raises RegistrationError on failure."""
        repo = UserRepository(db)
        if repo.find_by_email(email):
            raise RegistrationError(f"Email already registered: {email}")
        if not self._pwd.is_strong_password(password):
            raise RegistrationError(
                "Password must be at least 8 characters with uppercase, lowercase, and digit"
            )
        hashed = self._pwd.hash_password(password)
        user = repo.create(
            email=email.lower().strip(),
            password_hash=hashed,
            first_name=first_name,
            last_name=last_name,
        )
        return user

    def authenticate_user(self, db: Session, email: str, password: str) -> User:
        """Verify credentials. Raises AuthenticationError if invalid."""
        repo = UserRepository(db)
        user = repo.find_by_email(email.lower().strip())
        if not user:
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        if not self._pwd.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        return user

    def login(self, db: Session, email: str, password: str) -> dict:
        """Authenticate and issue tokens."""
        user = self.authenticate_user(db, email, password)
        access_token = self._jwt.generate_access_token(user.id, user.email, user.is_admin)
        refresh_token = self._jwt.generate_refresh_token(user.id)
        token_hash = self._jwt.hash_token(refresh_token)
        expires_at = self._jwt.refresh_expiry_datetime()
        db.add(RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        ))
        db.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
        }

    def refresh_access_token(self, db: Session, refresh_token: str) -> dict:
        """Issue a new access token using a valid refresh token."""
        try:
            payload = self._jwt.decode_refresh_token(refresh_token)
        except Exception as e:
            raise AuthenticationError(f"Invalid refresh token: {e}")
        token_hash = self._jwt.hash_token(refresh_token)
        stored = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,  # noqa: E712
            )
            .first()
        )
        if not stored or stored.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise AuthenticationError("Refresh token expired or revoked")
        user_id = payload["sub"]
        repo = UserRepository(db)
        user = repo.find_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        new_access_token = self._jwt.generate_access_token(user.id, user.email, user.is_admin)
        return {"access_token": new_access_token, "token_type": "bearer"}

    def logout(self, db: Session, refresh_token: str) -> None:
        """Revoke a refresh token."""
        token_hash = self._jwt.hash_token(refresh_token)
        stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if stored:
            stored.revoked = True
            db.commit()


auth_service = AuthService()
