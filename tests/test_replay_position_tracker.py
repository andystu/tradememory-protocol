"""Tests for PositionTracker — position lifecycle manager."""

from datetime import datetime

import pytest

from tradememory.replay.models import (
    AgentDecision,
    Bar,
    DecisionType,
    PositionState,
)
from tradememory.replay.position_tracker import PositionTracker


def _bar(
    o: float = 5000.0,
    h: float = 5010.0,
    l: float = 4990.0,
    c: float = 5005.0,
    ts: str = "2026-03-01 10:00:00",
) -> Bar:
    return Bar(timestamp=datetime.fromisoformat(ts), open=o, high=h, low=l, close=c)


def _decision(
    decision: DecisionType = DecisionType.BUY,
    entry: float = 5000.0,
    sl: float = 4950.0,
    tp: float = 5100.0,
) -> AgentDecision:
    return AgentDecision(
        market_observation="test obs",
        reasoning_trace="test reasoning",
        decision=decision,
        confidence=0.8,
        strategy_used="VolBreakout",
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
    )


class TestOpenPosition:
    def test_open_long(self):
        tracker = PositionTracker()
        pos = tracker.open_position(_decision(), _bar())
        assert pos.direction == "long"
        assert pos.entry_price == 5000.0
        assert pos.state == PositionState.OPEN

    def test_open_short(self):
        tracker = PositionTracker()
        pos = tracker.open_position(
            _decision(DecisionType.SELL, entry=5000.0, sl=5050.0, tp=4900.0), _bar()
        )
        assert pos.direction == "short"
        assert pos.entry_price == 5000.0

    def test_open_when_already_open_raises(self):
        tracker = PositionTracker()
        tracker.open_position(_decision(), _bar())
        with pytest.raises(ValueError, match="already open"):
            tracker.open_position(_decision(), _bar())


class TestSLTPLong:
    def test_sl_hit_long(self):
        tracker = PositionTracker(lot_size=0.10, initial_equity=10000.0)
        tracker.open_position(_decision(sl=4950.0, tp=5100.0), _bar())
        # Bar that breaches SL
        result = tracker.check_bar(_bar(o=4960, h=4970, l=4940, c=4945))
        assert result is not None
        assert result.state == PositionState.CLOSED_SL
        assert result.exit_price == 4950.0
        # PnL: (4950 - 5000) * 0.10 * 100 = -500
        assert result.pnl == pytest.approx(-500.0)
        assert tracker.current_position is None

    def test_tp_hit_long(self):
        tracker = PositionTracker(lot_size=0.10, initial_equity=10000.0)
        tracker.open_position(_decision(sl=4950.0, tp=5100.0), _bar())
        result = tracker.check_bar(_bar(o=5090, h=5110, l=5080, c=5105))
        assert result is not None
        assert result.state == PositionState.CLOSED_TP
        assert result.exit_price == 5100.0
        # PnL: (5100 - 5000) * 0.10 * 100 = +1000
        assert result.pnl == pytest.approx(1000.0)

    def test_no_trigger(self):
        tracker = PositionTracker()
        tracker.open_position(_decision(sl=4950.0, tp=5100.0), _bar())
        result = tracker.check_bar(_bar(o=5000, h=5050, l=4960, c=5020))
        assert result is None
        assert tracker.current_position is not None
        assert tracker.current_position.bars_held == 1


class TestSLTPShort:
    def test_sl_hit_short(self):
        tracker = PositionTracker(lot_size=0.10)
        tracker.open_position(
            _decision(DecisionType.SELL, entry=5000.0, sl=5050.0, tp=4900.0), _bar()
        )
        result = tracker.check_bar(_bar(o=5040, h=5060, l=5030, c=5055))
        assert result is not None
        assert result.state == PositionState.CLOSED_SL
        assert result.exit_price == 5050.0
        # PnL: -(5050 - 5000) * 0.10 * 100 = -500
        assert result.pnl == pytest.approx(-500.0)

    def test_tp_hit_short(self):
        tracker = PositionTracker(lot_size=0.10)
        tracker.open_position(
            _decision(DecisionType.SELL, entry=5000.0, sl=5050.0, tp=4900.0), _bar()
        )
        result = tracker.check_bar(_bar(o=4910, h=4920, l=4890, c=4895))
        assert result is not None
        assert result.state == PositionState.CLOSED_TP
        assert result.exit_price == 4900.0
        # PnL: -(4900 - 5000) * 0.10 * 100 = +1000
        assert result.pnl == pytest.approx(1000.0)


