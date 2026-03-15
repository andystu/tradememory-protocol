"""Auto-induction: promote episodic memories to semantic when pattern count reaches threshold."""

from collections import defaultdict
from typing import Any


def check_auto_induction(
    episodic_memories: list[dict[str, Any]],
    threshold: int = 10,
) -> list[dict[str, Any]]:
    """Check if any pattern has enough episodic memories to induce a semantic memory.

    Groups episodic memories by pattern_name. When a group reaches the threshold,
    produces a semantic memory dict summarizing the pattern.

    Args:
        episodic_memories: List of episodic memory dicts. Each must have at least
            'pattern_name'. Optional fields: 'pnl_r', 'direction', 'strategy'.
        threshold: Minimum episodic count to trigger induction (default 10).

    Returns:
        List of semantic memory dicts for patterns that crossed the threshold.
        Each dict contains: pattern_name, sample_size, win_rate, avg_pnl_r,
        directions, strategies, source.
    """
    if threshold < 1:
        raise ValueError("threshold must be >= 1")

    groups: dict[str, list[dict]] = defaultdict(list)
    for mem in episodic_memories:
        pattern = mem.get("pattern_name")
        if pattern:
            groups[pattern].append(mem)

    results = []
    for pattern_name, memories in groups.items():
        if len(memories) >= threshold:
            pnl_rs = [m["pnl_r"] for m in memories if "pnl_r" in m]
            wins = sum(1 for p in pnl_rs if p > 0)
            win_rate = wins / len(pnl_rs) if pnl_rs else 0.0
            avg_pnl_r = sum(pnl_rs) / len(pnl_rs) if pnl_rs else 0.0

            directions = sorted(set(m["direction"] for m in memories if "direction" in m))
            strategies = sorted(set(m["strategy"] for m in memories if "strategy" in m))

            results.append({
                "pattern_name": pattern_name,
                "sample_size": len(memories),
                "win_rate": round(win_rate, 4),
                "avg_pnl_r": round(avg_pnl_r, 4),
                "directions": directions,
                "strategies": strategies,
                "source": "auto_induction",
            })

    return results
