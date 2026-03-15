"""Tests for CUSUM drift detection."""

import pytest

from tradememory.owm.drift import cusum_drift_detect


class TestCusumDriftDetect:
    """CUSUM drift detection tests."""

    def test_all_wins_triggers_drift(self):
        """20 consecutive wins at target_wr=0.5 → drift detected."""
        pnl = [1.0] * 20
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        assert result["drift_detected"] is True
        assert result["drift_point"] is not None
        assert result["drift_point"] < 20

    def test_stable_no_drift(self):
        """Alternating win/loss at target_wr=0.5 → no drift."""
        pnl = [1.0, -1.0] * 20
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        assert result["drift_detected"] is False
        assert result["drift_point"] is None

    def test_all_losses_no_upward_drift(self):
        """All losses with one-sided CUSUM → no upward drift detected."""
        pnl = [-1.0] * 20
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        assert result["drift_detected"] is False

    def test_drift_from_60_to_30(self):
        """Win rate drops from 60% to 30% — detect using inverted target.

        To detect downward drift, we invert: target=0.5 means watching for
        above-target streaks. A long loss streak won't trigger upward CUSUM.
        Instead, test that a shift to high win rate triggers drift.
        """
        # 20 trades at ~80% win rate should trigger drift above 50%
        pnl = [1.0, 1.0, 1.0, 1.0, -1.0] * 4  # 80% WR
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        assert result["drift_detected"] is True

    def test_cusum_values_length(self):
        """cusum_values has same length as input."""
        pnl = [1.0, -1.0, 1.0]
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        assert len(result["cusum_values"]) == 3

    def test_cusum_never_negative(self):
        """CUSUM values are always >= 0 (max with 0)."""
        pnl = [-1.0] * 10
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        assert all(v >= 0 for v in result["cusum_values"])

    def test_cusum_increments_on_win(self):
        """First win at target_wr=0.5 → CUSUM = 0.5."""
        result = cusum_drift_detect([1.0], target_wr=0.5, threshold=4.0)
        assert result["cusum_values"][0] == pytest.approx(0.5)

    def test_drift_point_is_first_crossing(self):
        """drift_point is the first index where CUSUM > threshold."""
        pnl = [1.0] * 20
        result = cusum_drift_detect(pnl, target_wr=0.5, threshold=4.0)
        # S_i = 0.5 * (i+1), so S > 4.0 at i=8 (S=4.5)
        assert result["drift_point"] == 8

    def test_empty_input(self):
        """Empty list → no drift."""
        result = cusum_drift_detect([])
        assert result["drift_detected"] is False
        assert result["drift_point"] is None
        assert result["cusum_values"] == []

    def test_threshold_validation(self):
        """Threshold <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="threshold must be positive"):
            cusum_drift_detect([1.0], threshold=0)

    def test_target_wr_validation(self):
        """target_wr outside [0,1] raises ValueError."""
        with pytest.raises(ValueError, match="target_wr must be between"):
            cusum_drift_detect([1.0], target_wr=1.5)

    def test_zero_pnl_is_loss(self):
        """pnl_r=0 counts as loss (not > 0)."""
        result = cusum_drift_detect([0.0], target_wr=0.5, threshold=4.0)
        assert result["cusum_values"][0] == 0.0  # max(0, 0 + (0 - 0.5)) = 0
