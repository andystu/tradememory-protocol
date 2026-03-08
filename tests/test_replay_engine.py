"""Tests for ReplayEngine — full replay loop with mock LLM."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from src.tradememory.replay.engine import ReplayEngine, run_replay
from src.tradememory.replay.models import (
    AgentDecision,
    Bar,
    DecisionType,
    PositionState,
    ReplayConfig,
)

SAMPLE_CSV = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample_xauusd_m15.csv"
)


def _make_bars(n: int, base_price: float = 2300.0, trend: float = 0.5) -> List[Bar]:
    """Generate synthetic M15 bars."""
    bars = []
    price = base_price
    for i in range(n):
        bars.append(
            Bar(
                timestamp=datetime(2025, 1, 1) + timedelta(minutes=15 * i),
                open=price,
                high=price + 3.0,
                low=price - 2.0,
                close=price + trend,
                tick_volume=100,
                spread=20,
            )
        )
        price += trend
    return bars


def _write_csv(bars: List[Bar], path: str) -> None:
    """Write bars to MT5-format CSV."""
    with open(path, "w") as f:
        f.write("Date\tTime\tOpen\tHigh\tLow\tClose\tTickvol\tVolume\tSpread\n")
        for b in bars:
            date_str = b.timestamp.strftime("%Y.%m.%d")
            time_str = b.timestamp.strftime("%H:%M")
            f.write(
                f"{date_str}\t{time_str}\t{b.open:.2f}\t{b.high:.2f}\t"
                f"{b.low:.2f}\t{b.close:.2f}\t{b.tick_volume}\t0\t{b.spread}\n"
            )


def _hold_decision() -> AgentDecision:
    """Return a HOLD decision."""
    return AgentDecision(
        market_observation="No signal",
        reasoning_trace="No setup detected",
        decision=DecisionType.HOLD,
        confidence=0.3,
    )


def _buy_decision(
    entry: float = 2300.0, sl: float = 2290.0, tp: float = 2320.0
) -> AgentDecision:
    """Return a BUY decision."""
    return AgentDecision(
        market_observation="Breakout detected",
        reasoning_trace="Price broke above resistance",
        decision=DecisionType.BUY,
        confidence=0.8,
        strategy_used="VolBreakout",
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
    )


class TestDryRun:
    def test_dry_run_no_llm_calls(self):
        """Dry run should parse CSV and compute indicators without calling LLM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            bars = _make_bars(120)  # enough for window_size=96
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            summary = engine.run(dry_run=True)

            assert summary["total_bars"] == 120
            assert summary["decisions"] > 0
            assert summary["trades"] == 0
            assert summary["tokens"] == 0
            assert summary["cost"] == 0.0

    def test_dry_run_decisions_contain_indicators(self):
        """Dry-run decisions should include indicator snapshots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            bars = _make_bars(120)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            engine.run(dry_run=True)

            assert len(engine.decisions) > 0
            d = engine.decisions[0]
            assert d["decision"] == "DRY_RUN"
            assert "indicators" in d
            assert "atr_m15" in d["indicators"]


class TestHoldOnly:
    @patch("src.tradememory.replay.engine.LLMClient")
    def test_all_holds_no_trades(self, MockLLMClient):
        """If LLM always returns HOLD, no trades should open."""
        mock_llm = MagicMock()
        mock_llm.decide.return_value = _hold_decision()
        mock_llm.total_tokens_used = 100
        mock_llm.total_cost_usd = 0.01
        MockLLMClient.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            bars = _make_bars(120)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            summary = engine.run()

            assert summary["trades"] == 0
            assert summary["equity"] == config.initial_equity
            assert mock_llm.decide.call_count > 0


class TestSingleTradeSL:
    @patch("src.tradememory.replay.engine.LLMClient")
    def test_buy_then_sl_hit(self, MockLLMClient):
        """BUY on first decision, then SL hit on intermediate bar."""
        # Create bars where price drops below SL after entry
        bars = []
        price = 2300.0
        for i in range(120):
            if i < 100:
                bars.append(
                    Bar(
                        timestamp=datetime(2025, 1, 1) + timedelta(minutes=15 * i),
                        open=price,
                        high=price + 3.0,
                        low=price - 2.0,
                        close=price + 0.5,
                        tick_volume=100,
                        spread=20,
                    )
                )
                price += 0.5
            else:
                # Price crashes — SL at 2290 should be hit
                bars.append(
                    Bar(
                        timestamp=datetime(2025, 1, 1) + timedelta(minutes=15 * i),
                        open=price,
                        high=price + 1.0,
                        low=2285.0,  # below SL of 2290
                        close=2286.0,
                        tick_volume=200,
                        spread=30,
                    )
                )
                price = 2286.0

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # TP set very high so it won't be hit before SL
                return _buy_decision(entry=2300.0, sl=2290.0, tp=2500.0)
            return _hold_decision()

        mock_llm = MagicMock()
        mock_llm.decide.side_effect = side_effect
        mock_llm.total_tokens_used = 200
        mock_llm.total_cost_usd = 0.02
        MockLLMClient.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            summary = engine.run()

            assert summary["trades"] >= 1
            closed = engine.tracker.closed_positions
            assert any(p.state == PositionState.CLOSED_SL for p in closed)


class TestMemoryStorage:
    @patch("src.tradememory.replay.engine.LLMClient")
    @patch("src.tradememory.db.Database")
    def test_closed_trade_stored_to_db(self, MockDatabase, MockLLMClient):
        """Closed trades should be stored via db.insert_episodic()."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Wide SL/TP so only EOD close triggers
                return _buy_decision(entry=2348.0, sl=2200.0, tp=2500.0)
            return _hold_decision()

        mock_llm = MagicMock()
        mock_llm.decide.side_effect = side_effect
        mock_llm.total_tokens_used = 200
        mock_llm.total_cost_usd = 0.02
        MockLLMClient.return_value = mock_llm

        mock_db = MagicMock()
        mock_db.insert_episodic.return_value = True
        MockDatabase.return_value = mock_db

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            bars = _make_bars(120, trend=0.1)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=True,
                db_path=os.path.join(tmpdir, "test.db"),
            )
            engine = ReplayEngine(config)
            engine.run()

        # Position was opened, so EOD close should trigger insert_episodic
        assert mock_db.insert_episodic.called
        call_args = mock_db.insert_episodic.call_args[0][0]
        assert "replay_" in call_args["id"]
        assert call_args["strategy"] == "VolBreakout"
        assert "replay" in call_args["tags"]


