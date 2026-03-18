"""Pure Python indicator calculations (NO TA-Lib).

All functions accept lists of Bar and return None when insufficient data.
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

from tradememory.replay.models import Bar, IndicatorSnapshot


def _true_range(bar: Bar, prev_bar: Optional[Bar]) -> float:
    """True Range = max(H-L, |H-prevC|, |L-prevC|)."""
    if prev_bar is None:
        return bar.high - bar.low
    return max(
        bar.high - bar.low,
        abs(bar.high - prev_bar.close),
        abs(bar.low - prev_bar.close),
    )


def compute_atr(bars: List[Bar], period: int = 14) -> Optional[float]:
    """ATR using Wilder's smoothing.

    First ATR = simple average of first `period` true ranges.
    Subsequent: ATR = (prev_atr * (period - 1) + current_tr) / period.
    Requires at least period + 1 bars (period TRs need a previous close).
    """
    if len(bars) < period + 1:
        return None

    # Compute all true ranges (skip first bar — no prev close for it)
    trs: List[float] = []
    for i in range(1, len(bars)):
        trs.append(_true_range(bars[i], bars[i - 1]))

    if len(trs) < period:
        return None

    # Seed: simple average of first `period` TRs
    atr = sum(trs[:period]) / period

    # Wilder's smoothing for the rest
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period

    return atr


def compute_rsi(bars: List[Bar], period: int = 14) -> Optional[float]:
    """RSI using Wilder's smoothing on close-to-close changes.

    Requires at least period + 1 bars.
    """
    if len(bars) < period + 1:
        return None

    changes = [bars[i].close - bars[i - 1].close for i in range(1, len(bars))]

    if len(changes) < period:
        return None

    # Seed averages from first `period` changes
    gains = [max(c, 0.0) for c in changes[:period]]
    losses = [max(-c, 0.0) for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder's smoothing for the rest
    for c in changes[period:]:
        avg_gain = (avg_gain * (period - 1) + max(c, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-c, 0.0)) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def compute_sma(bars: List[Bar], period: int) -> Optional[float]:
    """Simple Moving Average of the last `period` closes."""
    if len(bars) < period:
        return None
    return sum(b.close for b in bars[-period:]) / period


def compute_bollinger_bands(
    bars: List[Bar], period: int = 20, num_std: float = 2.0
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Bollinger Bands: (upper, middle, lower).

    Middle = SMA(period). Bands = middle +/- num_std * stdev.
    """
    if len(bars) < period:
        return None, None, None

    closes = [b.close for b in bars[-period:]]
    middle = sum(closes) / period
    variance = sum((c - middle) ** 2 for c in closes) / period
    std = variance**0.5
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def aggregate_to_h1(m15_bars: List[Bar]) -> List[Bar]:
    """Group M15 bars into H1 bars (4 bars per group).

    OHLC: first open, max high, min low, last close.
    Incomplete trailing group is discarded.
    """
    result: List[Bar] = []
    count = len(m15_bars) // 4
    for i in range(count):
        group = m15_bars[i * 4 : (i + 1) * 4]
        result.append(
            Bar(
                timestamp=group[0].timestamp,
                open=group[0].open,
                high=max(b.high for b in group),
                low=min(b.low for b in group),
                close=group[-1].close,
                tick_volume=sum(b.tick_volume for b in group),
                spread=max(b.spread for b in group),
            )
        )
    return result


def aggregate_to_d1(m15_bars: List[Bar]) -> List[Bar]:
    """Group M15 bars into D1 bars (96 bars per group).

    OHLC: first open, max high, min low, last close.
    Incomplete trailing group is discarded.
    """
    result: List[Bar] = []
    count = len(m15_bars) // 96
    for i in range(count):
        group = m15_bars[i * 96 : (i + 1) * 96]
        result.append(
            Bar(
                timestamp=group[0].timestamp,
                open=group[0].open,
                high=max(b.high for b in group),
                low=min(b.low for b in group),
                close=group[-1].close,
                tick_volume=sum(b.tick_volume for b in group),
                spread=max(b.spread for b in group),
            )
        )
    return result


def aggregate_to_d1_by_date(m15_bars: List[Bar]) -> List[Bar]:
    """Group M15 bars into D1 bars by calendar date.

    More robust than fixed 96-bar chunks — handles weekends and partial days.
    """
    from collections import OrderedDict

    groups: OrderedDict[date, List[Bar]] = OrderedDict()
    for bar in m15_bars:
        d = bar.timestamp.date()
        if d not in groups:
            groups[d] = []
        groups[d].append(bar)

    result: List[Bar] = []
    for d, bars in groups.items():
        result.append(
            Bar(
                timestamp=bars[0].timestamp,
                open=bars[0].open,
                high=max(b.high for b in bars),
                low=min(b.low for b in bars),
                close=bars[-1].close,
                tick_volume=sum(b.tick_volume for b in bars),
                spread=max(b.spread for b in bars),
            )
        )
    return result


def precompute_d1_atr_series(
    m15_bars: List[Bar], period: int = 14
) -> Dict[date, float]:
    """Pre-compute D1 ATR for all dates using Wilder's smoothing.

    Aggregates ALL M15 bars by calendar date, then computes ATR incrementally.
    Returns {date: atr} for each date where sufficient history exists.
    """
    d1_bars = aggregate_to_d1_by_date(m15_bars)

    if len(d1_bars) < period + 1:
        return {}

    # Compute all true ranges
    trs: List[float] = []
    for i in range(1, len(d1_bars)):
        trs.append(_true_range(d1_bars[i], d1_bars[i - 1]))

    result: Dict[date, float] = {}

    # Seed: simple average of first `period` TRs
    atr = sum(trs[:period]) / period
    result[d1_bars[period].timestamp.date()] = atr

    # Wilder's smoothing for the rest
    for j in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[j]) / period
        result[d1_bars[j + 1].timestamp.date()] = atr

    return result


def compute_all_indicators(bars: List[Bar], precomputed_atr_d1: Optional[float] = None) -> IndicatorSnapshot:
    """Compute multi-TF indicators from M15 bars.

    ATR is computed on M15, H1 (aggregated), and D1 (aggregated).
    RSI, BB, SMA are computed on M15 timeframe.
    """
    atr_m15 = compute_atr(bars, period=14)
    rsi_14 = compute_rsi(bars, period=14)
    bb_upper, bb_middle, bb_lower = compute_bollinger_bands(bars, period=20, num_std=2.0)
    sma_50 = compute_sma(bars, period=50)
    sma_200 = compute_sma(bars, period=200)

    # H1 ATR
    h1_bars = aggregate_to_h1(bars)
    atr_h1 = compute_atr(h1_bars, period=14)

    # D1 ATR: use pre-computed value if available, else fall back to window aggregation
    if precomputed_atr_d1 is not None:
        atr_d1 = precomputed_atr_d1
    else:
        d1_bars = aggregate_to_d1(bars)
        atr_d1 = compute_atr(d1_bars, period=14)

    return IndicatorSnapshot(
        atr_d1=atr_d1,
        atr_h1=atr_h1,
        atr_m15=atr_m15,
        rsi_14=rsi_14,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        sma_50=sma_50,
        sma_200=sma_200,
    )
