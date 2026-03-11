"""Embedding backend for hybrid recall (pgvector integration).

Provides a Protocol-based abstraction for embedding backends,
with SentenceTransformer as the default implementation.
Gracefully degrades to None when dependencies are unavailable.
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class EmbeddingBackend(Protocol):
    """Abstract interface for embedding backends."""

    def embed(self, text: str) -> list[float]: ...

    def dim(self) -> int: ...


class SentenceTransformerBackend:
    """Embedding backend using sentence-transformers (all-MiniLM-L6-v2, 384-dim)."""

    MODEL_NAME = "all-MiniLM-L6-v2"
    DIMENSIONS = 384

    def __init__(self) -> None:
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.MODEL_NAME)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load_model()
        vector = model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def dim(self) -> int:
        return self.DIMENSIONS


_backend_cache: Optional[EmbeddingBackend] = None
_backend_checked = False


def get_embedding_backend() -> Optional[EmbeddingBackend]:
    """Factory: returns SentenceTransformerBackend if available, else None."""
    global _backend_cache, _backend_checked
    if _backend_checked:
        return _backend_cache
    _backend_checked = True
    try:
        import sentence_transformers  # noqa: F401

        _backend_cache = SentenceTransformerBackend()
    except ImportError:
        logger.warning(
            "sentence-transformers not installed — "
            "embedding features disabled, falling back to pure OWM recall"
        )
        _backend_cache = None
    return _backend_cache


def embed_trade_context(trade_data: dict) -> Optional[list[float]]:
    """Embed a trade's context into a vector.

    Combines strategy, direction, context_regime, session, and reflection
    into a single text string and embeds it.

    Returns None if embedding backend is unavailable or embedding fails.
    """
    backend = get_embedding_backend()
    if backend is None:
        return None

    parts = []
    for key in ("strategy", "direction", "context_regime", "session", "reflection"):
        value = trade_data.get(key)
        if value:
            parts.append(f"{key}: {value}")

    if not parts:
        logger.warning("embed_trade_context: no context fields found in trade_data")
        return None

    text = "; ".join(parts)
    try:
        return backend.embed(text)
    except Exception as e:
        logger.warning(f"Embedding failed for trade context: {e}")
        return None
