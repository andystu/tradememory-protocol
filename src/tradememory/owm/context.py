"""ContextVector and context_similarity for OWM framework.

Reference: docs/OWM_FRAMEWORK.md Section 2.6
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class ContextVector:
    """Market context at a point in time."""

    # Price
    symbol: Optional[str] = None
    price: Optional[float] = None

    # Volatility (multi-timeframe)
    atr_d1: Optional[float] = None          # ATR(14) on D1 in dollars
    atr_h1: Optional[float] = None          # ATR(14) on H1 in dollars
    atr_m5: Optional[float] = None          # ATR(14) on M5 in dollars
    atr_ratio_h1_d1: Optional[float] = None # H1/D1 ratio

    # Regime classification
    regime: Optional[str] = None            # 'trending_up', 'trending_down', 'ranging', 'volatile'
    volatility_regime: Optional[str] = None # 'low', 'normal', 'high', 'extreme'

    # Session
    session: Optional[str] = None           # 'asia', 'london', 'newyork', 'overlap'
    hour_utc: Optional[int] = None
    day_of_week: Optional[int] = None       # 0=Mon, 4=Fri

    # Spread
    spread_points: Optional[float] = None
    spread_as_atr_pct: Optional[float] = None  # spread / ATR(M5)

    # Agent state
    drawdown_pct: Optional[float] = None
    consecutive_losses: Optional[int] = None
    confidence: Optional[float] = None


# Weights from OWM_FRAMEWORK.md Section 2.6
_CATEGORICAL_WEIGHTS = [
    ("regime", 0.25),
    ("volatility_regime", 0.15),
    ("session", 0.10),
]

_NUMERICAL_WEIGHTS = [
    # (field, weight, bandwidth_as_fraction)
    ("atr_d1", 0.15, 0.3),
    ("atr_h1", 0.10, 0.3),
    ("spread_as_atr_pct", 0.05, 0.5),
    ("drawdown_pct", 0.10, 0.1),
    ("price", 0.10, 0.2),
]


def context_similarity(c1: ContextVector, c2: ContextVector) -> float:
    """Compute similarity between two context vectors.

    Uses weighted combination of:
    - Categorical fields: exact match → 1.0, else 0.0
    - Numerical fields: Gaussian kernel exp(-0.5 * ((v1-v2)/(bw*|v1|))^2)

    Returns value in [0, 1].
    """
    score = 0.0
    total_weight = 0.0

    # Categorical matches (exact)
    for field, weight in _CATEGORICAL_WEIGHTS:
        v1 = getattr(c1, field)
        v2 = getattr(c2, field)
        if v1 is None or v2 is None:
            continue
        total_weight += weight
        if v1 == v2:
            score += weight

    # Numerical similarity (Gaussian kernel)
    for field, weight, bandwidth in _NUMERICAL_WEIGHTS:
        v1 = getattr(c1, field)
        v2 = getattr(c2, field)
        if v1 is None or v2 is None or v1 == 0:
            continue
        total_weight += weight
        ratio = (v1 - v2) / (bandwidth * abs(v1))
        similarity = math.exp(-0.5 * ratio * ratio)
        score += weight * similarity

    # When no fields overlap, return 0.5 (neutral) instead of 0.0 (exclusion).
    # This prevents killing recall score when context data is sparse.
    return score / total_weight if total_weight > 0 else 0.5
