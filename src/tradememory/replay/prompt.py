"""LLM prompt builder aligned with NG_Gold EA logic.

Builds system and user prompts that encode the exact strategy rules
from the NG_Gold MQL5 Expert Advisors (VolBreakout, IntradayMomentum,
PullbackEntry) so an LLM agent can replicate EA decision-making.
"""

from datetime import datetime
from typing import Dict, List, Optional

from .models import Bar, IndicatorSnapshot, Position


def build_system_prompt() -> str:
    """Return ~600 token system prompt defining 3 XAUUSD strategies.

    All parameters match NG_Gold EA defaults. Server time = FXTM GMT+2.
    """
    return """You are a XAUUSD trading agent. You execute exactly 3 strategies on M15 bars.
Server time: FXTM GMT+2. BUY-only default. Risk: 0.25% equity per trade.

## Strategy 1: VolBreakout (VB)
- Asia session: 00:00–07:00 server time.
- At 07:00, read ATR(14, D1). Filter: asia_range < 0.3 × ATR(D1).
- Entry window: 07:00–14:00. BUY when M5 close > asia_high + 0.15 × ATR(D1).
- SL = asia_low − 0.25 × ATR(M5). TP = entry + asia_range × 3.5.
- One trade per day. Force close at 21:00.

## Strategy 2: IntradayMomentum (IM)
- Check at 10:00 only.
- day_move = close_10h − day_open. day_range = high_0010 − low_0010.
- direction_ratio = |day_move| / day_range. momentum_ratio = |day_move| / ATR(D1).
- BUY when direction_ratio > 0.55 AND momentum_ratio > 0.3 AND day_move > 0.
- SL = low_0010 − 0.25 × ATR(M5). TP = entry + 2.5 × risk.

## Strategy 3: PullbackEntry (PB)
- FSM states: IDLE → BREAKOUT → PULLBACK_READY → DONE.
- At 07:00, compute asia range from H1 bars. Filter: asia_range < 0.35 × ATR(D1).
- BREAKOUT: bid > asia_high. Track swing_high.
- PULLBACK_READY: bid < swing_high − 0.3 × ATR(D1).
- pullback_level = swing_high − 0.6 × (swing_high − asia_high).
- BUY when bid <= pullback_level.
- SL = asia_low − 0.25 × ATR(M5). TP = entry + 2.0 × risk.
- Window: 07:00–16:00.

## Common Rules
- SL buffer: 0.25 × ATR(M5) below structure low.
- Max 1 position per strategy. Respond with JSON: decision, strategy, entry, SL, TP, reasoning."""


def format_bars_table(bars: List[Bar], max_rows: int = 20) -> str:
    """Format bars into a compact table. Truncates to most recent max_rows."""
    if not bars:
        return "No bar data available."

    display = bars[-max_rows:] if len(bars) > max_rows else bars
    truncated = len(bars) > max_rows

    lines = ["time|open|high|low|close|vol"]
    for b in display:
        ts = b.timestamp.strftime("%m-%d %H:%M")
        lines.append(
            f"{ts}|{b.open:.2f}|{b.high:.2f}|{b.low:.2f}|{b.close:.2f}|{b.tick_volume}"
        )

    header = f"Last {len(display)} of {len(bars)} bars:\n" if truncated else ""
    return header + "\n".join(lines)


def build_user_prompt(
    current_bar: Bar,
    window_bars: List[Bar],
    indicators: IndicatorSnapshot,
    open_position: Optional[Position] = None,
    recent_trades: Optional[List[Dict]] = None,
    equity: float = 10000.0,
    asia_range: Optional[float] = None,
) -> str:
    """Return ~1000 token user prompt with market state for LLM decision.

    Args:
        current_bar: The current M15 bar.
        window_bars: Recent bars for context (truncated to 20 in table).
        indicators: Computed indicator snapshot at current time.
        open_position: Currently open position, if any.
        recent_trades: List of recent closed trade dicts.
        equity: Current account equity.
        asia_range: Pre-computed asia session range (high - low), if available.
    """
    ts = current_bar.timestamp.strftime("%Y-%m-%d %H:%M")

    parts = [
        f"## Current Bar\n"
        f"Time: {ts} | O: {current_bar.open:.2f} | H: {current_bar.high:.2f} | "
        f"L: {current_bar.low:.2f} | C: {current_bar.close:.2f}",
    ]

    # Bars table
    parts.append(f"\n## Recent Bars\n{format_bars_table(window_bars)}")

    # Indicators
    ind_lines = ["## Indicators"]
    if indicators.atr_d1 is not None:
        ind_lines.append(f"ATR(14,D1): {indicators.atr_d1:.2f}")
    if indicators.atr_h1 is not None:
        ind_lines.append(f"ATR(14,H1): {indicators.atr_h1:.2f}")
    if indicators.atr_m15 is not None:
        ind_lines.append(f"ATR(14,M15): {indicators.atr_m15:.2f}")
    if indicators.rsi_14 is not None:
        ind_lines.append(f"RSI(14): {indicators.rsi_14:.1f}")
    if indicators.sma_50 is not None:
        ind_lines.append(f"SMA(50): {indicators.sma_50:.2f}")
    if indicators.sma_200 is not None:
        ind_lines.append(f"SMA(200): {indicators.sma_200:.2f}")
    parts.append("\n".join(ind_lines))

    # Asia range
    if asia_range is not None:
        parts.append(f"\n## Asia Range\nasia_range: {asia_range:.2f}")
        if indicators.atr_d1 is not None and indicators.atr_d1 > 0:
            ratio = asia_range / indicators.atr_d1
            parts.append(f"asia_range / ATR(D1): {ratio:.3f}")

    # Open position
    if open_position is not None:
        unreal = current_bar.close - open_position.entry_price
        parts.append(
            f"\n## Open Position\n"
            f"Strategy: {open_position.strategy} | Dir: {open_position.direction} | "
            f"Entry: {open_position.entry_price:.2f}\n"
            f"SL: {open_position.stop_loss:.2f} | TP: {open_position.take_profit:.2f} | "
            f"Unrealized: {unreal:+.2f}"
        )

    # Recent trades
    if recent_trades:
        trade_lines = ["## Recent Trades"]
        for t in recent_trades[-5:]:
            pnl = t.get("pnl", 0.0)
            strategy = t.get("strategy", "?")
            result = t.get("result", "?")
            trade_lines.append(f"- {strategy}: {result} PnL={pnl:+.2f}")
        parts.append("\n".join(trade_lines))

    # Equity
    parts.append(f"\n## Account\nEquity: ${equity:,.2f} | Risk per trade: 0.25%")

    parts.append("\nWhat is your trading decision? Respond with JSON.")

    return "\n\n".join(parts)
