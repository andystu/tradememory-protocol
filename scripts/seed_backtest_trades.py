#!/usr/bin/env python3
"""Seed Strategy E backtest trades from JSON into Supabase live_trades table.

Reads data/strategy_e_backtest.json, deletes existing backtest rows for strategy_e,
then inserts all trades.

Usage:
    cd C:/Users/johns/projects/tradememory-protocol
    python scripts/seed_backtest_trades.py

Env vars required:
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY
"""

import json
import os
import sys
from pathlib import Path

from supabase import create_client

STRATEGY_ID = "strategy_e"
JSON_PATH = Path(__file__).parent.parent / "data" / "strategy_e_backtest.json"


def get_supabase():
    """Create Supabase client from env vars."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def load_trades() -> list[dict]:
    """Load backtest trades from JSON file."""
    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found. Run export_backtest_trades.py first.")
        sys.exit(1)

    with open(JSON_PATH, encoding="utf-8") as f:
        trades = json.load(f)

    print(f"Loaded {len(trades)} trades from {JSON_PATH}")
    return trades


def main():
    print("=== Seed Backtest Trades into Supabase ===\n")

    # 1. Load JSON
    trades = load_trades()

    # 2. Connect Supabase
    sb = get_supabase()

    # 3. DELETE existing backtest rows for strategy_e
    print(f"Deleting existing backtest trades for {STRATEGY_ID}...")
    result = (
        sb.table("live_trades")
        .delete()
        .eq("strategy_id", STRATEGY_ID)
        .eq("trade_type", "backtest")
        .execute()
    )
    deleted = len(result.data) if result.data else 0
    print(f"  Deleted {deleted} existing rows")

    # 4. INSERT trades (override strategy_id to match live system)
    print(f"\nInserting {len(trades)} trades...")
    inserted = 0
    errors = 0

    for i, trade in enumerate(trades):
        row = {
            "strategy_id": STRATEGY_ID,
            "symbol": trade["symbol"],
            "direction": trade["direction"],
            "entry_price": trade["entry_price"],
            "exit_price": trade["exit_price"],
            "entry_time": trade["entry_time"],
            "exit_time": trade["exit_time"],
            "pnl_pct": trade["pnl_pct"],
            "pnl_r": trade["pnl_r"],
            "exit_reason": trade["exit_reason"],
            "trade_type": "backtest",
        }
        # Include optional fields if present
        if trade.get("holding_bars") is not None:
            row["holding_bars"] = trade["holding_bars"]
        if trade.get("atr_at_entry") is not None:
            row["atr_at_entry"] = trade["atr_at_entry"]
        if trade.get("trend_12h_pct") is not None:
            row["trend_12h_pct"] = trade["trend_12h_pct"]

        try:
            sb.table("live_trades").insert(row).execute()
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  ERROR on trade {i}: {e}")
            elif errors == 4:
                print("  ... suppressing further errors")

    # 5. Summary
    print(f"\n--- Summary ---")
    print(f"  Loaded:   {len(trades)}")
    print(f"  Inserted: {inserted}")
    print(f"  Errors:   {errors}")
    print(f"  Deleted:  {deleted} (prior backtest rows)")

    if trades:
        wins = sum(1 for t in trades if t["pnl_pct"] > 0)
        losses = len(trades) - wins
        total_pnl = sum(t["pnl_pct"] for t in trades)
        print(f"  Wins:     {wins}")
        print(f"  Losses:   {losses}")
        print(f"  Total PnL%: {total_pnl:.2f}%")

    if errors > 0:
        print("\nWARNING: Some inserts failed. Check table schema matches.")
        sys.exit(1)


if __name__ == "__main__":
    main()
