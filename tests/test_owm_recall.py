"""Tests for OWM core recall algorithm.

Reference: docs/OWM_FRAMEWORK.md Section 3
"""

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from tradememory.owm.recall import (
    ScoredMemory,
    compute_affective_modulation,
    compute_confidence_factor,
    compute_outcome_quality,
    compute_recency,
    outcome_weighted_recall,
    sigmoid,
)
from tradememory.owm.context import ContextVector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts_ago(days: float) -> str:
    """Return ISO timestamp `days` days in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


def _make_memory(
    id: str = "m1",
    pnl_r: float | None = None,
    confidence: float = 0.5,
    days_ago: float = 1.0,
    memory_type: str = "episodic",
    context: dict | None = None,
) -> dict:
    return {
        "id": id,
        "pnl_r": pnl_r,
        "confidence": confidence,
        "timestamp": _ts_ago(days_ago),
        "memory_type": memory_type,
        "context": context or {},
    }


# ---------------------------------------------------------------------------
# sigmoid
# ---------------------------------------------------------------------------

class TestSigmoid:
    def test_zero(self):
        assert sigmoid(0) == 0.5

    def test_large_positive(self):
        assert sigmoid(100) == pytest.approx(1.0)

    def test_large_negative(self):
        assert sigmoid(-100) == pytest.approx(0.0)

    def test_symmetry(self):
        assert sigmoid(2) + sigmoid(-2) == pytest.approx(1.0)

    def test_no_overflow(self):
        """Should not raise even with extreme values."""
        assert sigmoid(1000) == pytest.approx(1.0)
        assert sigmoid(-1000) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# compute_outcome_quality
# ---------------------------------------------------------------------------

class TestOutcomeQuality:
    """Q value boundary tests per OWM_FRAMEWORK.md Section 3.2."""

    def test_plus_3r(self):
        # +3R, sigma_r=1.5 → sigmoid(2*3/1.5) = sigmoid(4) ≈ 0.982
        m = {"pnl_r": 3.0}
        q = compute_outcome_quality(m, sigma_r=1.5, k=2.0)
        assert q == pytest.approx(0.982, abs=0.002)

    def test_minus_3r(self):
        # -3R → sigmoid(-4) ≈ 0.018
        m = {"pnl_r": -3.0}
        q = compute_outcome_quality(m, sigma_r=1.5, k=2.0)
        assert q == pytest.approx(0.018, abs=0.002)

    def test_zero_r(self):
        # 0R → sigmoid(0) = 0.5
        m = {"pnl_r": 0.0}
        q = compute_outcome_quality(m, sigma_r=1.5, k=2.0)
        assert q == pytest.approx(0.5)

    def test_positive_half_r(self):
        # +0.5R → sigmoid(2*0.5/1.5) = sigmoid(0.667) ≈ 0.661
        m = {"pnl_r": 0.5}
        q = compute_outcome_quality(m, sigma_r=1.5, k=2.0)
        assert q == pytest.approx(0.661, abs=0.005)

    def test_negative_1r(self):
        # -1R → sigmoid(-1.333) ≈ 0.209
        m = {"pnl_r": -1.0}
        q = compute_outcome_quality(m, sigma_r=1.5, k=2.0)
        assert q == pytest.approx(0.209, abs=0.005)

    def test_no_pnl_r_uses_confidence(self):
        m = {"confidence": 0.8}
        assert compute_outcome_quality(m) == 0.8

    def test_no_pnl_r_no_confidence_defaults_half(self):
        m = {}
        assert compute_outcome_quality(m) == 0.5

    def test_winners_score_higher(self):
        winner = compute_outcome_quality({"pnl_r": 2.0})
        loser = compute_outcome_quality({"pnl_r": -2.0})
        assert winner > loser


# ---------------------------------------------------------------------------
# compute_recency
# ---------------------------------------------------------------------------

class TestRecency:
    """Rec values per OWM_FRAMEWORK.md Section 3.2."""

    def test_1_day(self):
        ts = _ts_ago(1.0)
        rec = compute_recency(ts, tau=30.0, d=0.5)
        # (1 + 1/30)^(-0.5) ≈ 0.9836
        assert rec == pytest.approx(0.984, abs=0.005)

    def test_30_days(self):
        ts = _ts_ago(30.0)
        rec = compute_recency(ts, tau=30.0, d=0.5)
        # (1 + 30/30)^(-0.5) = 2^(-0.5) ≈ 0.707
        assert rec == pytest.approx(0.707, abs=0.005)

    def test_365_days(self):
        ts = _ts_ago(365.0)
        rec = compute_recency(ts, tau=30.0, d=0.5)
        # (1 + 365/30)^(-0.5) = (13.167)^(-0.5) ≈ 0.276
        assert rec == pytest.approx(0.276, abs=0.01)

    def test_zero_days(self):
        ts = datetime.now(timezone.utc).isoformat()
        rec = compute_recency(ts, tau=30.0, d=0.5)
        assert rec == pytest.approx(1.0, abs=0.01)

    def test_monotonically_decreasing(self):
        recs = [compute_recency(_ts_ago(d), tau=30.0, d=0.5) for d in [1, 7, 30, 90, 365]]
        for i in range(len(recs) - 1):
            assert recs[i] > recs[i + 1]

    def test_semantic_slower_decay(self):
        ts = _ts_ago(90.0)
        episodic_rec = compute_recency(ts, tau=30.0, d=0.5)
        semantic_rec = compute_recency(ts, tau=180.0, d=0.3)
        assert semantic_rec > episodic_rec

    def test_handles_z_suffix(self):
        ts = "2020-01-01T00:00:00Z"
        rec = compute_recency(ts, tau=30.0, d=0.5)
        assert 0 < rec < 1


# ---------------------------------------------------------------------------
# compute_confidence_factor
# ---------------------------------------------------------------------------

class TestConfidenceFactor:
    def test_zero_confidence(self):
        assert compute_confidence_factor(0.0) == pytest.approx(0.5)

    def test_full_confidence(self):
        assert compute_confidence_factor(1.0) == pytest.approx(1.0)

    def test_half_confidence(self):
        assert compute_confidence_factor(0.5) == pytest.approx(0.75)

    def test_clamped_above_one(self):
        assert compute_confidence_factor(2.0) == pytest.approx(1.0)

    def test_clamped_below_zero(self):
        assert compute_confidence_factor(-1.0) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# compute_affective_modulation
# ---------------------------------------------------------------------------

class TestAffectiveModulation:
    def test_neutral_state(self):
        m = {"pnl_r": 0.5}
        assert compute_affective_modulation(m) == pytest.approx(1.0)

    def test_drawdown_boosts_large_loss(self):
        m = {"pnl_r": -2.0}
        aff = compute_affective_modulation(m, drawdown_state=0.8)
        # relevance=0.5, raw=1+0.3*0.5=1.15
        assert aff == pytest.approx(1.15)
        assert aff > 1.0

    def test_drawdown_boosts_large_win(self):
        m = {"pnl_r": 3.0}
        aff = compute_affective_modulation(m, drawdown_state=0.8)
        # relevance=0.3, raw=1+0.3*0.3=1.09
        assert aff == pytest.approx(1.09)

    def test_drawdown_neutral_for_small_trades(self):
        m = {"pnl_r": 0.5}
        aff = compute_affective_modulation(m, drawdown_state=0.8)
        assert aff == pytest.approx(1.0)

    def test_losing_streak_surfaces_winners(self):
        m = {"pnl_r": 1.5}
        aff = compute_affective_modulation(m, consecutive_losses=5)
        # relevance=0.3, raw=1.09
        assert aff == pytest.approx(1.09)

    def test_losing_streak_suppresses_losers(self):
        m = {"pnl_r": -0.5}
        aff = compute_affective_modulation(m, consecutive_losses=3)
        # relevance=-0.2, raw=1+0.3*(-0.2)=0.94
        assert aff == pytest.approx(0.94)

    def test_no_pnl_r_neutral(self):
        m = {}
        aff = compute_affective_modulation(m, drawdown_state=0.9, consecutive_losses=5)
        assert aff == pytest.approx(1.0)

    def test_output_bounded(self):
        """Aff must stay in [0.7, 1.3] regardless of inputs."""
        for pnl in [-10, -2, -1, 0, 1, 2, 10]:
            for dd in [0.0, 0.5, 1.0]:
                for cl in [0, 3, 10]:
                    aff = compute_affective_modulation(
                        {"pnl_r": pnl}, drawdown_state=dd, consecutive_losses=cl
                    )
                    assert 0.7 <= aff <= 1.3, f"Out of bounds: pnl={pnl}, dd={dd}, cl={cl} → {aff}"


# ---------------------------------------------------------------------------
# ScoredMemory dataclass
# ---------------------------------------------------------------------------

class TestScoredMemory:
    def test_creation(self):
        sm = ScoredMemory(
            memory_id="m1",
            memory_type="episodic",
            score=0.75,
            components={"Q": 0.9, "Sim": 0.8},
            data={"pnl_r": 2.0},
        )
        assert sm.memory_id == "m1"
        assert sm.score == 0.75
        assert sm.components["Q"] == 0.9

    def test_defaults(self):
        sm = ScoredMemory(memory_id="m2", memory_type="semantic", score=0.5)
        assert sm.components == {}
        assert sm.data == {}


# ---------------------------------------------------------------------------
# outcome_weighted_recall (integration)
# ---------------------------------------------------------------------------

class TestOutcomeWeightedRecall:
    def test_empty_memories_returns_empty(self):
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up")
        result = outcome_weighted_recall(ctx, [], limit=10)
        assert result == []

    def test_returns_scored_memories(self):
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up")
        memories = [
            _make_memory("m1", pnl_r=2.0, days_ago=1, context={"symbol": "XAUUSD", "regime": "trending_up"}),
            _make_memory("m2", pnl_r=-1.0, days_ago=5, context={"symbol": "XAUUSD", "regime": "trending_up"}),
        ]
        result = outcome_weighted_recall(ctx, memories)
        assert len(result) == 2
        assert all(isinstance(r, ScoredMemory) for r in result)

    def test_high_q_high_sim_ranks_first(self):
        """Memory with high Q + high Sim should outrank low Q + low Sim."""
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up", session="london")
        memories = [
            _make_memory("winner", pnl_r=3.0, days_ago=1, context={"symbol": "XAUUSD", "regime": "trending_up", "session": "london"}),
            _make_memory("loser", pnl_r=-2.0, days_ago=1, context={"symbol": "EURUSD", "regime": "ranging", "session": "asia"}),
        ]
        result = outcome_weighted_recall(ctx, memories)
        assert result[0].memory_id == "winner"
        assert result[0].score > result[1].score

    def test_limit_respected(self):
        ctx = ContextVector(symbol="XAUUSD")
        memories = [_make_memory(f"m{i}", pnl_r=float(i), days_ago=1, context={"symbol": "XAUUSD"}) for i in range(20)]
        result = outcome_weighted_recall(ctx, memories, limit=5)
        assert len(result) == 5

    def test_sorted_descending(self):
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up")
        memories = [
            _make_memory("m1", pnl_r=-2.0, days_ago=30, context={"symbol": "XAUUSD", "regime": "trending_up"}),
            _make_memory("m2", pnl_r=2.0, days_ago=1, context={"symbol": "XAUUSD", "regime": "trending_up"}),
            _make_memory("m3", pnl_r=0.5, days_ago=10, context={"symbol": "XAUUSD", "regime": "trending_up"}),
        ]
        result = outcome_weighted_recall(ctx, memories)
        scores = [r.score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_components_present(self):
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up")
        memories = [_make_memory("m1", pnl_r=1.0, days_ago=5, context={"symbol": "XAUUSD", "regime": "trending_up"})]
        result = outcome_weighted_recall(ctx, memories)
        assert len(result) == 1
        for key in ("Q", "Sim", "Rec", "Conf", "Aff"):
            assert key in result[0].components

    def test_affective_state_affects_ranking(self):
        """During drawdown, large-loss memories should get boosted."""
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up")
        memories = [
            _make_memory("big_loss", pnl_r=-2.0, days_ago=1, confidence=0.8, context={"symbol": "XAUUSD", "regime": "trending_up"}),
            _make_memory("small_loss", pnl_r=-0.5, days_ago=1, confidence=0.8, context={"symbol": "XAUUSD", "regime": "trending_up"}),
        ]
        result_neutral = outcome_weighted_recall(ctx, memories)
        result_drawdown = outcome_weighted_recall(ctx, memories, affective_state={"drawdown_state": 0.9})

        # In drawdown, big_loss gets Aff boost (1.15), small_loss stays 1.0
        # So big_loss's relative position should improve
        neutral_big_loss_score = next(r for r in result_neutral if r.memory_id == "big_loss").score
        drawdown_big_loss_score = next(r for r in result_drawdown if r.memory_id == "big_loss").score
        assert drawdown_big_loss_score > neutral_big_loss_score

    def test_semantic_memory_slower_decay(self):
        """Semantic memories should decay slower than episodic."""
        ctx = ContextVector(symbol="XAUUSD", regime="trending_up")
        base_ctx = {"symbol": "XAUUSD", "regime": "trending_up"}
        episodic = _make_memory("ep", pnl_r=1.0, days_ago=90, memory_type="episodic", context=base_ctx)
        semantic = _make_memory("sem", pnl_r=None, confidence=0.7, days_ago=90, memory_type="semantic", context=base_ctx)

        result = outcome_weighted_recall(ctx, [episodic, semantic])
        ep_rec = next(r for r in result if r.memory_id == "ep").components["Rec"]
        sem_rec = next(r for r in result if r.memory_id == "sem").components["Rec"]
        assert sem_rec > ep_rec
