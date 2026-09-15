"""
UserRepository — data access layer for User entities.

All database operations for users are encapsulated here.
Called by AuthService and UserService.
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from src.database.models import User


class UserRepository:
    """Data access for User table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_email(self, email: str) -> User | None:
        return self._db.query(User).filter(User.email == email).first()

    def find_by_id(self, user_id: str) -> User | None:
        return self._db.query(User).filter(User.id == user_id).first()

    def create(self, email: str, password_hash: str, first_name: str, last_name: str) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_profile(self, user: User, first_name: str | None = None, last_name: str | None = None) -> User:
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        self._db.commit()
        self._db.refresh(user)
        return user

    def deactivate(self, user: User) -> User:
        user.is_active = False
        self._db.commit()
        return user

    def list_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        return self._db.query(User).offset(offset).limit(limit).all()
