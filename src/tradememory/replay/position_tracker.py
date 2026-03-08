"""Position lifecycle manager for XAUUSD replay engine."""

import uuid
from typing import Optional

from .models import AgentDecision, Bar, DecisionType, Position, PositionState


class PositionTracker:
    """Manages position open/close lifecycle, equity, and drawdown tracking."""

    def __init__(self, lot_size: float = 0.10, initial_equity: float = 10000.0):
        self.lot_size = lot_size
        self.equity = initial_equity
        self.peak_equity = initial_equity
        self.drawdown_pct = 0.0
        self.current_position: Optional[Position] = None
        self.closed_positions: list[Position] = []

    def open_position(self, decision: AgentDecision, bar: Bar) -> Position:
        """Open a new position from an agent decision.

        Raises ValueError if a position is already open.
        """
        if self.current_position is not None:
            raise ValueError("Position already open")

        if decision.decision == DecisionType.BUY:
            direction = "long"
        elif decision.decision == DecisionType.SELL:
            direction = "short"
        else:
            raise ValueError(f"Cannot open position with decision {decision.decision}")

        entry_price = decision.entry_price if decision.entry_price is not None else bar.close

        self.current_position = Position(
            trade_id=str(uuid.uuid4())[:8],
            direction=direction,
            strategy=decision.strategy_used or "unknown",
            entry_price=entry_price,
            entry_time=bar.timestamp,
            stop_loss=decision.stop_loss or 0.0,
            take_profit=decision.take_profit or 0.0,
            confidence=decision.confidence,
            reasoning=decision.reasoning_trace,
            market_observation=decision.market_observation,
        )
        return self.current_position

    def check_bar(self, bar: Bar) -> Optional[Position]:
        """Check if current bar triggers SL or TP. Updates MAE and bars_held.

        Returns closed Position if SL/TP hit, None otherwise.
        """
        if self.current_position is None:
            return None

        pos = self.current_position
        pos.bars_held += 1

        if pos.direction == "long":
            # MAE: worst adverse move for a long = how far price dropped below entry
            adverse = pos.entry_price - bar.low
            if adverse > pos.max_adverse_excursion:
                pos.max_adverse_excursion = adverse

            # SL hit: bar low touches or breaches stop loss
            if pos.stop_loss > 0 and bar.low <= pos.stop_loss:
                return self._close(bar, pos.stop_loss, PositionState.CLOSED_SL)

            # TP hit: bar high touches or breaches take profit
            if pos.take_profit > 0 and bar.high >= pos.take_profit:
                return self._close(bar, pos.take_profit, PositionState.CLOSED_TP)

        else:  # short
            # MAE: worst adverse move for a short = how far price rose above entry
            adverse = bar.high - pos.entry_price
            if adverse > pos.max_adverse_excursion:
                pos.max_adverse_excursion = adverse

            # SL hit: bar high touches or breaches stop loss
            if pos.stop_loss > 0 and bar.high >= pos.stop_loss:
                return self._close(bar, pos.stop_loss, PositionState.CLOSED_SL)

            # TP hit: bar low touches or breaches take profit
            if pos.take_profit > 0 and bar.low <= pos.take_profit:
                return self._close(bar, pos.take_profit, PositionState.CLOSED_TP)

        return None

    def close_position(self, bar: Bar, reason: PositionState) -> Position:
        """Force-close the current position at bar.close.

        Raises ValueError if no position is open.
        """
        if self.current_position is None:
            raise ValueError("No position to close")

        return self._close(bar, bar.close, reason)

    def _close(self, bar: Bar, exit_price: float, state: PositionState) -> Position:
        """Internal close: compute PnL, update equity/drawdown, archive position."""
        pos = self.current_position
        assert pos is not None

        pos.exit_price = exit_price
        pos.exit_time = bar.timestamp
        pos.state = state

        # PnL: (exit - entry) * lots * 100 for long, negated for short
        price_diff = exit_price - pos.entry_price
        if pos.direction == "short":
            price_diff = -price_diff
        pos.pnl = price_diff * self.lot_size * 100

        # R-multiple: pnl / risk_per_trade
        risk_distance = abs(pos.entry_price - pos.stop_loss)
        if risk_distance > 0:
            risk_dollars = risk_distance * self.lot_size * 100
            pos.pnl_r = pos.pnl / risk_dollars
        else:
            pos.pnl_r = 0.0

        # Update equity and drawdown
        self.equity += pos.pnl
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        if self.peak_equity > 0:
            self.drawdown_pct = (self.peak_equity - self.equity) / self.peak_equity * 100

        self.closed_positions.append(pos)
        self.current_position = None
        return pos
