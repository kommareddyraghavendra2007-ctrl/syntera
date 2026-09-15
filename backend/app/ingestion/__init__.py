"""Ingestion package."""
from app.ingestion.pipeline import run_ingestion
from app.ingestion.providers import GitProvider, ZipProvider

__all__ = ["run_ingestion", "GitProvider", "ZipProvider"]
