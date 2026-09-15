"""Tests for the hash embedding provider."""
from __future__ import annotations

import math
import pytest
from app.embeddings.hash_provider import HashEmbeddingProvider


def test_dimensions():
    assert HashEmbeddingProvider().dimensions == 384


def test_single_embed_length():
    assert len(HashEmbeddingProvider().embed_one("hello world")) == 384


def test_unit_vector():
    vec = HashEmbeddingProvider().embed_one("test embedding")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-5


def test_deterministic():
    p = HashEmbeddingProvider()
    assert p.embed_one("same text") == p.embed_one("same text")


def test_different_texts_differ():
    p = HashEmbeddingProvider()
    assert p.embed_one("authenticate user") != p.embed_one("create order")


def test_batch_embed():
    vecs = HashEmbeddingProvider().embed_texts(["auth", "user", "order"])
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)


def test_empty_text():
    assert len(HashEmbeddingProvider().embed_one("")) == 384
