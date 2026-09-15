"""LLM provider factory — reads LLM_PROVIDER from settings."""
from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.llm.base import LLMProvider

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    cfg = settings or get_settings()
    provider = cfg.llm_provider.lower()

    if provider == "openai":
        from app.llm.openai_provider import OpenAILLMProvider  # noqa: PLC0415

        if not cfg.llm_api_key:
            raise RuntimeError(
                "LLM_API_KEY environment variable is required for OpenAI provider"
            )
        return OpenAILLMProvider(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
            base_url=cfg.llm_base_url,
            timeout=cfg.llm_timeout_seconds,
        )

    raise RuntimeError(
        f"Unsupported LLM_PROVIDER: '{provider}'. Supported: openai"
    )
