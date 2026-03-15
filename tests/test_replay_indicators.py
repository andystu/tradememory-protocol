"""Tests for replay/indicators.py — pure Python indicator calculations."""

import pytest
from datetime import datetime, timedelta

from tradememory.replay.models import Bar, IndicatorSnapshot
from tradememory.replay.indicators import (
    compute_atr,
    compute_rsi,
    compute_sma,
    compute_bollinger_bands,
    aggregate_to_h1,
    aggregate_to_d1,
    aggregate_to_d1_by_date,
    precompute_d1_atr_series,
    compute_all_indicators,
)


def _make_bars(closes: list[float], spread: float = 5.0) -> list[Bar]:
    """Helper: generate bars from close prices with synthetic OHLC."""
    bars = []
    for i, c in enumerate(closes):
        bars.append(
            Bar(
                timestamp=datetime(2025, 1, 1) + timedelta(minutes=15 * i),
                open=c - 1.0,
                high=c + 2.0,
                low=c - 3.0,
                close=c,
                tick_volume=100,
                spread=int(spread),
            )
        )
    return bars


def _make_flat_bars(price: float, n: int) -> list[Bar]:
    """Bars with identical OHLC (zero volatility)."""
    return [
        Bar(
            timestamp=datetime(2025, 1, 1) + timedelta(minutes=15 * i),
            open=price,
            high=price,
            low=price,
            close=price,
            tick_volume=100,
        )
        for i in range(n)
    ]


# --- ATR tests ---


class TestATR:
    def test_atr_insufficient_data(self):
        bars = _make_bars([100.0] * 10)  # need 15 for period=14
        assert compute_atr(bars, period=14) is None

    def test_atr_exact_minimum_data(self):
        """15 bars = 14 true ranges = exactly enough for period=14 seed."""
        bars = _make_bars([100.0 + i for i in range(15)])
        result = compute_atr(bars, period=14)
        assert result is not None
        assert result > 0

    def test_atr_flat_market(self):
        """Flat OHLC → TR=0 → ATR=0."""
        bars = _make_flat_bars(2000.0, 20)
        result = compute_atr(bars, period=14)
        assert result is not None
        assert result == pytest.approx(0.0)

    def test_atr_known_values(self):
        """Manually verify Wilder's smoothing with constant TR.

        If every bar has H-L=5 and prev_close==close (flat close),
        then TR=5 for every bar, ATR should converge to 5.
        """
        bars = []
        for i in range(30):
            bars.append(
                Bar(
                    timestamp=datetime(2025, 1, 1) + timedelta(minutes=15 * i),
                    open=100.0,
                    high=102.5,
                    low=97.5,  # H-L = 5.0
                    close=100.0,
                    tick_volume=100,
                )
            )
        result = compute_atr(bars, period=14)
        assert result == pytest.approx(5.0, abs=0.01)


# --- RSI tests ---


class TestRSI:
    def test_rsi_insufficient_data(self):
        bars = _make_bars([100.0] * 10)
        assert compute_rsi(bars, period=14) is None

    def test_rsi_overbought(self):
        """Steadily rising closes → RSI near 100."""
        closes = [2000.0 + i * 10 for i in range(30)]
        bars = _make_bars(closes)
        result = compute_rsi(bars, period=14)
        assert result is not None
        assert result > 80

    def test_rsi_oversold(self):
        """Steadily falling closes → RSI near 0."""
        closes = [3000.0 - i * 10 for i in range(30)]
        bars = _make_bars(closes)
        result = compute_rsi(bars, period=14)
        assert result is not None
        assert result < 20

    def test_rsi_neutral(self):
        """Alternating up/down with equal magnitude → RSI near 50."""
        closes = [2000.0 + (5 if i % 2 == 0 else -5) for i in range(40)]
        bars = _make_bars(closes)
        result = compute_rsi(bars, period=14)
        assert result is not None
        assert 40 < result < 60

    def test_rsi_all_gains(self):
        """All gains, zero losses → RSI = 100."""
        closes = [100.0 + i for i in range(20)]
        bars = _make_bars(closes)
        result = compute_rsi(bars, period=14)
        assert result == pytest.approx(100.0)


