"""Tests for MT5 CSV data loader and sliding window iterator."""

import os
import tempfile
from datetime import datetime

import pytest

from src.tradememory.replay.data_loader import parse_mt5_csv, sliding_window
from src.tradememory.replay.models import Bar

SAMPLE_CSV = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample_xauusd_m15.csv"
)


# --- parse_mt5_csv ---


class TestParseMt5Csv:
    def test_parse_sample_csv(self):
        """Parse real sample file — 50 bars, sorted oldest-first."""
        bars = parse_mt5_csv(SAMPLE_CSV)
        assert len(bars) == 50
        assert all(isinstance(b, Bar) for b in bars)
        # Sorted oldest-first
        for i in range(1, len(bars)):
            assert bars[i].timestamp >= bars[i - 1].timestamp

    def test_empty_file(self):
        """Empty file returns empty list."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("")
            f.flush()
            bars = parse_mt5_csv(f.name)
        os.unlink(f.name)
        assert bars == []

    def test_header_only(self):
        """File with only header returns empty list."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write("Date\tTime\tOpen\tHigh\tLow\tClose\tTickvol\tVolume\tSpread\n")
            f.flush()
            bars = parse_mt5_csv(f.name)
        os.unlink(f.name)
        assert bars == []

    def test_date_parsing(self):
        """Verify parsed datetime matches MT5 format."""
        bars = parse_mt5_csv(SAMPLE_CSV)
        first = bars[0]
        assert first.timestamp == datetime(2024, 6, 10, 0, 0)

    def test_tab_separated(self):
        """Explicitly tab-separated data parses correctly."""
        content = (
            "Date\tTime\tOpen\tHigh\tLow\tClose\tTickvol\tVolume\tSpread\n"
            "2024.01.02\t09:30\t2050.00\t2055.00\t2048.00\t2053.00\t500\t0\t10\n"
            "2024.01.02\t09:45\t2053.00\t2056.00\t2051.00\t2054.50\t600\t0\t12\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(content)
            f.flush()
            bars = parse_mt5_csv(f.name)
        os.unlink(f.name)
        assert len(bars) == 2
        assert bars[0].open == 2050.00
        assert bars[1].close == 2054.50
        assert bars[0].spread == 10

    def test_comma_separated(self):
        """Auto-detect comma delimiter."""
        content = (
            "Date,Time,Open,High,Low,Close,Tickvol,Volume,Spread\n"
            "2024.03.15,14:00,2100.00,2105.00,2098.00,2103.50,700,0,15\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            f.write(content)
            f.flush()
            bars = parse_mt5_csv(f.name)
        os.unlink(f.name)
        assert len(bars) == 1
        assert bars[0].close == 2103.50
        assert bars[0].tick_volume == 700


# --- sliding_window ---


class TestSlidingWindow:
    def _make_bars(self, n: int) -> list:
        """Create n dummy bars."""
        return [
            Bar(
                timestamp=datetime(2024, 1, 1, i // 4, (i % 4) * 15),
                open=2000.0 + i,
                high=2001.0 + i,
                low=1999.0 + i,
                close=2000.5 + i,
                tick_volume=100,
            )
            for i in range(n)
        ]

    def test_basic_window(self):
        """Window of 4, step=1 on 10 bars yields 7 windows."""
        bars = self._make_bars(10)
        results = list(sliding_window(bars, window_size=4, step=1))
        assert len(results) == 7
        # First window: idx 3, last window: idx 9
        assert results[0][0] == 3
        assert results[-1][0] == 9
        # Each window has 4 bars
        for idx, window, current in results:
            assert len(window) == 4
            assert current is bars[idx]
            assert window[-1] is current

    def test_step_4(self):
        """step=4 on 50 bars with window=8 yields correct count."""
        bars = self._make_bars(50)
        results = list(sliding_window(bars, window_size=8, step=4))
        # First at idx 7, then 11, 15, ..., 47 → (47-7)/4 + 1 = 11
        assert len(results) == 11
        # Verify step spacing
        indices = [r[0] for r in results]
        for i in range(1, len(indices)):
            assert indices[i] - indices[i - 1] == 4

    def test_insufficient_bars(self):
        """Fewer bars than window_size yields nothing."""
        bars = self._make_bars(3)
        results = list(sliding_window(bars, window_size=5))
        assert results == []
