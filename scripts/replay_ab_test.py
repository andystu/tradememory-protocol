"""A/B Test: Memory vs No-Memory Replay Comparison.

Runs two identical replay sessions on the same XAUUSD data:
  A) No memory recall (baseline)
  B) With memory recall (test)

Compares: win_rate, profit_factor, avg_confidence, strategy_distribution, cost.
Uses claude provider with claude-3-haiku-20240307 for cost efficiency.

Cost estimate: ~$1.2 total (200 decisions × 2 runs × ~$0.003/decision).

Usage:
    PYTHONPATH=. ANTHROPIC_API_KEY=sk-... python scripts/replay_ab_test.py
"""

import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from src.tradememory.replay.engine import ReplayEngine
from src.tradememory.replay.models import ReplayConfig

# ── Constants ──────────────────────────────────────────────────────
DATA_PATH = "data/xauusd_m15_20240101_20260308.csv"
MODEL = "claude-3-haiku-20240307"
PROVIDER = "claude"
MAX_DECISIONS = 200
SEED = 42

# Output paths
NO_MEM_DB = "data/replay_no_memory.db"
NO_MEM_JSONL = "data/replay_no_memory.jsonl"
WITH_MEM_DB = "data/replay_with_memory.db"
WITH_MEM_JSONL = "data/replay_with_memory.jsonl"


def clear_output_files(*paths: str) -> None:
    """Remove output files from previous runs."""
    for p in paths:
        path = Path(p)
        if path.exists():
            path.unlink()


def run_arm(
    label: str,
    use_memory: bool,
    db_path: str,
    log_path: str,
) -> Dict[str, Any]:
    """Run one arm of the A/B test."""
    # Set seed for reproducibility (affects any random choices in prompts/engine)
    random.seed(SEED)

    config = ReplayConfig(
        data_path=DATA_PATH,
        llm_provider=PROVIDER,
        llm_model=MODEL,
        api_key_env="ANTHROPIC_API_KEY",
        max_decisions=MAX_DECISIONS,
        use_memory_recall=use_memory,
        store_to_memory=True,
        db_path=db_path,
        log_path=log_path,
    )

    print(f"\n{'='*60}")
    print(f"  ARM {label}: {'WITH' if use_memory else 'WITHOUT'} memory")
    print(f"  Model: {MODEL} | Max decisions: {MAX_DECISIONS}")
    print(f"  DB: {db_path} | Log: {log_path}")
    print(f"{'='*60}\n")

    start = time.time()
    engine = ReplayEngine(config)
    summary = engine.run()
    elapsed = time.time() - start

    summary["elapsed_seconds"] = round(elapsed, 1)
    summary["label"] = label

    # Extract strategy distribution and avg confidence from JSONL
    strategy_counts: Counter = Counter()
    confidences: List[float] = []

    if Path(log_path).exists():
        with open(log_path) as f:
            for line in f:
                entry = json.loads(line)
                strategy = entry.get("strategy") or "NONE"
                strategy_counts[strategy] += 1
                conf = entry.get("confidence")
                if conf is not None:
                    confidences.append(conf)

    summary["strategy_distribution"] = dict(strategy_counts)
    summary["avg_confidence"] = (
        round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    )

    print(f"  Completed in {elapsed:.1f}s | Cost: ${summary['cost']:.4f}")
    print(f"  Trades: {summary['trades']} | Win rate: {summary['win_rate']:.2%}")
    return summary


