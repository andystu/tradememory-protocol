"""LLM prompt builder for the Replay Engine.

Provides a generic system prompt and a user prompt formatter.
Override the system prompt via ReplayConfig.system_prompt to inject
your own strategy rules (e.g. from a private strategy package).
"""

from typing import Dict, List, Optional

from .models import Bar, IndicatorSnapshot, Position


def build_system_prompt() -> str:
    """Return a generic trading agent system prompt.

    This is a minimal placeholder. For real strategy rules, set
    ReplayConfig.system_prompt to your own strategy-specific prompt.

    Example override::

        from tradememory.replay.models import ReplayConfig

        config = ReplayConfig(
            data_path="data/prices.csv",
            system_prompt=MY_STRATEGY_PROMPT,  # your custom rules
        )
    """
    return """You are a trading agent analyzing OHLCV price data on M15 bars.
Your job is to decide: BUY, SELL, HOLD, or CLOSE based on your strategy rules.

## Decision Rules
- If no clear setup exists, output HOLD with confidence = 0.
- If you have an open position, decide HOLD (keep it) or CLOSE (exit at market).
- Max 1 position at a time.
- Output JSON with: decision, strategy_used, entry_price, stop_loss, take_profit,
  confidence, market_observation, reasoning_trace."""


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
    memory_context: Optional[str] = None,
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

    # Past similar trades from memory recall
    if memory_context:
        section = memory_context.replace(
            "## Similar Past Trades", "## Past Similar Trades"
        )
        if not section.startswith("## Past Similar Trades"):
            section = "## Past Similar Trades\n" + section
        parts.append(section)

    parts.append("\nWhat is your trading decision? Respond with JSON.")

    return "\n\n".join(parts)
