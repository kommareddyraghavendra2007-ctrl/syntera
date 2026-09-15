"""
Application configuration.

All settings are loaded from environment variables.
Never hard-code credentials.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment."""

    # Database
    database_url: str
    database_pool_size: int
    database_max_overflow: int

    # Redis
    redis_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expiry_minutes: int
    jwt_refresh_expiry_days: int

    # Stripe payments
    stripe_secret_key: str
    stripe_webhook_secret: str

    # Mail
    mail_server: str
    mail_port: int
    mail_use_tls: bool
    mail_username: str
    mail_password: str

    # Application
    app_env: str
    debug: bool
    allowed_origins: list[str]

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables with safe defaults."""
        return cls(
            database_url=os.environ.get("DATABASE_URL", "sqlite:///./shopcore.db"),
            database_pool_size=int(os.environ.get("DATABASE_POOL_SIZE", "5")),
            database_max_overflow=int(os.environ.get("DATABASE_MAX_OVERFLOW", "10")),
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379"),
            jwt_secret_key=os.environ.get("JWT_SECRET_KEY", "change-me-in-production"),
            jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
            jwt_expiry_minutes=int(os.environ.get("JWT_EXPIRY_MINUTES", "60")),
            jwt_refresh_expiry_days=int(os.environ.get("JWT_REFRESH_EXPIRY_DAYS", "30")),
            stripe_secret_key=os.environ.get("STRIPE_SECRET_KEY", ""),
            stripe_webhook_secret=os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
            mail_server=os.environ.get("MAIL_SERVER", "localhost"),
            mail_port=int(os.environ.get("MAIL_PORT", "587")),
            mail_use_tls=os.environ.get("MAIL_USE_TLS", "true").lower() == "true",
            mail_username=os.environ.get("MAIL_USERNAME", ""),
            mail_password=os.environ.get("MAIL_PASSWORD", ""),
            app_env=os.environ.get("APP_ENV", "development"),
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            allowed_origins=os.environ.get(
                "ALLOWED_ORIGINS", "http://localhost:3000"
            ).split(","),
        )


# Singleton — loaded once at import time
settings = Settings.from_env()
