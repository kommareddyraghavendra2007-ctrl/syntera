"""Authentication API routes — register, login, logout, refresh."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.auth import AuthenticationError, RegistrationError, auth_service
from src.database.connection import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    try:
        user = auth_service.register(
            db, body.email, body.password, body.first_name, body.last_name
        )
        return {"id": user.id, "email": user.email, "message": "Registration successful"}
    except RegistrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and receive JWT tokens."""
    try:
        return auth_service.login(db, body.email, body.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/refresh")
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a refresh token for a new access token."""
    try:
        return auth_service.refresh_access_token(db, body.refresh_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke a refresh token."""
    auth_service.logout(db, body.refresh_token)
