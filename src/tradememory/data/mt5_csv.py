"""MT5 CSV data adapter — wraps replay/data_loader.py into DataSource Protocol.

Reads local MT5-exported CSV files and converts to OHLCVSeries.
Supports both tab and comma delimiters (auto-detected).
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from tradememory.data.models import OHLCV, OHLCVSeries, Timeframe
from tradememory.data.protocol import DataSourceError, SymbolNotFoundError
from tradememory.replay.data_loader import parse_mt5_csv

logger = logging.getLogger(__name__)

# Infer timeframe from filename conventions
# e.g. "XAUUSD_H1.csv", "BTCUSD_M5_2024.csv"
_TIMEFRAME_HINTS = {
    "M1": Timeframe.M1,
    "M5": Timeframe.M5,
    "M15": Timeframe.M15,
    "M30": Timeframe.M30,
    "H1": Timeframe.H1,
    "H4": Timeframe.H4,
    "D1": Timeframe.D1,
    "W1": Timeframe.W1,
    # Alternative formats
    "1m": Timeframe.M1,
    "5m": Timeframe.M5,
    "15m": Timeframe.M15,
    "30m": Timeframe.M30,
    "1h": Timeframe.H1,
    "4h": Timeframe.H4,
    "1d": Timeframe.D1,
    "1w": Timeframe.W1,
}


def _infer_timeframe(filename: str) -> Timeframe:
    """Infer timeframe from filename. Default to H1 if unknown."""
    stem = Path(filename).stem.upper()
    for hint, tf in _TIMEFRAME_HINTS.items():
        if hint.upper() in stem:
            return tf
    return Timeframe.H1


def _infer_symbol(filename: str) -> str:
    """Infer symbol from filename. e.g. 'XAUUSD_H1.csv' → 'XAUUSD'."""
    stem = Path(filename).stem
    # Take first part before underscore
    parts = stem.split("_")
    return parts[0].upper() if parts else stem.upper()


class MT5CSVDataSource:
    """MT5 CSV file data source — implements DataSource Protocol.

    Usage:
        source = MT5CSVDataSource()
        source.register("XAUUSD", Timeframe.H1, "path/to/XAUUSD_H1.csv")
        series = await source.fetch_ohlcv("XAUUSD", Timeframe.H1, start, end)

    Or auto-discover from directory:
        source = MT5CSVDataSource.from_directory("path/to/csv_files/")
    """

    def __init__(self):
        self._files: Dict[str, Path] = {}  # "SYMBOL_TIMEFRAME" -> path
        self._cache: Dict[str, OHLCVSeries] = {}  # parsed cache

    @property
    def name(self) -> str:
        return "mt5_csv"

    def register(self, symbol: str, timeframe: Timeframe, path: str | Path) -> None:
        """Register a CSV file for a symbol/timeframe pair."""
        key = f"{symbol.upper()}_{timeframe.value}"
        self._files[key] = Path(path)
        # Invalidate cache
        self._cache.pop(key, None)

    @classmethod
    def from_directory(cls, directory: str | Path) -> "MT5CSVDataSource":
        """Auto-discover CSV files in a directory.

        Infers symbol and timeframe from filenames.
        e.g. "XAUUSD_H1.csv" → symbol=XAUUSD, timeframe=H1
        """
        source = cls()
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise DataSourceError("mt5_csv", f"Directory not found: {directory}")

        for csv_file in sorted(dir_path.glob("*.csv")):
            symbol = _infer_symbol(csv_file.name)
            timeframe = _infer_timeframe(csv_file.name)
            source.register(symbol, timeframe, csv_file)
            logger.info(f"Registered {symbol} {timeframe.value} from {csv_file.name}")

        return source

    def _load_csv(self, key: str) -> OHLCVSeries:
        """Load and parse CSV file, with caching."""
        if key in self._cache:
            return self._cache[key]

        path = self._files.get(key)
        if path is None:
            raise KeyError(f"No file registered for {key}")

        if not path.exists():
            raise DataSourceError("mt5_csv", f"File not found: {path}")

        try:
            bars = parse_mt5_csv(str(path))
        except Exception as e:
            raise DataSourceError("mt5_csv", f"Failed to parse {path}: {e}") from e

        # Convert replay Bar → data OHLCV
        parts = key.split("_", 1)
        symbol = parts[0]
        tf = Timeframe(parts[1]) if len(parts) > 1 else Timeframe.H1

        ohlcv_bars = [
            OHLCV(
                timestamp=b.timestamp.replace(tzinfo=timezone.utc)
                if b.timestamp.tzinfo is None
                else b.timestamp,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=float(getattr(b, "tick_volume", 0)),
            )
            for b in bars
        ]

        series = OHLCVSeries(
            symbol=symbol,
            timeframe=tf,
            bars=ohlcv_bars,
            source="mt5_csv",
        )

        self._cache[key] = series
        logger.info(f"Loaded {len(ohlcv_bars)} bars from {path.name}")
        return series

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: Optional[int] = None,
    ) -> OHLCVSeries:
        """Fetch OHLCV data from registered CSV file.

        Filters bars to [start, end] range and applies limit.
        """
        key = f"{symbol.upper()}_{timeframe.value}"

        if key not in self._files:
            raise SymbolNotFoundError("mt5_csv", f"{symbol} {timeframe.value}")

        full_series = self._load_csv(key)

        # Ensure start/end are UTC
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Filter to date range
        filtered = full_series.slice(start, end)

        # Apply limit
        if limit and len(filtered.bars) > limit:
            filtered = OHLCVSeries(
                symbol=filtered.symbol,
                timeframe=filtered.timeframe,
                bars=filtered.bars[:limit],
                source=filtered.source,
            )

        return filtered

    async def available_symbols(self) -> list[str]:
        """List registered symbol/timeframe pairs."""
        symbols = set()
        for key in self._files:
            symbol = key.split("_")[0]
            symbols.add(symbol)
        return sorted(symbols)
