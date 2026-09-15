"""
OpenAI embedding provider.

Supports text-embedding-3-small (1536d), text-embedding-3-large (3072d),
and text-embedding-ada-002 (1536d).

Dimensions are read from model metadata at init time — never hard-coded.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider

logger = get_logger(__name__)

_MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text embeddings via the official openai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 32,
    ) -> None:
        try:
            from openai import OpenAI  # noqa: PLC0415

            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url or "https://api.openai.com/v1",
            )
        except ImportError as e:
            raise RuntimeError(
                "openai package is required for OpenAIEmbeddingProvider. "
                "Install it with: pip install openai"
            ) from e

        self._model = model
        self._batch_size = batch_size
        self._dims = dimensions or _MODEL_DIMENSIONS.get(model, 1536)
        logger.info(
            "openai_embedding_provider_init",
            extra={"model": model, "dimensions": self._dims},
        )

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            # Truncate each text to avoid token limit errors
            batch = [t[:8000] for t in batch]
            response = self._client.embeddings.create(
                model=self._model,
                input=batch,
            )
            results.extend([item.embedding for item in response.data])
        return results
