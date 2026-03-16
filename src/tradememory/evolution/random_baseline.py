"""Random baseline generator for Evolution Engine.

Generates random strategies to establish a null-hypothesis baseline.
Any real pattern must beat the 95th percentile of random strategies
to be considered statistically significant.
"""

from __future__ import annotations

import random
from typing import List

from pydantic import BaseModel

from tradememory.evolution.models import (
    CandidatePattern,
    ConditionOperator,
    EntryCondition,
    ExitCondition,
    RuleCondition,
)


class BaselineResult(BaseModel):
    """Summary statistics from a random strategy baseline run."""

    n_strategies: int
    sharpe_distribution: List[float]  # sorted ascending
    mean_sharpe: float
    std_sharpe: float
    percentile_95: float  # Sharpe value at 95th percentile


class RandomStrategyGenerator:
    """Generate random trading strategies for baseline comparison.

    Each strategy has a random hour-of-day entry, random direction,
    and fixed exit rules. Used to establish a null distribution of
    Sharpe ratios against which real patterns are tested.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def generate(self, n: int = 1000) -> List[CandidatePattern]:
        """Generate n random candidate patterns."""
        patterns: List[CandidatePattern] = []
        for i in range(n):
            hour = self._rng.randint(0, 23)
            direction = self._rng.choice(["long", "short"])

            pattern = CandidatePattern(
                pattern_id=f"RANDOM-{i + 1:03d}",
                name=f"RANDOM-{i + 1:03d}",
                description=f"Random baseline: {direction} at hour {hour} UTC",
                entry_condition=EntryCondition(
                    direction=direction,
                    conditions=[
                        RuleCondition(
                            field="hour_utc",
                            op=ConditionOperator.EQ,
                            value=hour,
                        )
                    ],
                    description=f"Enter {direction} when hour_utc == {hour}",
                ),
                exit_condition=ExitCondition(
                    stop_loss_atr=1.0,
                    take_profit_atr=2.0,
                    max_holding_bars=6,
                ),
                confidence=0.0,
                source="random_baseline",
            )
            patterns.append(pattern)
        return patterns
