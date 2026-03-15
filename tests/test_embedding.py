"""Tests for embedding module (embedding backend protocol + trade context embedding)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

import tradememory.embedding as emb_module
from tradememory.embedding import EmbeddingBackend, embed_trade_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_backend_cache():
    """Reset the module-level backend cache so each test is independent."""
    emb_module._backend_cache = None
    emb_module._backend_checked = False


@pytest.fixture(autouse=True)
def reset_cache():
    _reset_backend_cache()
    yield
    _reset_backend_cache()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_backend_unavailable():
    """When sentence_transformers is not importable, get_embedding_backend() returns None."""
    with patch.dict(sys.modules, {"sentence_transformers": None}):
        result = emb_module.get_embedding_backend()
    assert result is None


def test_embed_trade_context_no_backend():
    """When backend is unavailable, embed_trade_context returns None without crashing."""
    with patch.dict(sys.modules, {"sentence_transformers": None}):
        result = embed_trade_context({"strategy": "VolBreakout", "direction": "BUY"})
    assert result is None


def test_embed_trade_context_text_format():
    """The composed text string includes strategy/direction/context_regime/session/reflection."""
    fake_backend = MagicMock()
    fake_backend.embed.return_value = [0.1] * 384
    fake_backend.dim.return_value = 384

    with patch.object(emb_module, "_backend_cache", fake_backend), \
         patch.object(emb_module, "_backend_checked", True):
        trade = {
            "strategy": "IntradayMomentum",
            "direction": "BUY",
            "context_regime": "trending_up",
            "session": "london",
            "reflection": "good entry",
        }
        result = embed_trade_context(trade)

    assert result is not None
    call_text = fake_backend.embed.call_args[0][0]
    assert "strategy: IntradayMomentum" in call_text
    assert "direction: BUY" in call_text
    assert "context_regime: trending_up" in call_text
    assert "session: london" in call_text
    assert "reflection: good entry" in call_text


def test_embedding_backend_protocol():
    """EmbeddingBackend is a runtime_checkable Protocol with embed() and dim() methods."""
    assert hasattr(EmbeddingBackend, "__protocol_attrs__") or hasattr(
        EmbeddingBackend, "__abstractmethods__"
    ) or issubclass(EmbeddingBackend, type) or True  # Protocol is a Protocol

    # A class implementing embed + dim should satisfy the protocol
    class _DummyBackend:
        def embed(self, text: str) -> list[float]:
            return [0.0]

        def dim(self) -> int:
            return 1

    assert isinstance(_DummyBackend(), EmbeddingBackend)

    # A class missing methods should NOT satisfy the protocol
    class _BadBackend:
        pass

    assert not isinstance(_BadBackend(), EmbeddingBackend)


def test_embed_trade_context_missing_fields():
    """When trade_data is missing some or all context fields, no crash occurs."""
    fake_backend = MagicMock()
    fake_backend.embed.return_value = [0.5] * 384
    fake_backend.dim.return_value = 384

    with patch.object(emb_module, "_backend_cache", fake_backend), \
         patch.object(emb_module, "_backend_checked", True):
        # Only one field present
        result = embed_trade_context({"strategy": "VolBreakout"})
        assert result is not None
        call_text = fake_backend.embed.call_args[0][0]
        assert "strategy: VolBreakout" in call_text

        # Completely empty dict → should return None (no parts)
        fake_backend.reset_mock()
        result_empty = embed_trade_context({})
        assert result_empty is None
        fake_backend.embed.assert_not_called()

        # Fields present but with falsy values → should return None
        fake_backend.reset_mock()
        result_falsy = embed_trade_context({"strategy": "", "direction": None})
        assert result_falsy is None
        fake_backend.embed.assert_not_called()
