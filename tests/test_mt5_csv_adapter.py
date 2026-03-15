"""Tests for MT5 CSV data adapter (Task 9.4).

Uses temporary CSV files — no real MT5 data needed.
"""

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from tradememory.data.models import OHLCV, OHLCVSeries, Timeframe
from tradememory.data.mt5_csv import (
    MT5CSVDataSource,
    _infer_symbol,
    _infer_timeframe,
)
from tradememory.data.protocol import (
    DataSource,
    DataSourceError,
    SymbolNotFoundError,
)


# --- Fixtures ---

SAMPLE_CSV_TAB = """Date\tTime\tOpen\tHigh\tLow\tClose\tTickvol\tVolume\tSpread
2024.01.01\t00:00\t2050.50\t2055.80\t2048.20\t2053.40\t1500\t0\t25
2024.01.01\t01:00\t2053.40\t2058.10\t2051.30\t2056.90\t1800\t0\t22
2024.01.01\t02:00\t2056.90\t2060.50\t2054.60\t2059.20\t1200\t0\t28
2024.01.01\t03:00\t2059.20\t2062.00\t2057.10\t2060.80\t900\t0\t30
2024.01.01\t04:00\t2060.80\t2063.50\t2058.90\t2061.70\t1100\t0\t24
"""

SAMPLE_CSV_COMMA = """Date,Time,Open,High,Low,Close,Tickvol,Volume,Spread
2024.01.01,00:00,2050.50,2055.80,2048.20,2053.40,1500,0,25
2024.01.01,01:00,2053.40,2058.10,2051.30,2056.90,1800,0,22
2024.01.01,02:00,2056.90,2060.50,2054.60,2059.20,1200,0,28
"""


@pytest.fixture
def tab_csv(tmp_path):
    """Create a tab-delimited MT5 CSV file."""
    path = tmp_path / "XAUUSD_H1.csv"
    path.write_text(SAMPLE_CSV_TAB, encoding="utf-8")
    return path


@pytest.fixture
def comma_csv(tmp_path):
    """Create a comma-delimited MT5 CSV file."""
    path = tmp_path / "BTCUSD_M5.csv"
    path.write_text(SAMPLE_CSV_COMMA, encoding="utf-8")
    return path


@pytest.fixture
def csv_dir(tmp_path):
    """Create a directory with multiple CSV files."""
    (tmp_path / "XAUUSD_H1.csv").write_text(SAMPLE_CSV_TAB, encoding="utf-8")
    (tmp_path / "BTCUSD_M5.csv").write_text(SAMPLE_CSV_COMMA, encoding="utf-8")
    return tmp_path


@pytest.fixture
def source(tab_csv):
    """MT5CSVDataSource with one registered file."""
    src = MT5CSVDataSource()
    src.register("XAUUSD", Timeframe.H1, tab_csv)
    return src


# --- Protocol conformance ---


class TestProtocolConformance:
    def test_isinstance_check(self, source):
        assert isinstance(source, DataSource)

    def test_name_property(self, source):
        assert source.name == "mt5_csv"


# --- Filename inference ---


class TestFilenameInference:
    @pytest.mark.parametrize("filename,expected", [
        ("XAUUSD_H1.csv", "XAUUSD"),
        ("BTCUSD_M5_2024.csv", "BTCUSD"),
        ("eurusd.csv", "EURUSD"),
        ("GOLD_D1_export.csv", "GOLD"),
    ])
    def test_infer_symbol(self, filename, expected):
        assert _infer_symbol(filename) == expected

    @pytest.mark.parametrize("filename,expected", [
        ("XAUUSD_H1.csv", Timeframe.H1),
        ("BTCUSD_M5.csv", Timeframe.M5),
        ("EURUSD_D1_2024.csv", Timeframe.D1),
        ("GOLD_H4.csv", Timeframe.H4),
        ("unknown.csv", Timeframe.H1),  # default
    ])
    def test_infer_timeframe(self, filename, expected):
        assert _infer_timeframe(filename) == expected


# --- Registration ---


class TestRegistration:
    def test_register(self, tab_csv):
        source = MT5CSVDataSource()
        source.register("XAUUSD", Timeframe.H1, tab_csv)
        assert "XAUUSD_1h" in source._files

    def test_register_overwrites(self, tab_csv, comma_csv):
        source = MT5CSVDataSource()
        source.register("TEST", Timeframe.H1, tab_csv)
        source.register("TEST", Timeframe.H1, comma_csv)
        assert source._files["TEST_1h"] == comma_csv


