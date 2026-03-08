"""Tests for replay prompt builder."""

from datetime import datetime

from src.tradememory.replay.models import Bar, IndicatorSnapshot, Position, PositionState
from src.tradememory.replay.prompt import (
    build_system_prompt,
    build_user_prompt,
    format_bars_table,
)


def _make_bar(hour: int = 10, minute: int = 0, price: float = 5100.0) -> Bar:
    return Bar(
        timestamp=datetime(2026, 3, 8, hour, minute),
        open=price,
        high=price + 5,
        low=price - 5,
        close=price + 2,
        tick_volume=1000,
    )


def _make_indicators() -> IndicatorSnapshot:
    return IndicatorSnapshot(
        atr_d1=150.0,
        atr_h1=35.0,
        atr_m15=8.0,
        rsi_14=55.0,
    )


class TestSystemPrompt:
    def test_contains_strategy_names(self):
        prompt = build_system_prompt()
        assert "VolBreakout" in prompt
        assert "IntradayMomentum" in prompt
        assert "PullbackEntry" in prompt
        assert "BUY" in prompt
        assert "0.25%" in prompt


class TestUserPrompt:
    def test_contains_price(self):
        bar = _make_bar(price=5175.50)
        prompt = build_user_prompt(
            current_bar=bar,
            window_bars=[bar],
            indicators=_make_indicators(),
        )
        assert "5175.50" in prompt
        assert "ATR(14,D1): 150.00" in prompt

    def test_with_position(self):
        bar = _make_bar()
        pos = Position(
            trade_id="test-001",
            direction="long",
            strategy="VolBreakout",
            entry_price=5080.0,
            entry_time=datetime(2026, 3, 8, 7, 15),
            stop_loss=5050.0,
            take_profit=5200.0,
            confidence=0.8,
            reasoning="Breakout confirmed",
            state=PositionState.OPEN,
        )
        prompt = build_user_prompt(
            current_bar=bar,
            window_bars=[bar],
            indicators=_make_indicators(),
            open_position=pos,
        )
        assert "VolBreakout" in prompt
        assert "5080.00" in prompt
        assert "Open Position" in prompt

    def test_with_trades(self):
        bar = _make_bar()
        trades = [
            {"strategy": "IM", "result": "TP", "pnl": 125.50},
            {"strategy": "VB", "result": "SL", "pnl": -45.00},
        ]
        prompt = build_user_prompt(
            current_bar=bar,
            window_bars=[bar],
            indicators=_make_indicators(),
            recent_trades=trades,
        )
        assert "Recent Trades" in prompt
        assert "+125.50" in prompt
        assert "-45.00" in prompt


class TestBarsTable:
    def test_truncation(self):
        bars = [_make_bar(hour=i % 24, price=5000 + i) for i in range(50)]
        table = format_bars_table(bars, max_rows=20)
        assert "Last 20 of 50 bars" in table
        lines = table.strip().split("\n")
        # header line + column header + 20 data rows
        assert len(lines) == 22
