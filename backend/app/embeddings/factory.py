"""
Embedding provider factory.

Reads EMBEDDING_PROVIDER from settings and returns the appropriate instance.
Supported values: "hash" (dev default), "openai", "fastembed"
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    cfg = settings or get_settings()
    provider = cfg.embedding_provider.lower()

    if provider == "openai":
        from app.embeddings.openai_provider import OpenAIEmbeddingProvider  # noqa: PLC0415

        if not cfg.embedding_api_key and not cfg.llm_api_key:
            raise RuntimeError(
                "EMBEDDING_API_KEY or LLM_API_KEY must be set for OpenAI embeddings"
            )
        return OpenAIEmbeddingProvider(
            api_key=cfg.embedding_api_key or cfg.llm_api_key,  # type: ignore[arg-type]
            model=cfg.embedding_model,
            base_url=cfg.embedding_base_url,
            dimensions=cfg.embedding_dimensions,
            batch_size=cfg.embedding_batch_size,
        )

    if provider == "fastembed":
        try:
            from app.embeddings.fastembed_provider import FastEmbedProvider  # noqa: PLC0415

            return FastEmbedProvider(model=cfg.embedding_model)
        except ImportError:
            logger.warning(
                "fastembed_unavailable_falling_back_to_hash",
                extra={"model": cfg.embedding_model},
            )

    if provider != "hash":
        logger.warning(
            "unknown_embedding_provider_falling_back_to_hash",
            extra={"provider": provider},
        )

    from app.embeddings.hash_provider import HashEmbeddingProvider  # noqa: PLC0415

    logger.info("embedding_provider_hash_active")
    return HashEmbeddingProvider()