# --- from_directory ---


class TestFromDirectory:
    def test_auto_discover(self, csv_dir):
        source = MT5CSVDataSource.from_directory(csv_dir)
        assert "XAUUSD_1h" in source._files
        assert "BTCUSD_5m" in source._files

    def test_nonexistent_dir(self):
        with pytest.raises(DataSourceError):
            MT5CSVDataSource.from_directory("/nonexistent/path")


# --- fetch_ohlcv ---


class TestFetchOHLCV:
    @pytest.mark.asyncio
    async def test_basic_fetch(self, source):
        result = await source.fetch_ohlcv(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert isinstance(result, OHLCVSeries)
        assert result.symbol == "XAUUSD"
        assert result.timeframe == Timeframe.H1
        assert result.source == "mt5_csv"
        assert result.count == 5

    @pytest.mark.asyncio
    async def test_utc_enforcement(self, source):
        """All timestamps should have UTC timezone."""
        result = await source.fetch_ohlcv(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        for bar in result.bars:
            assert bar.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_date_range_filter(self, source):
        """Only bars within [start, end] returned."""
        result = await source.fetch_ohlcv(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc),
            end=datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc),
        )
        assert result.count == 3  # 01:00, 02:00, 03:00

    @pytest.mark.asyncio
    async def test_limit(self, source):
        result = await source.fetch_ohlcv(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            limit=2,
        )
        assert result.count == 2

    @pytest.mark.asyncio
    async def test_ohlcv_values(self, source):
        """Verify parsed OHLCV values match CSV."""
        result = await source.fetch_ohlcv(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        first_bar = result.bars[0]
        assert first_bar.open == 2050.50
        assert first_bar.high == 2055.80
        assert first_bar.low == 2048.20
        assert first_bar.close == 2053.40
        assert first_bar.volume == 1500.0  # tick_volume as volume

    @pytest.mark.asyncio
    async def test_cache_hit(self, source):
        """Second fetch uses cached data."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)

        result1 = await source.fetch_ohlcv("XAUUSD", Timeframe.H1, start, end)
        result2 = await source.fetch_ohlcv("XAUUSD", Timeframe.H1, start, end)
        assert result1.count == result2.count

    @pytest.mark.asyncio
    async def test_naive_datetime_converted(self, source):
        """Naive datetimes (no tz) should be treated as UTC."""
        result = await source.fetch_ohlcv(
            symbol="XAUUSD",
            timeframe=Timeframe.H1,
            start=datetime(2024, 1, 1),  # naive
            end=datetime(2024, 1, 2),  # naive
        )
        assert result.count == 5


# --- Error handling ---


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_symbol_not_found(self):
        source = MT5CSVDataSource()
        with pytest.raises(SymbolNotFoundError):
            await source.fetch_ohlcv(
                symbol="FAKEPAIR",
                timeframe=Timeframe.H1,
                start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            )

    @pytest.mark.asyncio
    async def test_file_not_found(self, tmp_path):
        source = MT5CSVDataSource()
        source.register("TEST", Timeframe.H1, tmp_path / "nonexistent.csv")
        with pytest.raises(DataSourceError):
            await source.fetch_ohlcv(
                symbol="TEST",
                timeframe=Timeframe.H1,
                start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end=datetime(2024, 1, 2, tzinfo=timezone.utc),
            )


# --- Comma delimiter ---


class TestCommaDelimiter:
    @pytest.mark.asyncio
    async def test_comma_csv(self, comma_csv):
        source = MT5CSVDataSource()
        source.register("BTCUSD", Timeframe.M5, comma_csv)
        result = await source.fetch_ohlcv(
            symbol="BTCUSD",
            timeframe=Timeframe.M5,
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert result.count == 3
        assert result.bars[0].open == 2050.50


# --- available_symbols ---


class TestAvailableSymbols:
    @pytest.mark.asyncio
    async def test_available_symbols(self, csv_dir):
        source = MT5CSVDataSource.from_directory(csv_dir)
        symbols = await source.available_symbols()
        assert "BTCUSD" in symbols
        assert "XAUUSD" in symbols

    @pytest.mark.asyncio
    async def test_empty_source(self):
        source = MT5CSVDataSource()
        symbols = await source.available_symbols()
        assert symbols == []
