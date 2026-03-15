"""Tests for Context Builder (Task 9.3).

All pure functions — no I/O, no mocks needed.
"""

import math
from datetime import datetime, timezone, timedelta

import pytest

from tradememory.data.context_builder import (
    ContextConfig,
    MarketContext,
    Regime,
    RegimeMethod,
    Session,
    VolatilityRegime,
    build_context,
    classify_regime,
    classify_session,
    classify_volatility,
    compute_adx,
    compute_atr,
    compute_sma,
    compute_trend,
)
from tradememory.data.models import OHLCV, OHLCVSeries, Timeframe


# --- Helpers ---


def make_bar(
    ts: datetime,
    o: float = 100.0,
    h: float = 110.0,
    l: float = 90.0,
    c: float = 105.0,
    v: float = 1000.0,
) -> OHLCV:
    return OHLCV(timestamp=ts, open=o, high=h, low=l, close=c, volume=v)


def make_bars(
    count: int,
    start: datetime = datetime(2024, 1, 1, tzinfo=timezone.utc),
    interval: timedelta = timedelta(hours=1),
    base_price: float = 100.0,
    trend: float = 0.0,  # per-bar price change
    volatility: float = 5.0,  # half-range
) -> list[OHLCV]:
    """Generate synthetic OHLCV bars.

    trend > 0 = uptrend, trend < 0 = downtrend, trend = 0 = ranging.
    """
    bars = []
    price = base_price
    for i in range(count):
        ts = start + interval * i
        o = price
        c = price + trend
        h = max(o, c) + volatility
        l = min(o, c) - volatility
        bars.append(OHLCV(timestamp=ts, open=o, high=h, low=l, close=c, volume=1000))
        price = c
    return bars


def make_series(
    bars: list[OHLCV],
    symbol: str = "BTCUSDT",
    timeframe: Timeframe = Timeframe.H1,
) -> OHLCVSeries:
    return OHLCVSeries(symbol=symbol, timeframe=timeframe, bars=bars, source="test")


# --- ATR ---


class TestComputeATR:
    def test_basic_atr(self):
        """ATR of uniform bars = bar range."""
        bars = make_bars(20, volatility=10.0, trend=0.0)
        atr = compute_atr(bars, period=14)
        assert atr is not None
        # Uniform bars: TR = high - low = 20 (volatility * 2)
        assert abs(atr - 20.0) < 1.0

    def test_insufficient_bars(self):
        bars = make_bars(5)
        assert compute_atr(bars, period=14) is None

    def test_single_bar(self):
        bars = make_bars(1)
        assert compute_atr(bars, period=14) is None

    def test_empty_bars(self):
        assert compute_atr([], period=14) is None

    def test_trending_increases_atr(self):
        """Trending market has higher true range due to gaps."""
        calm = make_bars(20, volatility=5.0, trend=0.0)
        trending = make_bars(20, volatility=5.0, trend=3.0)
        atr_calm = compute_atr(calm, period=14)
        atr_trend = compute_atr(trending, period=14)
        assert atr_calm is not None
        assert atr_trend is not None
        assert atr_trend > atr_calm

    def test_exact_period_plus_one(self):
        """Minimum data: period + 1 bars."""
        bars = make_bars(15, volatility=10.0)
        atr = compute_atr(bars, period=14)
        assert atr is not None

    def test_period_exact_insufficient(self):
        """Exactly `period` bars is NOT enough (need period+1)."""
        bars = make_bars(14, volatility=10.0)
        assert compute_atr(bars, period=14) is None