# --- Bollinger Bands tests ---


class TestBollingerBands:
    def test_bb_insufficient_data(self):
        bars = _make_bars([100.0] * 10)
        upper, middle, lower = compute_bollinger_bands(bars, period=20)
        assert upper is None and middle is None and lower is None

    def test_bb_flat_market(self):
        """Zero stdev → upper == middle == lower."""
        bars = _make_flat_bars(2000.0, 25)
        upper, middle, lower = compute_bollinger_bands(bars, period=20)
        assert upper == pytest.approx(2000.0)
        assert middle == pytest.approx(2000.0)
        assert lower == pytest.approx(2000.0)

    def test_bb_width_increases_with_volatility(self):
        """More volatile data → wider bands."""
        calm = _make_bars([2000.0 + (i % 2) for i in range(25)])
        wild = _make_bars([2000.0 + (i % 2) * 50 for i in range(25)])

        u_calm, m_calm, l_calm = compute_bollinger_bands(calm)
        u_wild, m_wild, l_wild = compute_bollinger_bands(wild)

        width_calm = u_calm - l_calm
        width_wild = u_wild - l_wild
        assert width_wild > width_calm


# --- SMA tests ---


class TestSMA:
    def test_sma_insufficient_data(self):
        bars = _make_bars([100.0] * 3)
        assert compute_sma(bars, period=5) is None

    def test_sma_correct_value(self):
        bars = _make_bars([10.0, 20.0, 30.0, 40.0, 50.0])
        result = compute_sma(bars, period=5)
        assert result == pytest.approx(30.0)


# --- Aggregation tests ---


class TestAggregation:
    def test_aggregate_h1(self):
        """4 M15 bars → 1 H1 bar."""
        bars = [
            Bar(
                timestamp=datetime(2025, 1, 1, 0, 0),
                open=100.0, high=110.0, low=95.0, close=105.0,
            ),
            Bar(
                timestamp=datetime(2025, 1, 1, 0, 15),
                open=105.0, high=115.0, low=100.0, close=108.0,
            ),
            Bar(
                timestamp=datetime(2025, 1, 1, 0, 30),
                open=108.0, high=112.0, low=98.0, close=101.0,
            ),
            Bar(
                timestamp=datetime(2025, 1, 1, 0, 45),
                open=101.0, high=109.0, low=97.0, close=107.0,
            ),
        ]
        h1 = aggregate_to_h1(bars)
        assert len(h1) == 1
        assert h1[0].open == 100.0
        assert h1[0].high == 115.0  # max of all highs
        assert h1[0].low == 95.0  # min of all lows
        assert h1[0].close == 107.0  # last close

    def test_aggregate_h1_partial_discarded(self):
        """5 M15 bars → 1 H1 bar (trailing 1 discarded)."""
        bars = _make_bars([100.0] * 5)
        h1 = aggregate_to_h1(bars)
        assert len(h1) == 1

    def test_aggregate_d1(self):
        """96 M15 bars → 1 D1 bar."""
        bars = _make_bars([2000.0 + i for i in range(96)])
        d1 = aggregate_to_d1(bars)
        assert len(d1) == 1
        assert d1[0].open == bars[0].open
        assert d1[0].close == bars[-1].close

    def test_aggregate_d1_insufficient(self):
        """< 96 bars → 0 D1 bars."""
        bars = _make_bars([100.0] * 50)
        d1 = aggregate_to_d1(bars)
        assert len(d1) == 0


# --- compute_all_indicators ---


