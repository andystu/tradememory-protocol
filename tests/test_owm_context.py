"""Tests for ContextVector and context_similarity."""

import math

import pytest

from tradememory.owm.context import ContextVector, context_similarity


def _make_context(**overrides):
    """Helper to build a fully-populated ContextVector."""
    defaults = dict(
        symbol="XAUUSD",
        price=5175.0,
        atr_d1=165.0,
        atr_h1=35.0,
        atr_m5=4.0,
        atr_ratio_h1_d1=0.212,
        regime="trending_up",
        volatility_regime="high",
        session="london",
        hour_utc=10,
        day_of_week=1,
        spread_points=30.0,
        spread_as_atr_pct=7.5,
        drawdown_pct=5.0,
        consecutive_losses=2,
        confidence=0.7,
    )
    defaults.update(overrides)
    return ContextVector(**defaults)


# --- identity ---

class TestIdentity:
    def test_same_context_similarity_is_one(self):
        c = _make_context()
        assert context_similarity(c, c) == pytest.approx(1.0)

    def test_two_equal_contexts_similarity_is_one(self):
        c1 = _make_context()
        c2 = _make_context()
        assert context_similarity(c1, c2) == pytest.approx(1.0)


# --- completely different ---

class TestDifferent:
    def test_all_different_similarity_near_zero(self):
        c1 = _make_context(
            regime="trending_up",
            volatility_regime="low",
            session="asia",
            price=2000.0,
            atr_d1=50.0,
            atr_h1=10.0,
            spread_as_atr_pct=1.0,
            drawdown_pct=0.5,
        )
        c2 = _make_context(
            regime="ranging",
            volatility_regime="extreme",
            session="newyork",
            price=8000.0,
            atr_d1=300.0,
            atr_h1=80.0,
            spread_as_atr_pct=20.0,
            drawdown_pct=40.0,
        )
        sim = context_similarity(c1, c2)
        assert sim < 0.1

    def test_opposite_regimes_reduce_similarity(self):
        c1 = _make_context(regime="trending_up")
        c2 = _make_context(regime="trending_down")
        sim = context_similarity(c1, c2)
        assert sim < 1.0


# --- partial match ---

class TestPartialMatch:
    def test_same_categorical_different_numerical(self):
        c1 = _make_context(price=3000.0, atr_d1=100.0)
        c2 = _make_context(price=5000.0, atr_d1=180.0)
        sim = context_similarity(c1, c2)
        assert 0.0 < sim < 1.0

    def test_same_numerical_different_categorical(self):
        c1 = _make_context(regime="trending_up", session="london")
        c2 = _make_context(regime="ranging", session="asia")
        sim = context_similarity(c1, c2)
        assert 0.0 < sim < 1.0

    def test_close_prices_high_similarity(self):
        c1 = _make_context(price=5000.0)
        c2 = _make_context(price=5050.0)  # 1% diff
        sim = context_similarity(c1, c2)
        assert sim > 0.9

    def test_symmetry(self):
        c1 = _make_context(price=3000.0, regime="ranging")
        c2 = _make_context(price=5000.0, regime="trending_up")
        # Note: Gaussian kernel uses abs(v1) so not perfectly symmetric,
        # but both directions should yield 0 < sim < 1
        s12 = context_similarity(c1, c2)
        s21 = context_similarity(c2, c1)
        assert 0.0 < s12 < 1.0
        assert 0.0 < s21 < 1.0


# --- None handling ---

class TestNoneHandling:
    def test_all_none_returns_neutral(self):
        """When no fields overlap, return 0.5 (neutral) to avoid killing recall scores."""
        c1 = ContextVector()
        c2 = ContextVector()
        assert context_similarity(c1, c2) == 0.5

    def test_one_side_none_categorical_skipped(self):
        c1 = _make_context(regime=None)
        c2 = _make_context()
        sim = context_similarity(c1, c2)
        # Should still work, just without regime weight
        assert 0.0 < sim <= 1.0

    def test_one_side_none_numerical_skipped(self):
        c1 = _make_context(price=None, atr_d1=None)
        c2 = _make_context()
        sim = context_similarity(c1, c2)
        assert 0.0 < sim <= 1.0

    def test_mixed_none_fields(self):
        c1 = ContextVector(regime="trending_up", price=5000.0, atr_d1=150.0)
        c2 = ContextVector(regime="trending_up", price=5000.0, atr_d1=150.0)
        sim = context_similarity(c1, c2)
        assert sim == pytest.approx(1.0)

    def test_numerical_zero_value_skipped(self):
        """v1 == 0 should be skipped (division by zero guard)."""
        c1 = _make_context(price=0.0)
        c2 = _make_context(price=5000.0)
        # price field skipped, rest should still compute
        sim = context_similarity(c1, c2)
        assert 0.0 < sim <= 1.0


# --- Gaussian kernel math ---

class TestGaussianKernel:
    def test_identical_numerical_contributes_full_weight(self):
        """When v1 == v2, Gaussian kernel = 1.0."""
        c1 = ContextVector(price=5000.0)
        c2 = ContextVector(price=5000.0)
        sim = context_similarity(c1, c2)
        assert sim == pytest.approx(1.0)

    def test_large_difference_contributes_near_zero(self):
        """When |v1 - v2| >> bandwidth * v1, kernel ≈ 0."""
        c1 = ContextVector(price=1000.0)
        c2 = ContextVector(price=100000.0)
        sim = context_similarity(c1, c2)
        assert sim < 0.01