def print_comparison(a: Dict[str, Any], b: Dict[str, Any]) -> None:
    """Print side-by-side comparison table."""
    print(f"\n{'='*70}")
    print("  A/B TEST RESULTS: Memory vs No-Memory")
    print(f"{'='*70}")

    rows = [
        ("Decisions", a["decisions"], b["decisions"], "d"),
        ("Trades", a["trades"], b["trades"], "d"),
        ("Win Rate", a["win_rate"], b["win_rate"], "%"),
        ("Profit Factor", a["profit_factor"], b["profit_factor"], ".2f"),
        ("Final Equity", a["equity"], b["equity"], ",.2f"),
        ("Avg Confidence", a["avg_confidence"], b["avg_confidence"], ".4f"),
        ("Memory Recalls", a["memory_recalls_count"], b["memory_recalls_count"], "d"),
        ("Tokens Used", a["tokens"], b["tokens"], ",d"),
        ("Cost (USD)", a["cost"], b["cost"], ".4f"),
        ("Time (sec)", a["elapsed_seconds"], b["elapsed_seconds"], ".1f"),
    ]

    header = f"  {'Metric':<20} {'No Memory':>15} {'With Memory':>15} {'Delta':>12}"
    print(header)
    print(f"  {'-'*62}")

    for label, val_a, val_b, fmt in rows:
        if fmt == "%":
            sa = f"{val_a:.2%}"
            sb = f"{val_b:.2%}"
            delta = val_b - val_a
            sd = f"{delta:+.2%}"
        elif fmt == "d":
            sa = f"{val_a:d}"
            sb = f"{val_b:d}"
            delta = val_b - val_a
            sd = f"{delta:+d}"
        elif fmt == ",d":
            sa = f"{val_a:,d}"
            sb = f"{val_b:,d}"
            delta = val_b - val_a
            sd = f"{delta:+,d}"
        elif fmt == ",.2f":
            sa = f"{val_a:,.2f}"
            sb = f"{val_b:,.2f}"
            delta = val_b - val_a
            sd = f"{delta:+,.2f}"
        else:
            sa = f"{val_a:{fmt}}"
            sb = f"{val_b:{fmt}}"
            delta = val_b - val_a
            sd = f"{delta:+{fmt}}"

        print(f"  {label:<20} {sa:>15} {sb:>15} {sd:>12}")

    # Strategy distribution comparison
    all_strategies = sorted(
        set(list(a["strategy_distribution"].keys()) + list(b["strategy_distribution"].keys()))
    )
    if all_strategies:
        print(f"\n  {'Strategy Distribution':<20} {'No Memory':>15} {'With Memory':>15} {'Delta':>12}")
        print(f"  {'-'*62}")
        for strat in all_strategies:
            ca = a["strategy_distribution"].get(strat, 0)
            cb = b["strategy_distribution"].get(strat, 0)
            d = cb - ca
            print(f"  {strat:<20} {ca:>15d} {cb:>15d} {d:>+12d}")

    print(f"\n  Model: {MODEL}")
    print(f"  Data: {DATA_PATH}")
    print(f"  Seed: {SEED}")
    print(f"{'='*70}\n")


def main() -> int:
    # Validate API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        return 1

    # Validate data file
    if not Path(DATA_PATH).exists():
        print(f"ERROR: Data file not found: {DATA_PATH}", file=sys.stderr)
        return 1

    # Clean previous outputs
    clear_output_files(NO_MEM_DB, NO_MEM_JSONL, WITH_MEM_DB, WITH_MEM_JSONL)

    # Also clean checkpoint files that might interfere
    checkpoint = Path(DATA_PATH).with_suffix(".checkpoint.json")
    if checkpoint.exists():
        # Don't delete — it belongs to the main replay. Engine creates its own.
        pass

    # Run A: No memory (baseline)
    summary_a = run_arm("A", use_memory=False, db_path=NO_MEM_DB, log_path=NO_MEM_JSONL)

    # Run B: With memory
    summary_b = run_arm("B", use_memory=True, db_path=WITH_MEM_DB, log_path=WITH_MEM_JSONL)

    # Compare
    print_comparison(summary_a, summary_b)

    # Save raw results
    results_path = "data/replay_ab_results.json"
    with open(results_path, "w") as f:
        json.dump({"no_memory": summary_a, "with_memory": summary_b}, f, indent=2, default=str)
    print(f"  Raw results saved to {results_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
