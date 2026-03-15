"""Evolution MCP tool functions — pure async, not yet registered on MCP server.

Three tools:
1. fetch_market_data — fetch OHLCV via BinanceDataSource
2. discover_patterns — LLM pattern discovery from market data
3. run_backtest — backtest a pattern dict against OHLCV data
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from tradememory.data.binance import BinanceDataSource
from tradememory.data.models import OHLCVSeries, Timeframe
from tradememory.evolution.backtester import backtest
from tradememory.evolution.generator import GenerationConfig, HypothesisGenerator
from tradememory.evolution.llm import LLMClient
from tradememory.evolution.models import CandidatePattern, EntryCondition, ExitCondition

logger = logging.getLogger(__name__)

# Timeframe string → Timeframe enum mapping
_TIMEFRAME_MAP = {tf.value: tf for tf in Timeframe}


def _resolve_timeframe(tf_str: str) -> Timeframe:
    """Resolve timeframe string to enum, raise ValueError if invalid."""
    tf = _TIMEFRAME_MAP.get(tf_str)
    if tf is None:
        valid = ", ".join(_TIMEFRAME_MAP.keys())
        raise ValueError(f"Invalid timeframe '{tf_str}'. Valid: {valid}")
    return tf


async def fetch_market_data(
    symbol: str,
    timeframe: str = "1h",
    days: int = 90,
    *,
    data_source: Optional[BinanceDataSource] = None,
) -> dict[str, Any]:
    """Fetch OHLCV market data via BinanceDataSource.

    Args:
        symbol: Trading pair (e.g. "BTCUSDT")
        timeframe: Bar timeframe (e.g. "1h", "4h", "1d")
        days: Number of days of history to fetch
        data_source: Optional injected data source (for testing)

    Returns:
        dict with bars_count, start_date, end_date, symbol, timeframe, series
    """
    try:
        tf = _resolve_timeframe(timeframe)
    except ValueError as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_count": 0,
            "start_date": None,
            "end_date": None,
            "series": None,
        }

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    own_source = data_source is None
    if own_source:
        data_source = BinanceDataSource()

    try:
        series = await data_source.fetch_ohlcv(
            symbol=symbol,
            timeframe=tf,
            start=start,
            end=end,
        )
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_count": series.count,
            "start_date": series.start.isoformat() if series.start else None,
            "end_date": series.end.isoformat() if series.end else None,
            "series": series,
        }
    except Exception as e:
        logger.error("fetch_market_data failed: %s", e)
        return {
            "error": str(e),
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_count": 0,
            "start_date": None,
            "end_date": None,
            "series": None,
        }
    finally:
        if own_source:
            await data_source.close()


async def discover_patterns(
    symbol: str,
    timeframe: str = "1h",
    count: int = 5,
    temperature: float = 0.7,
    *,
    llm: LLMClient,
    series: Optional[OHLCVSeries] = None,
    data_source: Optional[BinanceDataSource] = None,
    days: int = 90,
) -> dict[str, Any]:
    """Discover trading patterns from market data using LLM.

    Args:
        symbol: Trading pair
        timeframe: Bar timeframe
        count: Number of patterns to generate
        temperature: LLM sampling temperature
        llm: LLM client (required)
        series: Pre-fetched OHLCVSeries (skips fetch if provided)
        data_source: Optional injected data source
        days: Days of history if fetching

    Returns:
        dict with patterns list, tokens_used, count, errors
    """
    # Get data
    if series is None:
        result = await fetch_market_data(
            symbol, timeframe, days, data_source=data_source,
        )
        if result.get("error"):
            return {
                "error": result["error"],
                "patterns": [],
                "tokens_used": 0,
                "count": 0,
            }
        series = result["series"]

    config = GenerationConfig(
        patterns_per_batch=count,
        discovery_temperature=temperature,
    )
    generator = HypothesisGenerator(llm=llm, config=config)

    try:
        gen_result = await generator.generate(series=series, temperature=temperature, count=count)
        patterns = []
        for hyp in gen_result.hypotheses:
            patterns.append(hyp.pattern.model_dump(mode="json"))

        return {
            "patterns": patterns,
            "tokens_used": gen_result.total_tokens,
            "count": len(patterns),
            "errors": gen_result.errors,
        }
    except Exception as e:
        logger.error("discover_patterns failed: %s", e)
        return {
            "error": str(e),
            "patterns": [],
            "tokens_used": 0,
            "count": 0,
        }


def _pattern_from_dict(pattern_dict: dict) -> CandidatePattern:
    """Build CandidatePattern from a dict (handles nested models)."""
    return CandidatePattern.model_validate(pattern_dict)


async def run_backtest(
    pattern_dict: dict[str, Any],
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    days: int = 90,
    *,
    series: Optional[OHLCVSeries] = None,
    data_source: Optional[BinanceDataSource] = None,
) -> dict[str, Any]:
    """Backtest a pattern against OHLCV data.

    Args:
        pattern_dict: CandidatePattern as dict
        symbol: Trading pair
        timeframe: Bar timeframe
        days: Days of history if fetching
        series: Pre-fetched OHLCVSeries (skips fetch if provided)
        data_source: Optional injected data source

    Returns:
        dict with fitness metrics (sharpe_ratio, win_rate, etc.)
    """
    tf_str = timeframe

    # Parse pattern
    try:
        pattern = _pattern_from_dict(pattern_dict)
    except Exception as e:
        logger.error("Invalid pattern_dict: %s", e)
        return {"error": f"Invalid pattern: {e}"}

    # Get data
    if series is None:
        result = await fetch_market_data(
            symbol, tf_str, days, data_source=data_source,
        )
        if result.get("error"):
            return {"error": result["error"]}
        series = result["series"]

    # Run backtest
    try:
        fitness = backtest(series=series, pattern=pattern, timeframe=tf_str)
        return {
            "pattern_id": pattern.pattern_id,
            "pattern_name": pattern.name,
            **fitness.model_dump(),
        }
    except Exception as e:
        logger.error("run_backtest failed: %s", e)
        return {"error": f"Backtest failed: {e}"}
