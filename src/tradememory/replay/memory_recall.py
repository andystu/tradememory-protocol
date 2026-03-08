"""Memory recall for replay: query episodic_memory for similar past trades."""

import sqlite3
from typing import List, Optional


def build_memory_context(
    db_path: str,
    strategy: Optional[str] = None,
    regime: Optional[str] = None,
    session: Optional[str] = None,
    atr_d1: float = 0.0,
    limit: int = 5,
) -> str:
    """Query episodic_memory for similar past trades and format as prompt context.

    Matches on any combination of strategy, context_regime, context_session
    (filters are skipped when None). Ordered by retrieval_strength DESC.

    Returns a formatted string block for injection into LLM prompts.
    Returns empty string if no matches found.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conditions: List[str] = []
        params: List[object] = []
        if strategy is not None:
            conditions.append("strategy = ?")
            params.append(strategy)
        if regime is not None:
            conditions.append("context_regime = ?")
            params.append(regime)
        if session is not None:
            conditions.append("context_session = ?")
            params.append(session)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT strategy, entry_price, exit_price, pnl, pnl_r, reflection
            FROM episodic_memory
            {where_clause}
            ORDER BY retrieval_strength DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        if not rows:
            return ""

        lines = ["## Similar Past Trades"]
        for i, row in enumerate(rows, 1):
            reflection = (row["reflection"] or "")[:150]
            lines.append(
                f"{i}. [{row['strategy']}] "
                f"entry={row['entry_price']:.2f} exit={row['exit_price']:.2f} "
                f"pnl=${row['pnl']:.2f} pnl_r={row['pnl_r']:.2f}"
            )
            if reflection:
                lines.append(f"   Reflection: {reflection}")
        return "\n".join(lines)
    finally:
        conn.close()