class TestComputeAll:
    def test_multi_tf_atr_hierarchy(self):
        """With enough data: ATR(D1) > ATR(H1) > ATR(M15).

        We use trending data so higher TF bars have wider ranges.
        """
        # 15 D1 bars + 1 extra = 16 * 96 = 1536 M15 bars
        n = 16 * 96
        closes = [2000.0 + i * 0.5 for i in range(n)]
        bars = _make_bars(closes)
        snap = compute_all_indicators(bars)

        assert snap.atr_m15 is not None
        assert snap.atr_h1 is not None
        assert snap.atr_d1 is not None
        assert snap.atr_d1 > snap.atr_h1 > snap.atr_m15

    def test_partial_data_returns_nones(self):
        """Very few bars → most indicators None."""
        bars = _make_bars([100.0] * 5)
        snap = compute_all_indicators(bars)
        assert snap.atr_m15 is None
        assert snap.atr_h1 is None
        assert snap.atr_d1 is None
        assert snap.rsi_14 is None
        assert snap.bb_upper is None
        assert snap.sma_50 is None
        assert snap.sma_200 is None

    def test_precomputed_atr_d1_overrides_window(self):
        """When precomputed_atr_d1 is passed, it should be used instead of window aggregation."""
        bars = _make_bars([100.0] * 20)  # too few for D1 ATR from window
        snap = compute_all_indicators(bars, precomputed_atr_d1=42.5)
        assert snap.atr_d1 == 42.5
        # Other indicators still computed from window
        assert snap.atr_m15 is not None

    def test_precomputed_atr_d1_none_falls_back(self):
        """When precomputed_atr_d1 is None, falls back to window aggregation."""
        bars = _make_bars([100.0] * 20)
        snap = compute_all_indicators(bars, precomputed_atr_d1=None)
        assert snap.atr_d1 is None  # window too small for D1


# --- D1 by-date aggregation ---


class TestAggregateD1ByDate:
    def test_single_day(self):
        """All bars on same date → 1 D1 bar."""
        bars = _make_bars([100.0 + i for i in range(10)])  # all on 2025-01-01
        d1 = aggregate_to_d1_by_date(bars)
        assert len(d1) == 1
        assert d1[0].open == bars[0].open
        assert d1[0].close == bars[-1].close

    def test_multiple_days(self):
        """Bars spanning 3 calendar days → 3 D1 bars."""
        bars = []
        for day in range(3):
            for h in range(4):
                bars.append(
                    Bar(
                        timestamp=datetime(2025, 1, 1 + day, h, 0),
                        open=100.0 + day * 10,
                        high=105.0 + day * 10,
                        low=95.0 + day * 10,
                        close=102.0 + day * 10,
                        tick_volume=100,
                    )
                )
        d1 = aggregate_to_d1_by_date(bars)
        assert len(d1) == 3


# --- Precompute D1 ATR series ---


class TestPrecomputeD1ATR:
    def test_insufficient_days(self):
        """< 15 days → empty dict."""
        # 10 days × 96 bars = 960 M15 bars, but only 10 D1 bars < period+1=15
        bars = []
        for day in range(10):
            for i in range(96):
                bars.append(
                    Bar(
                        timestamp=datetime(2025, 1, 1 + day, 0, 0)
                        + timedelta(minutes=15 * i),
                        open=100.0,
                        high=102.5,
                        low=97.5,
                        close=100.0,
                        tick_volume=100,
                    )
                )
        result = precompute_d1_atr_series(bars, period=14)
        assert result == {}

    def test_sufficient_days_returns_values(self):
        """20 days of data → ATR values from day 15 onwards."""
        bars = []
        for day in range(20):
            for i in range(96):
                bars.append(
                    Bar(
                        timestamp=datetime(2025, 1, 1 + day, 0, 0)
                        + timedelta(minutes=15 * i),
                        open=2000.0 + day,
                        high=2005.0 + day,
                        low=1995.0 + day,
                        close=2002.0 + day,
                        tick_volume=100,
                    )
                )
        result = precompute_d1_atr_series(bars, period=14)
        assert len(result) > 0
        # All values should be positive (non-flat data)
        for v in result.values():
            assert v > 0

    def test_constant_range_converges(self):
        """Constant daily range → ATR converges to that range."""
        bars = []
        for day in range(30):
            for i in range(96):
                bars.append(
                    Bar(
                        timestamp=datetime(2025, 1, 1 + day, 0, 0)
                        + timedelta(minutes=15 * i),
                        open=2000.0,
                        high=2010.0,  # daily H-L = 20
                        low=1990.0,
                        close=2000.0,
                        tick_volume=100,
                    )
                )
        result = precompute_d1_atr_series(bars, period=14)
        # ATR should converge to ~20 (daily range is always 20)
        last_date = max(result.keys())
        assert result[last_date] == pytest.approx(20.0, abs=1.0)
