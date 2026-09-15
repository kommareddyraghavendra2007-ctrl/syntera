"""
Deterministic hash-based embedding provider for development and testing.

Produces 384-dimensional pseudo-embeddings derived from SHA-256 hashes.
These are NOT semantically meaningful — they allow the rest of the pipeline
to run without any external API. Switch to openai or fastembed for production.
"""
from __future__ import annotations

import math
import struct
from hashlib import sha256

from app.embeddings.base import EmbeddingProvider

_DIMENSIONS = 384


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, zero-dependency embedding provider for local dev."""

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        # Produce a stable pseudo-random unit vector from SHA-256 of text
        digest = sha256(text.encode("utf-8", errors="replace")).digest()
        # Extend to required dimensions by repeating the hash with different seeds
        raw: list[float] = []
        seed = 0
        while len(raw) < _DIMENSIONS:
            extra = sha256(digest + seed.to_bytes(4, "big")).digest()
            for i in range(0, len(extra) - 3, 4):
                val = struct.unpack_from(">i", extra, i)[0]
                raw.append(float(val))
            seed += 1

        vec = raw[:_DIMENSIONS]
        # L2-normalise
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]
