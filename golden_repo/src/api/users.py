"""User profile API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.auth.dependencies import get_admin_user, get_current_user
from src.database.connection import get_db
from src.database.models import User
from src.users import user_service

router = APIRouter(prefix="/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None


@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_admin": current_user.is_admin,
        "is_verified": current_user.is_verified,
    }


@router.put("/me")
def update_my_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile fields."""
    updated = user_service.update_profile(
        db, current_user, body.first_name, body.last_name
    )
    return {
        "id": updated.id,
        "email": updated.email,
        "first_name": updated.first_name,
        "last_name": updated.last_name,
    }


@router.get("/admin/all")
def list_all_users(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Admin only: list all registered users."""
    users = user_service.list_users(db, limit=limit)
    return [
        {"id": u.id, "email": u.email, "is_active": u.is_active}
        for u in users
    ]
