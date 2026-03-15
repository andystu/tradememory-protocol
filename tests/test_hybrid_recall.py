"""Tests for hybrid_recall: vector + OWM fusion and ensure_negative_balance.

Reference: ARCHITECTURE_RULES.md Section 7
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from tradememory.hybrid_recall import (
    _cosine_similarity,
    ensure_negative_balance,
    hybrid_recall,
)
from tradememory.owm.context import ContextVector
from tradememory.owm.recall import ScoredMemory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_ago(days: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


def _make_memory(
    id: str = "m1",
    pnl_r: float | None = None,
    confidence: float = 0.5,
    days_ago: float = 1.0,
    memory_type: str = "episodic",
    context: dict | None = None,
    embedding: list[float] | None = None,
) -> dict:
    m = {
        "id": id,
        "pnl_r": pnl_r,
        "confidence": confidence,
        "timestamp": _ts_ago(days_ago),
        "memory_type": memory_type,
        "context": context or {},
    }
    if embedding is not None:
        m["embedding"] = embedding
    return m


def _ctx(**kwargs) -> ContextVector:
    return ContextVector(**kwargs)


# ---------------------------------------------------------------------------
# 1. test_hybrid_happy_path
# ---------------------------------------------------------------------------

def test_hybrid_happy_path():
    """With query_embedding + memory embeddings, hybrid path runs and
    final_score = alpha * vector_sim + (1 - alpha) * owm_score."""
    query_emb = [1.0, 0.0, 0.0]
    memories = [
        _make_memory(id="m1", pnl_r=2.0, days_ago=1, embedding=[1.0, 0.0, 0.0]),
        _make_memory(id="m2", pnl_r=-1.0, days_ago=1, embedding=[0.0, 1.0, 0.0]),
    ]
    alpha = 0.5
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=query_emb,
        memories=memories,
        alpha=alpha,
        limit=10,
    )
    assert len(results) >= 1
    # Every result should have hybrid components
    for r in results:
        assert "vector_sim" in r.components
        assert "owm_score" in r.components
        assert "alpha" in r.components
        expected = alpha * r.components["vector_sim"] + (1 - alpha) * r.components["owm_score"]
        assert abs(r.score - expected) < 1e-9, f"score {r.score} != expected {expected}"


# ---------------------------------------------------------------------------
# 2. test_fallback_no_embedding
# ---------------------------------------------------------------------------

def test_fallback_no_embedding():
    """query_embedding=None → pure OWM path (no vector_sim in components)."""
    memories = [
        _make_memory(id="m1", pnl_r=1.5, days_ago=1, embedding=[1.0, 0.0]),
        _make_memory(id="m2", pnl_r=-0.5, days_ago=2),
    ]
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=None,
        memories=memories,
        limit=10,
    )
    assert len(results) >= 1
    # Should NOT have hybrid components — pure OWM
    for r in results:
        assert "vector_sim" not in r.components


# ---------------------------------------------------------------------------
# 3. test_fallback_no_memory_embeddings
# ---------------------------------------------------------------------------

def test_fallback_no_memory_embeddings():
    """Memories without embedding field → fallback to pure OWM."""
    query_emb = [1.0, 0.0]
    memories = [
        _make_memory(id="m1", pnl_r=1.0, days_ago=1),  # no embedding
        _make_memory(id="m2", pnl_r=-0.5, days_ago=2),  # no embedding
    ]
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=query_emb,
        memories=memories,
        limit=10,
    )
    assert len(results) >= 1
    for r in results:
        assert "vector_sim" not in r.components


# ---------------------------------------------------------------------------
# 4. test_alpha_zero
# ---------------------------------------------------------------------------

def test_alpha_zero():
    """alpha=0 → final_score = pure OWM score (vector_sim weight is 0)."""
    query_emb = [1.0, 0.0, 0.0]
    memories = [
        _make_memory(id="m1", pnl_r=2.0, days_ago=1, embedding=[1.0, 0.0, 0.0]),
        _make_memory(id="m2", pnl_r=-1.0, days_ago=1, embedding=[0.0, 1.0, 0.0]),
    ]
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=query_emb,
        memories=memories,
        alpha=0.0,
        limit=10,
    )
    for r in results:
        assert abs(r.score - r.components["owm_score"]) < 1e-9


# ---------------------------------------------------------------------------
# 5. test_alpha_one
# ---------------------------------------------------------------------------

def test_alpha_one():
    """alpha=1 → vector similarity dominates ranking."""
    query_emb = [0.0, 1.0, 0.0]
    # m1 embedding is orthogonal to query, m2 is parallel
    memories = [
        _make_memory(id="m1", pnl_r=5.0, days_ago=1, embedding=[1.0, 0.0, 0.0]),
        _make_memory(id="m2", pnl_r=-1.0, days_ago=1, embedding=[0.0, 1.0, 0.0]),
    ]
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=query_emb,
        memories=memories,
        alpha=1.0,
        limit=10,
    )
    # m2 should rank first (cos_sim=1.0 vs m1 cos_sim=0.0)
    assert results[0].memory_id == "m2"
    assert abs(results[0].score - results[0].components["vector_sim"]) < 1e-9


# ---------------------------------------------------------------------------
# 6. test_ensure_negative_balance
# ---------------------------------------------------------------------------

def test_ensure_negative_balance():
    """All-positive results → at least 20% negative after balance enforcement."""
    query_emb = [1.0, 0.0, 0.0]
    # 5 positive + 5 negative memories, positives have higher OWM scores
    memories = []
    for i in range(5):
        memories.append(
            _make_memory(id=f"pos{i}", pnl_r=2.0 + i, days_ago=1, embedding=[1.0, 0.0, 0.0])
        )
    for i in range(5):
        memories.append(
            _make_memory(id=f"neg{i}", pnl_r=-1.0 - i, days_ago=10, embedding=[0.0, 0.0, 1.0])
        )
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=query_emb,
        memories=memories,
        alpha=0.3,
        limit=5,
    )
    neg_count = sum(1 for r in results if r.data.get("pnl_r", 0) < 0)
    assert neg_count >= 1, f"Expected >=1 negative in 5 results, got {neg_count}"


# ---------------------------------------------------------------------------
# 7. test_ensure_negative_balance_already_met
# ---------------------------------------------------------------------------

def test_ensure_negative_balance_already_met():
    """When enough negatives already present, ensure_negative_balance is a no-op."""
    results = [
        ScoredMemory(memory_id="p1", memory_type="episodic", score=0.9, data={"pnl_r": 2.0}),
        ScoredMemory(memory_id="p2", memory_type="episodic", score=0.8, data={"pnl_r": 1.0}),
        ScoredMemory(memory_id="n1", memory_type="episodic", score=0.7, data={"pnl_r": -1.0}),
        ScoredMemory(memory_id="n2", memory_type="episodic", score=0.6, data={"pnl_r": -2.0}),
        ScoredMemory(memory_id="p3", memory_type="episodic", score=0.5, data={"pnl_r": 0.5}),
    ]
    # 2/5 = 40% negative, already above 20%
    balanced = ensure_negative_balance(results, results)
    ids_before = [r.memory_id for r in results]
    ids_after = [r.memory_id for r in balanced]
    assert set(ids_before) == set(ids_after), "Should not swap when ratio already met"


# ---------------------------------------------------------------------------
# 8. test_empty_memories
# ---------------------------------------------------------------------------

def test_empty_memories():
    """Empty memory list → returns [] without crash."""
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=[1.0, 0.0],
        memories=[],
        limit=10,
    )
    assert results == []


# ---------------------------------------------------------------------------
# 9. test_single_memory
# ---------------------------------------------------------------------------

def test_single_memory():
    """Single memory works correctly in both hybrid and fallback paths."""
    emb = [1.0, 0.0]
    mem = _make_memory(id="solo", pnl_r=1.5, days_ago=1, embedding=emb)

    # Hybrid path
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=emb,
        memories=[mem],
        alpha=0.5,
        limit=10,
    )
    assert len(results) == 1
    assert results[0].memory_id == "solo"

    # Fallback path
    results2 = hybrid_recall(
        query_context=_ctx(),
        query_embedding=None,
        memories=[mem],
        limit=10,
    )
    assert len(results2) == 1
    assert results2[0].memory_id == "solo"


# ---------------------------------------------------------------------------
# 10. test_all_negative_memories
# ---------------------------------------------------------------------------

def test_all_negative_memories():
    """All negative pnl_r memories → no crash, returns valid results."""
    memories = [
        _make_memory(id=f"n{i}", pnl_r=-1.0 * (i + 1), days_ago=i + 1, embedding=[1.0, 0.0])
        for i in range(5)
    ]
    results = hybrid_recall(
        query_context=_ctx(),
        query_embedding=[1.0, 0.0],
        memories=memories,
        alpha=0.3,
        limit=5,
    )
    assert len(results) == 5
    # All should be negative
    for r in results:
        assert r.data.get("pnl_r", 0) < 0


# ---------------------------------------------------------------------------
# 11. test_limit_respected
# ---------------------------------------------------------------------------

def test_limit_respected():
    """limit parameter correctly caps the number of returned results."""
    memories = [
        _make_memory(id=f"m{i}", pnl_r=float(i), days_ago=1, embedding=[1.0, 0.0])
        for i in range(20)
    ]
    for limit in [1, 3, 5, 10]:
        results = hybrid_recall(
            query_context=_ctx(),
            query_embedding=[1.0, 0.0],
            memories=memories,
            alpha=0.3,
            limit=limit,
        )
        assert len(results) <= limit, f"Expected <={limit} results, got {len(results)}"


# ---------------------------------------------------------------------------
# 12. test_cosine_similarity_correctness
# ---------------------------------------------------------------------------

def test_cosine_similarity_correctness():
    """Verify cosine similarity with known vectors."""
    # Identical vectors → 1.0
    assert abs(_cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9

    # Orthogonal vectors → 0.0
    assert abs(_cosine_similarity([1, 0, 0], [0, 1, 0])) < 1e-9

    # Opposite vectors → -1.0
    assert abs(_cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 1e-9

    # 45 degree angle → cos(45°) ≈ 0.7071
    val = _cosine_similarity([1, 0], [1, 1])
    expected = 1.0 / math.sqrt(2)
    assert abs(val - expected) < 1e-6

    # Scaled vectors (same direction) → 1.0
    assert abs(_cosine_similarity([3, 4], [6, 8]) - 1.0) < 1e-9

    # Empty vectors → 0.0
    assert _cosine_similarity([], []) == 0.0

    # Mismatched lengths → 0.0
    assert _cosine_similarity([1, 0], [1, 0, 0]) == 0.0

    # Zero vector → 0.0
    assert _cosine_similarity([0, 0], [1, 1]) == 0.0
