"""Tests for evolution MCP tool functions.

Uses MockLLMClient and synthetic OHLCV data — no real API calls.
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from tradememory.data.models import OHLCV, OHLCVSeries, Timeframe
from tradememory.evolution.llm import MockLLMClient
from tradememory.evolution.mcp_tools import (
    fetch_market_data,
    discover_patterns,
    run_backtest,
    _resolve_timeframe,
    _pattern_from_dict,
)


# --- Helpers ---


def make_bar(idx: int, base_price: float = 100.0) -> OHLCV:
    drift = idx * 0.05
    noise = (idx % 7 - 3) * 0.3
    price = base_price + drift + noise
    return OHLCV(
        timestamp=datetime(2025, 1, 1, idx % 24, tzinfo=timezone.utc),
        open=price,
        high=price + 1.5,
        low=price - 1.5,
        close=price + 0.2,
        volume=1000.0 + idx * 10,
    )


def make_series(n_bars: int = 200) -> OHLCVSeries:
    return OHLCVSeries(
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        bars=[make_bar(i) for i in range(n_bars)],
        source="test",
    )


def make_pattern_dict(name: str = "TestPattern", hour: int = 10) -> dict:
    return {
        "name": name,
        "description": f"Buy at hour {hour}",
        "entry_condition": {
            "direction": "long",
            "conditions": [
                {"field": "hour_utc", "op": "eq", "value": hour}
            ],
        },
        "exit_condition": {
            "stop_loss_atr": 1.5,
            "take_profit_atr": 3.0,
            "max_holding_bars": 24,
        },
        "confidence": 0.7,
    }


VALID_LLM_RESPONSE = json.dumps({
    "patterns": [
        {
            "name": "LLM Pattern",
            "description": "Discovered pattern",
            "entry_condition": {
                "direction": "long",
                "conditions": [
                    {"field": "hour_utc", "op": "eq", "value": 10}
                ],
            },
            "exit_condition": {
                "stop_loss_atr": 1.5,
                "take_profit_atr": 3.0,
                "max_holding_bars": 24,
            },
            "confidence": 0.7,
        }
    ]
})


# --- _resolve_timeframe ---


class TestResolveTimeframe:
    def test_valid_timeframes(self):
        assert _resolve_timeframe("1h") == Timeframe.H1
        assert _resolve_timeframe("1d") == Timeframe.D1
        assert _resolve_timeframe("5m") == Timeframe.M5

    def test_invalid_timeframe(self):
        with pytest.raises(ValueError, match="Invalid timeframe"):
            _resolve_timeframe("2h")


# --- _pattern_from_dict ---


class TestPatternFromDict:
    def test_valid_dict(self):
        p = _pattern_from_dict(make_pattern_dict())
        assert p.name == "TestPattern"
        assert p.entry_condition.direction == "long"
        assert p.exit_condition.stop_loss_atr == 1.5

    def test_invalid_dict(self):
        with pytest.raises(Exception):
            _pattern_from_dict({"invalid": "data"})


# --- fetch_market_data ---


class TestFetchMarketData:
    @pytest.mark.asyncio
    async def test_with_injected_source(self):
        series = make_series(100)
        source = AsyncMock()
        source.fetch_ohlcv = AsyncMock(return_value=series)
        source.close = AsyncMock()

        result = await fetch_market_data(
            "BTCUSDT", "1h", 30, data_source=source,
        )

        assert result["bars_count"] == 100
        assert result["symbol"] == "BTCUSDT"
        assert result["timeframe"] == "1h"
        assert result["series"] is series
        assert result["start_date"] is not None
        assert result["end_date"] is not None
        # injected source — close NOT called by function
        source.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_timeframe(self):
        result = await fetch_market_data("BTCUSDT", "invalid", 30)
        assert "error" in result
        assert result["bars_count"] == 0

    @pytest.mark.asyncio
    async def test_source_error(self):
        source = AsyncMock()
        source.fetch_ohlcv = AsyncMock(side_effect=RuntimeError("API down"))
        source.close = AsyncMock()

        result = await fetch_market_data(
            "BTCUSDT", "1h", 30, data_source=source,
        )

        assert "error" in result
        assert "API down" in result["error"]
        assert result["bars_count"] == 0


# --- discover_patterns ---


class TestDiscoverPatterns:
    @pytest.mark.asyncio
    async def test_with_series(self):
        llm = MockLLMClient(responses=[VALID_LLM_RESPONSE])
        series = make_series(200)

        result = await discover_patterns(
            "BTCUSDT", "1h", count=1, temperature=0.7,
            llm=llm, series=series,
        )

        assert result["count"] >= 1
        assert len(result["patterns"]) >= 1
        assert result["patterns"][0]["name"] == "LLM Pattern"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_tokens_tracked(self):
        llm = MockLLMClient(responses=[VALID_LLM_RESPONSE])
        series = make_series(200)

        result = await discover_patterns(
            "BTCUSDT", "1h", count=1, temperature=0.5,
            llm=llm, series=series,
        )

        assert "tokens_used" in result
        assert isinstance(result["tokens_used"], int)

    @pytest.mark.asyncio
    async def test_fetch_error_propagated(self):
        llm = MockLLMClient(responses=[VALID_LLM_RESPONSE])
        source = AsyncMock()
        source.fetch_ohlcv = AsyncMock(side_effect=RuntimeError("Binance down"))
        source.close = AsyncMock()

        result = await discover_patterns(
            "BTCUSDT", "1h", count=1, temperature=0.7,
            llm=llm, data_source=source,
        )

        assert "error" in result
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_llm_error_handled(self):
        llm = MockLLMClient()
        llm.should_error = True
        series = make_series(200)

        result = await discover_patterns(
            "BTCUSDT", "1h", count=1, temperature=0.7,
            llm=llm, series=series,
        )

        # Generator handles LLM errors internally — returns empty or error
        assert result["count"] == 0 or "error" in result


# --- run_backtest ---


class TestRunBacktest:
    @pytest.mark.asyncio
    async def test_basic_backtest(self):
        series = make_series(200)
        pattern = make_pattern_dict()

        result = await run_backtest(
            pattern, "BTCUSDT", "1h", series=series,
        )

        assert "error" not in result
        assert "sharpe_ratio" in result
        assert "win_rate" in result
        assert "trade_count" in result
        assert "total_pnl" in result
        assert "max_drawdown_pct" in result
        assert "pattern_name" in result
        assert result["pattern_name"] == "TestPattern"

    @pytest.mark.asyncio
    async def test_invalid_pattern(self):
        result = await run_backtest(
            {"not": "a pattern"}, "BTCUSDT", "1h", series=make_series(50),
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_different_timeframes(self):
        series = make_series(200)
        pattern = make_pattern_dict()

        for tf in ["1h", "4h", "1d"]:
            result = await run_backtest(
                pattern, "BTCUSDT", tf, series=series,
            )
            assert "error" not in result
            assert "sharpe_ratio" in result

    @pytest.mark.asyncio
    async def test_fetch_error(self):
        source = AsyncMock()
        source.fetch_ohlcv = AsyncMock(side_effect=RuntimeError("offline"))
        source.close = AsyncMock()

        result = await run_backtest(
            make_pattern_dict(), "BTCUSDT", "1h",
            data_source=source,
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_pattern_id_preserved(self):
        series = make_series(200)
        pattern = make_pattern_dict()
        pattern["pattern_id"] = "PAT-CUSTOM"

        result = await run_backtest(pattern, "BTCUSDT", "1h", series=series)

        assert result.get("pattern_id") == "PAT-CUSTOM"