class TestComputeSMA:
    def test_basic_sma(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert compute_sma(values, 5) == 3.0

    def test_sma_last_n(self):
        """SMA uses last N values."""
        values = [100.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        assert compute_sma(values, 5) == 3.0

    def test_insufficient_data(self):
        assert compute_sma([1.0, 2.0], 5) is None


# --- ADX ---


class TestComputeADX:
    def test_trending_market_high_adx(self):
        """Strong trend should produce high ADX."""
        bars = make_bars(50, trend=2.0, volatility=3.0)
        adx = compute_adx(bars, period=14)
        assert adx is not None
        assert adx > 20  # trending

    def test_ranging_market_low_adx(self):
        """Ranging market should produce low ADX."""
        # Alternating up/down = ranging
        bars = []
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for i in range(50):
            ts = start + timedelta(hours=i)
            direction = 1 if i % 2 == 0 else -1
            o = 100.0
            c = 100.0 + direction * 0.5
            bars.append(OHLCV(timestamp=ts, open=o, high=max(o, c) + 2, low=min(o, c) - 2, close=c, volume=1000))
        adx = compute_adx(bars, period=14)
        assert adx is not None
        assert adx < 30  # not strongly trending

    def test_insufficient_bars(self):
        bars = make_bars(10)
        assert compute_adx(bars, period=14) is None


# --- Session ---


class TestClassifySession:
    @pytest.mark.parametrize("hour,expected", [
        (0, Session.ASIA),
        (3, Session.ASIA),
        (6, Session.ASIA),
        (7, Session.LONDON),
        (10, Session.LONDON),
        (12, Session.LONDON),
        (13, Session.OVERLAP),
        (14, Session.OVERLAP),  # Strategy E trigger hour
        (15, Session.OVERLAP),
        (16, Session.NEWYORK),  # Strategy C trigger hour
        (18, Session.NEWYORK),
        (20, Session.NEWYORK),
        (21, Session.ASIA),     # late night = Asia prep
        (23, Session.ASIA),
    ])
    def test_session_classification(self, hour, expected):
        assert classify_session(hour) == expected

    def test_p1_strategy_c_hour(self):
        """Strategy C (US Session Drain) at 16:00 UTC = New York session."""
        assert classify_session(16) == Session.NEWYORK

    def test_p1_strategy_e_hour(self):
        """Strategy E (Afternoon Engine) at 14:00 UTC = Overlap session."""
        assert classify_session(14) == Session.OVERLAP


# --- Regime ---


class TestClassifyRegime:
    def test_trending_up(self):
        bars = make_bars(30, trend=3.0, volatility=3.0)
        regime = classify_regime(bars)
        assert regime == Regime.TRENDING_UP

    def test_trending_down(self):
        bars = make_bars(30, base_price=200.0, trend=-3.0, volatility=3.0)
        regime = classify_regime(bars)
        assert regime == Regime.TRENDING_DOWN

    def test_ranging(self):
        """Small bodies, small ranges = ranging."""
        bars = []
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        for i in range(30):
            ts = start + timedelta(hours=i)
            # Tiny body, moderate range
            bars.append(OHLCV(timestamp=ts, open=100.0, high=102.0, low=98.0, close=100.1, volume=1000))
        regime = classify_regime(bars)
        assert regime == Regime.RANGING

    def test_insufficient_data_defaults_ranging(self):
        bars = make_bars(5)
        regime = classify_regime(bars)
        assert regime == Regime.RANGING

    def test_adx_method(self):
        """ADX method should also detect trends."""
        config = ContextConfig(regime_method=RegimeMethod.ADX)
        bars = make_bars(50, trend=2.0, volatility=3.0)
        regime = classify_regime(bars, config)
        assert regime in (Regime.TRENDING_UP, Regime.TRENDING_DOWN)

    def test_configurable_sma_period(self):
        config = ContextConfig(sma_period=10)
        bars = make_bars(30, trend=3.0, volatility=3.0)
        regime = classify_regime(bars, config)
        assert regime == Regime.TRENDING_UP


# --- Volatility ---


class TestClassifyVolatility:
    def test_normal_volatility(self):
        bars = make_bars(80, volatility=5.0)
        atr = compute_atr(bars, period=14)
        assert atr is not None
        regime, pct = classify_volatility(atr, bars)
        # Uniform bars → percentile should be moderate
        assert regime in (VolatilityRegime.LOW, VolatilityRegime.NORMAL)

    def test_high_current_atr(self):
        """Current ATR much higher than historical = high/extreme."""
        bars = make_bars(80, volatility=5.0)
        # Pretend current ATR is 3x historical
        atr = compute_atr(bars, period=14)
        assert atr is not None
        regime, pct = classify_volatility(atr * 3, bars)
        assert regime in (VolatilityRegime.HIGH, VolatilityRegime.EXTREME)

    def test_low_current_atr(self):
        """Current ATR much lower than historical = low."""
        bars = make_bars(80, volatility=10.0)
        regime, pct = classify_volatility(0.1, bars)
        assert regime == VolatilityRegime.LOW

    def test_insufficient_bars(self):
        bars = make_bars(5)
        regime, pct = classify_volatility(10.0, bars)
        assert regime == VolatilityRegime.NORMAL
        assert pct == 50.0

    def test_custom_thresholds(self):
        config = ContextConfig(vol_low_pct=10, vol_normal_pct=50, vol_extreme_pct=90)
        bars = make_bars(80, volatility=5.0)
        atr = compute_atr(bars, period=14)
        assert atr is not None
        regime, pct = classify_volatility(atr, bars, config)
        # With tighter thresholds, same ATR might classify differently
        assert isinstance(regime, VolatilityRegime)


# --- Trend ---


class TestComputeTrend:
    def test_uptrend(self):
        bars = make_bars(20, trend=2.0, base_price=100.0)
        abs_change, pct_change = compute_trend(bars, 12)
        assert abs_change is not None
        assert abs_change > 0
        assert pct_change is not None
        assert pct_change > 0

    def test_downtrend(self):
        bars = make_bars(30, trend=-1.5, base_price=200.0)
        abs_change, pct_change = compute_trend(bars, 12)
        assert abs_change is not None
        assert abs_change < 0
        assert pct_change is not None
        assert pct_change < 0

    def test_24h_trend(self):
        bars = make_bars(30, trend=1.0, base_price=100.0)
        abs_12, pct_12 = compute_trend(bars, 12)
        abs_24, pct_24 = compute_trend(bars, 24)
        assert abs_12 is not None and abs_24 is not None
        # 24H trend should be larger magnitude than 12H
        assert abs(abs_24) > abs(abs_12)

    def test_insufficient_bars(self):
        bars = make_bars(5)
        abs_change, pct_change = compute_trend(bars, 12)
        assert abs_change is None
        assert pct_change is None

    def test_exact_magnitude(self):
        """Known price change: 10 bars × $2/bar = $20."""
        bars = make_bars(15, trend=2.0, base_price=100.0)
        abs_change, pct_change = compute_trend(bars, 10)
        assert abs_change is not None
        assert abs(abs_change - 20.0) < 0.01


# --- build_context ---


class TestBuildContext:
    def test_basic_build(self):
        bars = make_bars(30, trend=0.5, base_price=42000.0)
        series = make_series(bars)
        ctx = build_context(series)

        assert ctx.symbol == "BTCUSDT"
        assert ctx.price is not None
        assert ctx.hour_utc is not None
        assert ctx.session is not None
        assert ctx.atr_h1 is not None
        assert ctx.regime is not None

    def test_empty_series(self):
        series = make_series([])
        ctx = build_context(series)
        assert ctx.symbol == "BTCUSDT"
        assert ctx.price is None

    def test_single_bar(self):
        bars = make_bars(1)
        series = make_series(bars)
        ctx = build_context(series)
        assert ctx.price is not None
        assert ctx.atr_h1 is None  # insufficient data

    def test_bar_index(self):
        """Build context at specific bar."""
        bars = make_bars(30)
        series = make_series(bars)
        ctx = build_context(series, bar_index=10)
        assert ctx.timestamp == bars[10].timestamp

    def test_negative_bar_index(self):
        """Negative index: -1 = last bar."""
        bars = make_bars(30)
        series = make_series(bars)
        ctx = build_context(series, bar_index=-1)
        assert ctx.timestamp == bars[-1].timestamp

    def test_out_of_range_index(self):
        bars = make_bars(10)
        series = make_series(bars)
        ctx = build_context(series, bar_index=100)
        assert ctx.price is None

    def test_trend_fields(self):
        """Trending data should produce non-None trend fields."""
        bars = make_bars(30, trend=1.0, base_price=100.0)
        series = make_series(bars)
        ctx = build_context(series)
        assert ctx.trend_12h is not None
        assert ctx.trend_12h_pct is not None
        assert ctx.trend_24h is not None
        assert ctx.trend_24h_pct is not None
        assert ctx.trend_12h > 0  # uptrend

    def test_multiframe_atr_with_d1(self):
        """D1 series provides atr_d1."""
        h1_bars = make_bars(30, volatility=5.0)
        d1_bars = make_bars(
            30,
            volatility=50.0,
            interval=timedelta(days=1),
            start=datetime(2023, 12, 1, tzinfo=timezone.utc),
        )
        h1_series = make_series(h1_bars, timeframe=Timeframe.H1)
        d1_series = make_series(d1_bars, timeframe=Timeframe.D1)

        ctx = build_context(h1_series, d1_series=d1_series)
        assert ctx.atr_h1 is not None
        assert ctx.atr_d1 is not None
        assert ctx.atr_d1 > ctx.atr_h1  # D1 ATR >> H1 ATR
        assert ctx.atr_ratio_h1_d1 is not None
        assert 0 < ctx.atr_ratio_h1_d1 < 1

    def test_volatility_regime_computed(self):
        bars = make_bars(80, volatility=5.0)
        series = make_series(bars)
        ctx = build_context(series)
        assert ctx.volatility_regime is not None
        assert ctx.atr_percentile is not None

    def test_custom_config(self):
        """Custom config propagates."""
        config = ContextConfig(
            atr_period=7,
            sma_period=10,
            trend_12h_bars=6,
            trend_24h_bars=12,
        )
        bars = make_bars(30, trend=1.0)
        series = make_series(bars)
        ctx = build_context(series, config=config)
        assert ctx.atr_h1 is not None  # shorter period = computable with fewer bars

    def test_day_of_week(self):
        """Monday bar = day_of_week 0."""
        # 2024-01-01 is Monday
        bars = make_bars(20, start=datetime(2024, 1, 1, tzinfo=timezone.utc))
        series = make_series(bars)
        ctx = build_context(series, bar_index=0)
        assert ctx.day_of_week == 0  # Monday

    def test_p1_strategy_c_context(self):
        """16:00 UTC bar → newyork session, correct hour."""
        start = datetime(2024, 1, 1, 16, 0, tzinfo=timezone.utc)
        bars = make_bars(30, start=start)
        series = make_series(bars)
        ctx = build_context(series, bar_index=0)
        assert ctx.hour_utc == 16
        assert ctx.session == Session.NEWYORK

    def test_p1_strategy_e_context(self):
        """14:00 UTC bar → overlap session, correct hour."""
        start = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
        bars = make_bars(30, start=start)
        series = make_series(bars)
        ctx = build_context(series, bar_index=0)
        assert ctx.hour_utc == 14
        assert ctx.session == Session.OVERLAP


# --- to_owm_context ---


class TestToOWMContext:
    def test_conversion(self):
        bars = make_bars(30, trend=0.5, base_price=42000.0)
        series = make_series(bars)
        ctx = build_context(series)
        owm = ctx.to_owm_context()

        assert owm.symbol == "BTCUSDT"
        assert owm.price == ctx.price
        assert owm.atr_h1 == ctx.atr_h1
        assert owm.atr_d1 == ctx.atr_d1
        assert owm.hour_utc == ctx.hour_utc
        assert owm.day_of_week == ctx.day_of_week

    def test_regime_string_conversion(self):
        bars = make_bars(30, trend=1.5, volatility=3.0)
        series = make_series(bars)
        ctx = build_context(series)
        owm = ctx.to_owm_context()
        # OWM uses string values, not enum
        assert owm.regime in ("trending_up", "trending_down", "ranging", "volatile")

    def test_none_fields(self):
        """Empty context converts without error."""
        ctx = MarketContext(symbol="TEST")
        owm = ctx.to_owm_context()
        assert owm.symbol == "TEST"
        assert owm.regime is None


# --- ContextConfig ---


class TestContextConfig:
    def test_defaults(self):
        config = ContextConfig()
        assert config.atr_period == 14
        assert config.sma_period == 20
        assert config.trend_12h_bars == 12
        assert config.trend_24h_bars == 24

    def test_custom(self):
        config = ContextConfig(atr_period=7, trend_12h_bars=6)
        assert config.atr_period == 7
        assert config.trend_12h_bars == 6
