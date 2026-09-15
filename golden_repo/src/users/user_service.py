"""
UserService — business logic for user management.

Calls: UserRepository
Called by: API layer (api/users.py)
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from src.database.models import User
from src.users.user_repository import UserRepository


class UserService:
    """Business logic for user profile management."""

    def get_profile(self, db: Session, user_id: str) -> User:
        repo = UserRepository(db)
        user = repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    def update_profile(self, db: Session, user: User, first_name: str | None, last_name: str | None) -> User:
        repo = UserRepository(db)
        return repo.update_profile(user, first_name=first_name, last_name=last_name)

    def list_users(self, db: Session, limit: int = 100, offset: int = 0) -> list[User]:
        repo = UserRepository(db)
        return repo.list_all(limit=limit, offset=offset)


user_service = UserService()
