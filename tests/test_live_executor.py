"""Tests for scripts/live_executor.py — check_exit() function."""

import sys
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace, ModuleType
from unittest import mock

import pytest

# Stub heavy dependencies before importing live_executor
_stubs = {}
for mod_name in ("supabase", "httpx", "strategy_definitions"):
    if mod_name not in sys.modules:
        _stubs[mod_name] = sys.modules[mod_name] = ModuleType(mod_name)
        if mod_name == "supabase":
            sys.modules[mod_name].create_client = lambda *a, **k: None
        if mod_name == "strategy_definitions":
            sys.modules[mod_name].build_strategy_e = lambda: None

# Add scripts/ to path so we can import live_executor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from live_executor import check_exit


def _make_pos(
    direction="long",
    entry_price=100.0,
    stop_loss=95.0,
    take_profit=110.0,
    max_exit_hours=24,
):
    """Helper to build a position dict."""
    return {
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "max_exit_time": (
            datetime.now(timezone.utc) + timedelta(hours=max_exit_hours)
        ).isoformat(),
    }


def _make_bar(open_=100.0, high=105.0, low=96.0, close=102.0):
    """Helper to build a bar object with OHLC attributes."""
    return SimpleNamespace(open=open_, high=high, low=low, close=close)


# --- Test 1: SL hit (long) ---
class TestSLHit:
    def test_long_sl_hit(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=94.0, high=101.0)  # low breaches SL
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "sl"
        assert result["exit_price"] == 95.0

    def test_short_sl_hit(self):
        pos = _make_pos(direction="short", entry_price=100.0, stop_loss=105.0, take_profit=90.0)
        bar = _make_bar(high=106.0, low=99.0)  # high breaches SL
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "sl"
        assert result["exit_price"] == 105.0


# --- Test 2: TP hit (long) ---
class TestTPHit:
    def test_long_tp_hit(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=99.0, high=112.0)  # high breaches TP
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "tp"
        assert result["exit_price"] == 110.0

    def test_short_tp_hit(self):
        pos = _make_pos(direction="short", entry_price=100.0, stop_loss=105.0, take_profit=90.0)
        bar = _make_bar(low=89.0, high=101.0)  # low breaches TP
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "tp"
        assert result["exit_price"] == 90.0


# --- Test 3: Timeout (max_exit_time exceeded) ---
class TestTimeout:
    def test_timeout_exit(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        # Set max_exit_time in the past
        pos["max_exit_time"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        bar = _make_bar(low=98.0, high=102.0, close=101.0)  # no SL/TP hit
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "time"
        assert result["exit_price"] == 101.0  # exits at bar.close


# --- Test 4: No exit condition → None ---
class TestNoExit:
    def test_no_exit_returns_none(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=98.0, high=105.0)  # within SL-TP range
        result = check_exit(pos, bar)
        assert result is None


# --- Test 5: Edge case — price exactly equals SL or TP ---
class TestExactBoundary:
    def test_long_price_exactly_at_sl(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=95.0, high=105.0)  # low == SL exactly
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "sl"
        assert result["exit_price"] == 95.0

    def test_long_price_exactly_at_tp(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=99.0, high=110.0)  # high == TP exactly
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "tp"
        assert result["exit_price"] == 110.0

    def test_short_price_exactly_at_sl(self):
        pos = _make_pos(direction="short", entry_price=100.0, stop_loss=105.0, take_profit=90.0)
        bar = _make_bar(high=105.0, low=99.0)  # high == SL exactly
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "sl"
        assert result["exit_price"] == 105.0

    def test_short_price_exactly_at_tp(self):
        pos = _make_pos(direction="short", entry_price=100.0, stop_loss=105.0, take_profit=90.0)
        bar = _make_bar(low=90.0, high=101.0)  # low == TP exactly
        result = check_exit(pos, bar)
        assert result is not None
        assert result["reason"] == "tp"
        assert result["exit_price"] == 90.0


# --- Test 6: SL priority over TP (both hit same bar) ---
class TestSLPriority:
    def test_long_sl_priority_over_tp(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=90.0, high=115.0)  # both SL and TP breached
        result = check_exit(pos, bar)
        assert result["reason"] == "sl"  # SL takes priority

    def test_short_sl_priority_over_tp(self):
        pos = _make_pos(direction="short", entry_price=100.0, stop_loss=105.0, take_profit=90.0)
        bar = _make_bar(low=85.0, high=110.0)  # both SL and TP breached
        result = check_exit(pos, bar)
        assert result["reason"] == "sl"  # SL takes priority


# --- Test 7: PnL calculations ---
class TestPnLCalc:
    def test_long_tp_pnl_positive(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=99.0, high=112.0)
        result = check_exit(pos, bar)
        assert result["pnl_pct"] > 0  # profit
        assert result["pnl_r"] > 0

    def test_long_sl_pnl_negative(self):
        pos = _make_pos(direction="long", entry_price=100.0, stop_loss=95.0, take_profit=110.0)
        bar = _make_bar(low=93.0, high=101.0)
        result = check_exit(pos, bar)
        assert result["pnl_pct"] < 0  # loss
        assert result["pnl_r"] < 0
