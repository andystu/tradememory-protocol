"""Tests for OWM auto-induction (episodic → semantic promotion)."""

import pytest

from tradememory.owm.induction import check_auto_induction


def _make_episodic(pattern_name, pnl_r=1.0, direction="long", strategy="VolBreakout"):
    return {
        "pattern_name": pattern_name,
        "pnl_r": pnl_r,
        "direction": direction,
        "strategy": strategy,
    }


class TestAutoInduction:
    """Auto-induction triggers at threshold."""

    def test_exact_threshold_triggers(self):
        """10 memories with same pattern → 1 semantic memory."""
        memories = [_make_episodic("breakout") for _ in range(10)]
        result = check_auto_induction(memories, threshold=10)
        assert len(result) == 1
        assert result[0]["pattern_name"] == "breakout"
        assert result[0]["sample_size"] == 10
        assert result[0]["source"] == "auto_induction"

    def test_below_threshold_no_induction(self):
        """9 memories → no induction."""
        memories = [_make_episodic("breakout") for _ in range(9)]
        result = check_auto_induction(memories, threshold=10)
        assert result == []

    def test_above_threshold(self):
        """15 memories → induction with correct sample_size."""
        memories = [_make_episodic("breakout") for _ in range(15)]
        result = check_auto_induction(memories, threshold=10)
        assert len(result) == 1
        assert result[0]["sample_size"] == 15

    def test_multiple_patterns(self):
        """Two patterns both above threshold → two semantic memories."""
        memories = (
            [_make_episodic("breakout") for _ in range(10)]
            + [_make_episodic("pullback") for _ in range(12)]
        )
        result = check_auto_induction(memories, threshold=10)
        names = {r["pattern_name"] for r in result}
        assert names == {"breakout", "pullback"}

    def test_mixed_one_above_one_below(self):
        """One pattern at threshold, another below → only one induced."""
        memories = (
            [_make_episodic("breakout") for _ in range(10)]
            + [_make_episodic("pullback") for _ in range(5)]
        )
        result = check_auto_induction(memories, threshold=10)
        assert len(result) == 1
        assert result[0]["pattern_name"] == "breakout"

    def test_win_rate_calculation(self):
        """Win rate computed from positive pnl_r."""
        memories = [_make_episodic("x", pnl_r=1.0) for _ in range(7)]
        memories += [_make_episodic("x", pnl_r=-0.5) for _ in range(3)]
        result = check_auto_induction(memories, threshold=10)
        assert result[0]["win_rate"] == 0.7

    def test_avg_pnl_r(self):
        """Average pnl_r correctly computed."""
        memories = [_make_episodic("x", pnl_r=2.0) for _ in range(5)]
        memories += [_make_episodic("x", pnl_r=-1.0) for _ in range(5)]
        result = check_auto_induction(memories, threshold=10)
        assert result[0]["avg_pnl_r"] == pytest.approx(0.5, abs=0.001)

    def test_directions_and_strategies_collected(self):
        """Unique directions and strategies aggregated."""
        memories = [_make_episodic("x", direction="long", strategy="VolBreakout") for _ in range(5)]
        memories += [_make_episodic("x", direction="short", strategy="MeanReversion") for _ in range(5)]
        result = check_auto_induction(memories, threshold=10)
        assert result[0]["directions"] == ["long", "short"]
        assert result[0]["strategies"] == ["MeanReversion", "VolBreakout"]

    def test_empty_input(self):
        """Empty list → no induction."""
        assert check_auto_induction([]) == []

    def test_missing_pattern_name_skipped(self):
        """Memories without pattern_name are ignored."""
        memories = [{"pnl_r": 1.0} for _ in range(20)]
        assert check_auto_induction(memories) == []

    def test_threshold_validation(self):
        """Threshold < 1 raises ValueError."""
        with pytest.raises(ValueError, match="threshold must be >= 1"):
            check_auto_induction([], threshold=0)

    def test_missing_pnl_r_graceful(self):
        """Memories without pnl_r → win_rate=0, avg_pnl_r=0."""
        memories = [{"pattern_name": "x"} for _ in range(10)]
        result = check_auto_induction(memories, threshold=10)
        assert result[0]["win_rate"] == 0.0
        assert result[0]["avg_pnl_r"] == 0.0
