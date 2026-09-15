"""
ShopCore FastAPI application entry point.

Route organization:
  /auth    — registration, login, logout, token refresh
  /users   — profile management
  /orders  — order creation and management
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database.connection import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


def create_app() -> FastAPI:
    from src.api import auth, users, orders  # noqa: PLC0415

    app = FastAPI(
        title="ShopCore API",
        description="E-commerce backend: users, authentication, and orders.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(orders.router)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "ShopCore"}

    return app


app = create_app()
