"""Live monitor for replay engine progress. Run in a separate CMD window."""

import json
import sqlite3
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
JSONL = DATA_DIR / "replay_decisions.jsonl"
DB = DATA_DIR / "replay.db"
CHECKPOINT = DATA_DIR / "xauusd_m15_20240101_20260308.checkpoint.json"
TARGET = 2000


def get_stats():
    # Decision count from JSONL
    decisions = 0
    last_line = None
    if JSONL.exists():
        with open(JSONL) as f:
            for line in f:
                decisions += 1
                last_line = line.strip()

    # Parse last decision
    last = {}
    if last_line:
        try:
            last = json.loads(last_line)
        except Exception:
            pass

    # Trade count from DB
    trades = 0
    total_pnl = 0.0
    wins = 0
    if DB.exists():
        try:
            conn = sqlite3.connect(DB)
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(pnl),0), "
                "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) "
                "FROM episodic_memory"
            ).fetchone()
            trades, total_pnl, wins = row[0], row[1], row[2] or 0
            conn.close()
        except Exception:
            pass

    # Checkpoint
    cp = {}
    if CHECKPOINT.exists():
        try:
            cp = json.loads(CHECKPOINT.read_text())
        except Exception:
            pass

    return decisions, last, trades, total_pnl, wins, cp


def main():
    print("=" * 60)
    print("  REPLAY ENGINE MONITOR — Ctrl+C to exit")
    print("=" * 60)
    start_time = time.time()
    prev_decisions = 0

    while True:
        decisions, last, trades, total_pnl, wins, cp = get_stats()
        pct = decisions / TARGET * 100 if TARGET else 0
        elapsed = time.time() - start_time

        # Speed calc
        speed = 0
        eta_str = "calculating..."
        if decisions > prev_decisions and elapsed > 5:
            speed = decisions / elapsed
            remaining = TARGET - decisions
            if speed > 0:
                eta_sec = remaining / speed
                eta_min = int(eta_sec // 60)
                eta_str = f"{eta_min}m {int(eta_sec % 60)}s"

        # Progress bar
        bar_len = 30
        filled = int(bar_len * pct / 100)
        bar = "█" * filled + "░" * (bar_len - filled)

        # Last decision info
        last_ts = last.get("timestamp", "?")
        last_dec = last.get("decision", "?")
        last_eq = last.get("equity", "?")
        last_conf = last.get("confidence", "?")
        last_strat = last.get("strategy", "?")

        win_rate = (wins / trades * 100) if trades > 0 else 0

        print(f"\r\033[K", end="")  # clear line
        print(f"\n\033[K  [{bar}] {decisions}/{TARGET} ({pct:.1f}%)")
        print(f"\033[K  Speed: {speed:.1f} dec/s | ETA: {eta_str}")
        print(f"\033[K  Trades: {trades} | Win rate: {win_rate:.0f}% | PnL: ${total_pnl:+.2f} | Equity: {last_eq}")
        print(f"\033[K  Last: {last_ts} | {last_dec} ({last_strat}) conf={last_conf}")
        print(f"\033[K", end="")
        # Move cursor up for overwrite
        print(f"\033[5A", end="", flush=True)

        if decisions >= TARGET:
            print(f"\n\n\n\n\n\n  ✅ DONE! {decisions} decisions completed.")
            break

        prev_decisions = decisions
        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Stopped.")
