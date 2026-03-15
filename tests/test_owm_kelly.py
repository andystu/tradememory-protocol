"""Tests for OWM Kelly criterion position sizing."""

import pytest

from tradememory.owm.kelly import kelly_from_memory
from tradememory.owm.recall import ScoredMemory


def _make_memory(pnl_r: float, score: float = 1.0) -> ScoredMemory:
    """Helper to create a ScoredMemory with given pnl_r and score."""
    return ScoredMemory(
        memory_id="test",
        memory_type="episodic",
        score=score,
        data={"pnl_r": pnl_r},
    )


def _make_memories(pnl_rs: list[float], score: float = 1.0) -> list[ScoredMemory]:
    return [_make_memory(pnl_r, score) for pnl_r in pnl_rs]


class TestKellyMinimumData:
    """Memories < 10 should return 0.0."""

    def test_empty(self):
        assert kelly_from_memory([]) == 0.0

    def test_one_memory(self):
        assert kelly_from_memory([_make_memory(1.5)]) == 0.0

    def test_nine_memories(self):
        mems = _make_memories([1.0] * 9)
        assert kelly_from_memory(mems) == 0.0

    def test_ten_memories_returns_nonzero(self):
        """Exactly 10 should be enough to compute."""
        mems = _make_memories([2.0] * 7 + [-1.0] * 3)
        result = kelly_from_memory(mems)
        assert result > 0.0

    def test_memories_without_pnl_r_dont_count(self):
        """Memories missing pnl_r are filtered out."""
        valid = _make_memories([1.0] * 9)
        no_pnl = ScoredMemory(
            memory_id="no_pnl", memory_type="episodic", score=1.0, data={}
        )
        mems = valid + [no_pnl]
        assert kelly_from_memory(mems) == 0.0  # only 9 valid


class TestKellyAllWins:
    """All winning trades should produce f > 0."""

    def test_all_wins(self):
        mems = _make_memories([2.0] * 12)
        result = kelly_from_memory(mems)
        assert result > 0.0

    def test_all_wins_large_pnl(self):
        mems = _make_memories([10.0] * 15)
        result = kelly_from_memory(mems)
        assert result > 0.0


class TestKellyAllLosses:
    """All losing trades should return 0 (clamped)."""

    def test_all_losses(self):
        mems = _make_memories([-1.0] * 12)
        assert kelly_from_memory(mems) == 0.0

    def test_all_losses_varying(self):
        mems = _make_memories([-0.5, -1.0, -2.0, -0.3] * 3)
        assert kelly_from_memory(mems) == 0.0


class TestKellyRiskAppetite:
    """risk_appetite=0.1 should significantly reduce the result."""

    def test_risk_appetite_scales_down(self):
        mems = _make_memories([2.0] * 8 + [-1.0] * 4)
        normal = kelly_from_memory(mems, risk_appetite=1.0)
        scaled = kelly_from_memory(mems, risk_appetite=0.1)
        assert normal > 0.0
        assert scaled >= 0.0
        assert scaled < normal

    def test_risk_appetite_zero(self):
        mems = _make_memories([2.0] * 8 + [-1.0] * 4)
        assert kelly_from_memory(mems, risk_appetite=0.0) == 0.0


class TestKellyClamp:
    """Result should never exceed 0.5."""

    def test_never_above_half(self):
        # Extreme edge: huge wins, tiny losses, full Kelly, high appetite
        mems = _make_memories([100.0] * 10 + [-0.01] * 2)
        result = kelly_from_memory(mems, fractional=1.0, risk_appetite=10.0)
        assert result <= 0.5

    def test_never_negative(self):
        mems = _make_memories([-5.0] * 12)
        result = kelly_from_memory(mems, fractional=1.0, risk_appetite=5.0)
        assert result >= 0.0


class TestKellyWeighting:
    """OWM score should act as weight in statistics."""

    def test_higher_score_wins_dominate(self):
        # 5 wins with high score, 7 losses with low score
        wins = [_make_memory(2.0, score=5.0) for _ in range(5)]
        losses = [_make_memory(-1.0, score=0.1) for _ in range(7)]
        mems = wins + losses
        result = kelly_from_memory(mems)
        assert result > 0.0

    def test_zero_score_memories_ignored(self):
        """Score=0 memories contribute no weight."""
        wins = [_make_memory(2.0, score=0.0) for _ in range(6)]
        losses = [_make_memory(-1.0, score=1.0) for _ in range(6)]
        mems = wins + losses
        # All wins have zero weight, so effectively all losses → 0
        assert kelly_from_memory(mems) == 0.0
