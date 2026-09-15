"""Abstract embedding provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Produce dense vector embeddings for text."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the vector dimension for this model."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns a list of float vectors."""

    def embed_one(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
