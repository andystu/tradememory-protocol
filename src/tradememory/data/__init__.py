"""Platform-agnostic market data layer.

Provides a unified DataSource protocol for fetching OHLCV data
from any exchange or broker (Binance, MT5, etc.).
"""

from tradememory.data.models import OHLCV, OHLCVSeries, Timeframe
from tradememory.data.protocol import DataSource

__all__ = ["BinanceDataSource", "DataSource", "OHLCV", "OHLCVSeries", "Timeframe"]


def get_binance_source(**kwargs):
    """Lazy import to avoid httpx dependency at module level."""
    from tradememory.data.binance import BinanceDataSource
    return BinanceDataSource(**kwargs)