class TestClosePosition:
    def test_close_eod(self):
        tracker = PositionTracker(lot_size=0.10, initial_equity=10000.0)
        tracker.open_position(_decision(sl=4950.0, tp=5100.0), _bar())
        close_bar = _bar(o=5020, h=5030, l=5010, c=5025, ts="2026-03-01 23:45:00")
        result = tracker.close_position(close_bar, PositionState.CLOSED_EOD)
        assert result.state == PositionState.CLOSED_EOD
        assert result.exit_price == 5025.0
        # PnL: (5025 - 5000) * 0.10 * 100 = +250
        assert result.pnl == pytest.approx(250.0)
        assert tracker.equity == pytest.approx(10250.0)

    def test_close_no_position_raises(self):
        tracker = PositionTracker()
        with pytest.raises(ValueError, match="No position"):
            tracker.close_position(_bar(), PositionState.CLOSED_EOD)


class TestPnLCalculation:
    def test_pnl_win_long(self):
        tracker = PositionTracker(lot_size=0.20, initial_equity=10000.0)
        tracker.open_position(
            _decision(entry=5000.0, sl=4950.0, tp=5100.0), _bar()
        )
        result = tracker.check_bar(_bar(o=5090, h=5110, l=5080, c=5105))
        # PnL: (5100 - 5000) * 0.20 * 100 = +2000
        assert result.pnl == pytest.approx(2000.0)
        # pnl_r: 2000 / (50 * 0.20 * 100) = 2000 / 1000 = 2.0
        assert result.pnl_r == pytest.approx(2.0)
        assert tracker.equity == pytest.approx(12000.0)

    def test_pnl_loss_short(self):
        tracker = PositionTracker(lot_size=0.10, initial_equity=10000.0)
        tracker.open_position(
            _decision(DecisionType.SELL, entry=5000.0, sl=5050.0, tp=4900.0), _bar()
        )
        result = tracker.check_bar(_bar(o=5040, h=5060, l=5030, c=5055))
        # PnL: -(5050 - 5000) * 0.10 * 100 = -500
        assert result.pnl == pytest.approx(-500.0)
        # pnl_r: -500 / (50 * 0.10 * 100) = -500/500 = -1.0
        assert result.pnl_r == pytest.approx(-1.0)
        assert tracker.equity == pytest.approx(9500.0)


class TestMAETracking:
    def test_mae_updates_across_bars(self):
        tracker = PositionTracker()
        tracker.open_position(
            _decision(entry=5000.0, sl=4900.0, tp=5200.0), _bar()
        )
        # Bar 1: low dips to 4980 → MAE = 20
        tracker.check_bar(_bar(o=5000, h=5010, l=4980, c=4990))
        assert tracker.current_position.max_adverse_excursion == pytest.approx(20.0)

        # Bar 2: low dips further to 4960 → MAE = 40
        tracker.check_bar(_bar(o=4990, h=5000, l=4960, c=4970))
        assert tracker.current_position.max_adverse_excursion == pytest.approx(40.0)
        assert tracker.current_position.bars_held == 2

        # Bar 3: low only 4975 → MAE stays 40
        tracker.check_bar(_bar(o=4970, h=5050, l=4975, c=5040))
        assert tracker.current_position.max_adverse_excursion == pytest.approx(40.0)


class TestEquityDrawdown:
    def test_drawdown_after_loss(self):
        tracker = PositionTracker(lot_size=0.10, initial_equity=10000.0)
        tracker.open_position(_decision(sl=4950.0, tp=5100.0), _bar())
        tracker.check_bar(_bar(o=4960, h=4970, l=4940, c=4945))
        # Lost 500 → equity 9500, peak 10000, dd = 5%
        assert tracker.equity == pytest.approx(9500.0)
        assert tracker.peak_equity == pytest.approx(10000.0)
        assert tracker.drawdown_pct == pytest.approx(5.0)