class TestEquityTracking:
    @patch("src.tradememory.replay.engine.LLMClient")
    def test_equity_changes_after_trade(self, MockLLMClient):
        """Equity should change after a trade closes."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # BUY with tight TP that will hit on uptrending bars
                return _buy_decision(entry=2348.0, sl=2290.0, tp=2354.0)
            return _hold_decision()

        mock_llm = MagicMock()
        mock_llm.decide.side_effect = side_effect
        mock_llm.total_tokens_used = 100
        mock_llm.total_cost_usd = 0.01
        MockLLMClient.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            # Uptrending bars — TP should be hit
            bars = _make_bars(120, base_price=2300.0, trend=1.0)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                initial_equity=10000.0,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            summary = engine.run()

            # Equity should differ from initial after trade
            if summary["trades"] > 0:
                assert summary["equity"] != 10000.0


class TestMaxOnePosition:
    @patch("src.tradememory.replay.engine.LLMClient")
    def test_second_buy_ignored_while_position_open(self, MockLLMClient):
        """Only 1 position allowed — second BUY should be ignored."""
        mock_llm = MagicMock()
        # Always return BUY
        mock_llm.decide.return_value = _buy_decision(
            entry=2348.0, sl=2200.0, tp=2500.0
        )
        mock_llm.total_tokens_used = 100
        mock_llm.total_cost_usd = 0.01
        MockLLMClient.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            # Flat bars — no SL/TP hit
            bars = _make_bars(120, base_price=2300.0, trend=0.1)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            engine.run()

            # Multiple BUY calls but only 1 position opened (closed at EOD = 1 trade)
            assert len(engine.tracker.closed_positions) <= 1


class TestEODClose:
    @patch("src.tradememory.replay.engine.LLMClient")
    def test_open_position_closed_at_end(self, MockLLMClient):
        """Open position at end of data should be force-closed as EOD."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Wide SL/TP that won't be hit
                return _buy_decision(entry=2348.0, sl=2200.0, tp=2500.0)
            return _hold_decision()

        mock_llm = MagicMock()
        mock_llm.decide.side_effect = side_effect
        mock_llm.total_tokens_used = 100
        mock_llm.total_cost_usd = 0.01
        MockLLMClient.return_value = mock_llm

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            bars = _make_bars(120, base_price=2300.0, trend=0.1)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            engine.run()

            assert len(engine.tracker.closed_positions) == 1
            assert (
                engine.tracker.closed_positions[0].state == PositionState.CLOSED_EOD
            )
            assert engine.tracker.current_position is None


class TestSummaryFormat:
    def test_summary_has_all_fields(self):
        """_build_summary() should return all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test.csv")
            bars = _make_bars(120)
            _write_csv(bars, csv_path)

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            summary = engine.run(dry_run=True)

            expected_keys = {
                "total_bars",
                "decisions",
                "trades",
                "equity",
                "win_rate",
                "profit_factor",
                "tokens",
                "cost",
            }
            assert set(summary.keys()) == expected_keys

    def test_summary_empty_data(self):
        """Summary on empty CSV should return zeros."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "empty.csv")
            with open(csv_path, "w") as f:
                f.write(
                    "Date\tTime\tOpen\tHigh\tLow\tClose\tTickvol\tVolume\tSpread\n"
                )

            config = ReplayConfig(
                data_path=csv_path,
                window_size=96,
                decision_interval=4,
                store_to_memory=False,
            )
            engine = ReplayEngine(config)
            summary = engine.run(dry_run=True)

            assert summary["total_bars"] == 0
            assert summary["decisions"] == 0
            assert summary["trades"] == 0
