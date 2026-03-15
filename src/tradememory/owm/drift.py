"""CUSUM drift detection for strategy performance monitoring.

Detects regime changes in win-rate using cumulative sum (CUSUM) method.
"""


def cusum_drift_detect(
    pnl_ratios: list[float],
    target_wr: float = 0.5,
    threshold: float = 4.0,
) -> dict:
    """Detect performance drift using one-sided CUSUM on binary win/loss outcomes.

    Converts pnl_ratios to binary outcomes (1 if > 0, else 0), then applies:
        S_i = max(0, S_{i-1} + (x_i - target_wr))

    Drift is detected when S exceeds threshold, indicating the win rate has
    shifted above the target. For detecting downward drift (degradation),
    pass 1-target_wr or negate the outcomes externally.

    Args:
        pnl_ratios: List of P&L ratios. Positive = win, non-positive = loss.
        target_wr: Expected win rate (default 0.5).
        threshold: CUSUM threshold for drift detection (default 4.0).

    Returns:
        Dict with:
            drift_detected: bool — True if CUSUM exceeded threshold.
            drift_point: int or None — Index where drift was first detected.
            cusum_values: list[float] — Full CUSUM series.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    if not 0 <= target_wr <= 1:
        raise ValueError("target_wr must be between 0 and 1")

    cusum_values: list[float] = []
    s = 0.0
    drift_point = None

    for i, pnl in enumerate(pnl_ratios):
        x = 1.0 if pnl > 0 else 0.0
        s = max(0.0, s + (x - target_wr))
        cusum_values.append(round(s, 6))
        if drift_point is None and s > threshold:
            drift_point = i

    return {
        "drift_detected": drift_point is not None,
        "drift_point": drift_point,
        "cusum_values": cusum_values,
    }
