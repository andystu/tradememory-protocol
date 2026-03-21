#!/usr/bin/env python3
"""Phase 15 Exp 4a: Grid Walk-Forward Optimization (WFO) Baseline.

Timeline: 2020-01 → 2026-03 (BTCUSDT 1H via BinanceDataSource)
IS window: 3 months, OOS window: 1 month, slide by 3 months.

Four arms:
  Arm G  — Grid WFO with decay detection + re-evolution
  Ctrl A — Static Strategy E (2024 frozen)
  Ctrl B — Buy & Hold
  Ctrl C — Random (pick random grid params every 3 months)

Grid: 19,200 combinations per re-evolution.
DSR gate applied to Arm G only.

Output: validation/grid_wfo_results.json with per-regime-period OOS Sharpe.

Usage:
    cd C:/Users/johns/projects/tradememory-protocol
    python scripts/research/run_grid_wfo.py
"""

import asyncio
import json
import math
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))  # scripts/

from tradememory.data.binance import BinanceDataSource
from tradememory.data.context_builder import ContextConfig
from tradememory.data.models import OHLCV, OHLCVSeries, Timeframe
from tradememory.evolution.backtester import _compute_fitness
from tradememory.evolution.models import CandidatePattern, FitnessMetrics
from tradememory.evolution.re_evolution import (
    GridSearchSpace,
    ReEvolutionConfig,
    ReEvolutionPipeline,
    build_grid_pattern,
    generate_grid,
)
from tradememory.evolution.regime_detector import (
    DecayAssessment,
    RegimeDecayDetector,
    RegimeDetectorConfig,
    TradeResult,
)
from tradememory.evolution.statistical_gates import deflated_sharpe_ratio
from tradememory.evolution.strategy_registry import StrategyRegistry

from run_real_baseline import (
    fast_backtest,
    precompute_atrs,
    precompute_contexts,
)
from run_walk_forward import month_boundaries, slice_bars_by_date
from strategy_definitions import build_strategy_e


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def backtest_on_window(
    bars: List[OHLCV],
    contexts: list,
    atrs: list,
    pattern: CandidatePattern,
    start_idx: int,
    end_idx: int,
    timeframe: str = "1h",
    annualize: bool = True,
) -> FitnessMetrics:
    """Run fast_backtest on a sub-window."""
    return fast_backtest(
        bars[start_idx:end_idx],
        contexts[start_idx:end_idx],
        atrs[start_idx:end_idx],
        pattern,
        timeframe=timeframe,
        annualize=annualize,
    )


def compute_buy_and_hold_sharpe(
    bars: List[OHLCV],
    start_idx: int,
    end_idx: int,
) -> float:
    """Compute buy & hold raw Sharpe on a window of bars (no annualization)."""
    window = bars[start_idx:end_idx]
    if len(window) < 5:
        return 0.0
    # Compute bar-by-bar returns
    returns = []
    for i in range(1, len(window)):
        if window[i - 1].close > 0:
            returns.append(
                (window[i].close - window[i - 1].close) / window[i - 1].close
            )
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(var_r) if var_r > 0 else 0
    if std_r == 0:
        return 0.0
    return round(mean_r / std_r, 4)


def pick_random_grid_pattern(seed: int) -> CandidatePattern:
    """Pick a random grid candidate given a seed."""
    rng = random.Random(seed)
    space = GridSearchSpace()
    return build_grid_pattern(
        hour_utc=rng.choice(space.hour_utc),
        direction=rng.choice(space.direction),
        trend_threshold=rng.choice(space.trend_12h_pct_threshold),
        sl_atr=rng.choice(space.sl_atr),
        tp_atr=rng.choice(space.tp_atr),
        max_holding_bars=rng.choice(space.max_holding_bars),
    )


# ────────────────────────────────────────────────────────────────
# Main experiment
# ────────────────────────────────────────────────────────────────

async def main():
    print("=" * 70)
    print("Phase 15 Exp 4a: Grid WFO Baseline")
    print("=" * 70)

    # --- Config ---
    data_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    data_end = datetime(2026, 3, 1, tzinfo=timezone.utc)
    is_months = 3
    oos_months = 3  # deploy for 3 months, then re-check
    total_months = (data_end.year - data_start.year) * 12 + (data_end.month - data_start.month)

    # --- Step 1: Fetch data ---
    print(f"\n[1/5] Fetching BTCUSDT 1H data ({data_start.date()} to {data_end.date()})...")
    binance = BinanceDataSource()
    try:
        series = await binance.fetch_ohlcv(
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            start=data_start,
            end=data_end,
        )
    finally:
        await binance.close()

    bars = series.bars
    print(f"  Bars: {series.count}")
    print(f"  Period: {series.start} -> {series.end}")
    if bars:
        print(f"  First close: ${bars[0].close:,.0f}, Last close: ${bars[-1].close:,.0f}")

    # --- Step 2: Precompute ---
    print("\n[2/5] Precomputing MarketContext + ATR...")
    t0 = time.time()
    contexts = precompute_contexts(series)
    atrs = precompute_atrs(bars)
    print(f"  Done in {time.time() - t0:.1f}s")

    # --- Step 3: Build regime periods ---
    # Each period: IS = 3 months, OOS = 3 months
    # First period: IS [2020-01, 2020-04], OOS [2020-04, 2020-07]
    # Second period: IS [2020-04, 2020-07], OOS [2020-07, 2020-10]
    # Slide by 3 months each time
    print("\n[3/5] Building regime periods...")
    boundaries = month_boundaries(2020, 1, total_months)

    periods = []
    step = oos_months  # slide by OOS length
    i = 0
    while i + is_months + oos_months <= len(boundaries) - 1:
        is_start = boundaries[i]
        is_end = boundaries[i + is_months]
        oos_start = is_end
        oos_end_idx = i + is_months + oos_months
        if oos_end_idx >= len(boundaries):
            break
        oos_end = boundaries[oos_end_idx]
        periods.append({
            "id": len(periods) + 1,
            "is_start": is_start,
            "is_end": is_end,
            "oos_start": oos_start,
            "oos_end": oos_end,
        })
        i += step

    print(f"  {len(periods)} regime periods (IS={is_months}mo, OOS={oos_months}mo)")
    for p in periods:
        print(f"    P{p['id']}: IS {p['is_start'].strftime('%Y-%m')} → {p['is_end'].strftime('%Y-%m')}, "
              f"OOS {p['oos_start'].strftime('%Y-%m')} → {p['oos_end'].strftime('%Y-%m')}")

    # --- Step 4: Run all four arms ---
    print("\n[4/5] Running 4 arms across all periods...")

    # Strategy E (Control A) — frozen
    strategy_e = build_strategy_e()

    # Re-evolution pipeline config — use smaller grid for feasibility
    # Full 19200 takes ~minutes per period; we keep it for scientific rigor
    grid_space = GridSearchSpace()
    reevo_config = ReEvolutionConfig(
        min_is_trades=5,
        min_is_sharpe=0.0,
        min_oos_trades=3,
        top_n_for_oos=20,
    )

    # Wrapper for pipeline's backtest_fn
    def pipeline_backtest(b, c, a, pattern, tf="1h"):
        return fast_backtest(b, c, a, pattern, timeframe=tf, annualize=False)

    registry = StrategyRegistry()
    random_seed_base = 42

    arm_results: Dict[str, List[Dict[str, Any]]] = {
        "arm_g": [],
        "ctrl_a": [],
        "ctrl_b": [],
        "ctrl_c": [],
    }
    dsr_gate_results = []

    for p in periods:
        pid = p["id"]
        print(f"\n  --- Period {pid}/{len(periods)} ---")

        # Get bar indices for IS and OOS
        _, is_s, is_e = slice_bars_by_date(bars, p["is_start"], p["is_end"])
        _, oos_s, oos_e = slice_bars_by_date(bars, p["oos_start"], p["oos_end"])

        if is_e - is_s < 30 or oos_e - oos_s < 10:
            print(f"    Skipping: not enough bars (IS={is_e - is_s}, OOS={oos_e - oos_s})")
            continue

        is_label = f"{p['is_start'].strftime('%Y-%m')} to {p['is_end'].strftime('%Y-%m')}"
        oos_label = f"{p['oos_start'].strftime('%Y-%m')} to {p['oos_end'].strftime('%Y-%m')}"

        # ── Arm G: Grid WFO with re-evolution ──
        print(f"    Arm G: Grid re-evolution ({grid_space.total_combinations} combos)...", flush=True)
        t_arm = time.time()
        pipeline = ReEvolutionPipeline(
            backtest_fn=pipeline_backtest,
            config=reevo_config,
            grid_space=grid_space,
        )
        reevo_result = pipeline.run(
            is_bars=bars[is_s:is_e],
            is_contexts=contexts[is_s:is_e],
            is_atrs=atrs[is_s:is_e],
            oos_bars=bars[oos_s:oos_e],
            oos_contexts=contexts[oos_s:oos_e],
            oos_atrs=atrs[oos_s:oos_e],
            registry=registry,
            version_id=f"V{pid}",
            metadata={"is_period": is_label, "oos_period": oos_label},
        )

        # If DSR gate passed and we have a best candidate, use its OOS fitness
        # Otherwise deploy nothing (cash position) — Sharpe = 0
        if reevo_result.best_candidate and reevo_result.passed_dsr_gate:
            arm_g_sharpe = reevo_result.best_candidate.oos_fitness.sharpe_ratio
            arm_g_trades = reevo_result.best_candidate.oos_fitness.trade_count
            arm_g_pnl = reevo_result.best_candidate.oos_fitness.total_pnl
        else:
            arm_g_sharpe = 0.0
            arm_g_trades = 0
            arm_g_pnl = 0.0

        arm_g_time = time.time() - t_arm
        print(f"      Sharpe={arm_g_sharpe:.4f}, trades={arm_g_trades}, "
              f"DSR={reevo_result.dsr or 0:.4f}, gate={'PASS' if reevo_result.passed_dsr_gate else 'FAIL'} "
              f"({arm_g_time:.1f}s)")

        dsr_gate_results.append({
            "period": pid,
            "passed": reevo_result.passed_dsr_gate,
            "dsr": reevo_result.dsr,
            "dsr_pvalue": reevo_result.dsr_pvalue,
            "num_tested": reevo_result.num_tested,
            "num_viable": reevo_result.num_viable,
        })

        arm_results["arm_g"].append({
            "period": pid,
            "is_period": is_label,
            "oos_period": oos_label,
            "oos_sharpe": arm_g_sharpe,
            "oos_trades": arm_g_trades,
            "oos_pnl": arm_g_pnl,
            "dsr": reevo_result.dsr,
            "dsr_pvalue": reevo_result.dsr_pvalue,
            "passed_dsr": reevo_result.passed_dsr_gate,
            "num_viable": reevo_result.num_viable,
        })

        # ── Control A: Static Strategy E ──
        ctrl_a_metrics = backtest_on_window(
            bars, contexts, atrs, strategy_e, oos_s, oos_e, annualize=False
        )
        arm_results["ctrl_a"].append({
            "period": pid,
            "oos_period": oos_label,
            "oos_sharpe": ctrl_a_metrics.sharpe_ratio,
            "oos_trades": ctrl_a_metrics.trade_count,
            "oos_pnl": ctrl_a_metrics.total_pnl,
        })
        print(f"    Ctrl A (Strategy E): Sharpe={ctrl_a_metrics.sharpe_ratio:.4f}, "
              f"trades={ctrl_a_metrics.trade_count}")

        # ── Control B: Buy & Hold ──
        bh_sharpe = compute_buy_and_hold_sharpe(bars, oos_s, oos_e)
        arm_results["ctrl_b"].append({
            "period": pid,
            "oos_period": oos_label,
            "oos_sharpe": bh_sharpe,
        })
        print(f"    Ctrl B (Buy&Hold): Sharpe={bh_sharpe:.4f}")

        # ── Control C: Random ──
        ctrl_c_pattern = pick_random_grid_pattern(seed=random_seed_base + pid)
        ctrl_c_metrics = backtest_on_window(
            bars, contexts, atrs, ctrl_c_pattern, oos_s, oos_e, annualize=False
        )
        arm_results["ctrl_c"].append({
            "period": pid,
            "oos_period": oos_label,
            "oos_sharpe": ctrl_c_metrics.sharpe_ratio,
            "oos_trades": ctrl_c_metrics.trade_count,
            "oos_pnl": ctrl_c_metrics.total_pnl,
        })
        print(f"    Ctrl C (Random): Sharpe={ctrl_c_metrics.sharpe_ratio:.4f}, "
              f"trades={ctrl_c_metrics.trade_count}")

    # --- Step 5: Statistical analysis ---
    print("\n[5/5] Statistical analysis...")
    n_periods = len(arm_results["arm_g"])
    if n_periods == 0:
        print("  No periods completed!")
        return

    # Extract OOS Sharpe arrays
    g_sharpes = [r["oos_sharpe"] for r in arm_results["arm_g"]]
    a_sharpes = [r["oos_sharpe"] for r in arm_results["ctrl_a"]]
    b_sharpes = [r["oos_sharpe"] for r in arm_results["ctrl_b"]]
    c_sharpes = [r["oos_sharpe"] for r in arm_results["ctrl_c"]]

    # Arm G vs Control A: win rate
    g_beats_a = sum(1 for g, a in zip(g_sharpes, a_sharpes) if g > a)
    g_beats_c = sum(1 for g, c in zip(g_sharpes, c_sharpes) if g > c)

    # Wilcoxon signed-rank test (pure Python implementation)
    def wilcoxon_signed_rank(x: List[float], y: List[float]) -> Tuple[float, float]:
        """Simple Wilcoxon signed-rank test. Returns (statistic, p_value_approx)."""
        diffs = [xi - yi for xi, yi in zip(x, y) if abs(xi - yi) > 1e-10]
        n = len(diffs)
        if n < 6:
            return 0.0, 1.0  # not enough data

        # Rank absolute differences
        abs_diffs = [(abs(d), i) for i, d in enumerate(diffs)]
        abs_diffs.sort(key=lambda t: t[0])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n and abs(abs_diffs[j][0] - abs_diffs[i][0]) < 1e-10:
                j += 1
            avg_rank = (i + j + 1) / 2  # 1-indexed average rank for ties
            for k in range(i, j):
                ranks[abs_diffs[k][1]] = avg_rank
            i = j

        # W+ = sum of ranks for positive differences
        w_plus = sum(ranks[i] for i in range(n) if diffs[i] > 0)
        w_minus = sum(ranks[i] for i in range(n) if diffs[i] < 0)
        w = min(w_plus, w_minus)

        # Normal approximation for p-value
        mean_w = n * (n + 1) / 4
        std_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
        if std_w == 0:
            return w, 1.0
        z = (w - mean_w) / std_w
        # Two-tailed p-value from normal CDF
        p = 2 * (1 - _norm_cdf(abs(z)))
        return w, round(p, 6)

    def _norm_cdf(x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    w_ga, p_ga = wilcoxon_signed_rank(g_sharpes, a_sharpes)
    w_gc, p_gc = wilcoxon_signed_rank(g_sharpes, c_sharpes)

    # DSR gate survive rate
    dsr_passed = sum(1 for d in dsr_gate_results if d["passed"])
    dsr_survive_rate = dsr_passed / len(dsr_gate_results) if dsr_gate_results else 0

    # --- Print results ---
    print("\n" + "=" * 70)
    print("RESULTS: Grid WFO Baseline (Exp 4a)")
    print("=" * 70)

    print(f"\nPeriods: {n_periods}")
    print(f"Grid space: {GridSearchSpace().total_combinations} combinations/re-evolution")
    print(f"Cumulative trials: {registry.cumulative_trials}")

    print(f"\n{'Period':<8} {'Arm G':>10} {'Ctrl A':>10} {'Ctrl B':>10} {'Ctrl C':>10} {'G>A':>5} {'G>C':>5} {'DSR':>8}")
    print("-" * 70)
    for i in range(n_periods):
        g = g_sharpes[i]
        a = a_sharpes[i]
        b = b_sharpes[i]
        c = c_sharpes[i]
        d = dsr_gate_results[i]
        print(f"P{i+1:<7} {g:>10.4f} {a:>10.4f} {b:>10.4f} {c:>10.4f} "
              f"{'Y' if g > a else 'N':>5} {'Y' if g > c else 'N':>5} "
              f"{'PASS' if d['passed'] else 'FAIL':>8}")

    print(f"\nMean Sharpe:")
    print(f"  Arm G:  {sum(g_sharpes)/n_periods:.4f}")
    print(f"  Ctrl A: {sum(a_sharpes)/n_periods:.4f}")
    print(f"  Ctrl B: {sum(b_sharpes)/n_periods:.4f}")
    print(f"  Ctrl C: {sum(c_sharpes)/n_periods:.4f}")

    print(f"\nArm G vs Ctrl A: wins {g_beats_a}/{n_periods} = {g_beats_a/n_periods:.1%}, Wilcoxon p={p_ga:.4f}")
    print(f"Arm G vs Ctrl C: wins {g_beats_c}/{n_periods} = {g_beats_c/n_periods:.1%}, Wilcoxon p={p_gc:.4f}")
    print(f"DSR gate survive rate: {dsr_passed}/{len(dsr_gate_results)} = {dsr_survive_rate:.1%}")

    # Layer 1 Gate criteria (for Sean's reference — NOT judging here)
    print(f"\n--- Layer 1 Gate Criteria (Sean judges) ---")
    print(f"  1. G Sharpe > A in >=60% periods: {g_beats_a/n_periods:.1%} {'PASS' if g_beats_a/n_periods >= 0.6 else 'FAIL'}, p={p_ga:.4f}")
    print(f"  2. G Sharpe > C in >=60% periods: {g_beats_c/n_periods:.1%} {'PASS' if g_beats_c/n_periods >= 0.6 else 'FAIL'}, p={p_gc:.4f}")
    print(f"  3. DSR survive >=50%: {dsr_survive_rate:.1%} {'PASS' if dsr_survive_rate >= 0.5 else 'FAIL'}")

    # --- Save results ---
    output = {
        "experiment": "Phase 15 Exp 4a: Grid WFO Baseline",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_period": f"{data_start.date()} to {data_end.date()}",
        "bars": series.count,
        "is_months": is_months,
        "oos_months": oos_months,
        "n_periods": n_periods,
        "grid_combinations": grid_space.total_combinations,
        "cumulative_trials": registry.cumulative_trials,
        "arms": {
            "arm_g": arm_results["arm_g"],
            "ctrl_a": arm_results["ctrl_a"],
            "ctrl_b": arm_results["ctrl_b"],
            "ctrl_c": arm_results["ctrl_c"],
        },
        "dsr_gate_results": dsr_gate_results,
        "statistics": {
            "mean_sharpe": {
                "arm_g": round(sum(g_sharpes) / n_periods, 4),
                "ctrl_a": round(sum(a_sharpes) / n_periods, 4),
                "ctrl_b": round(sum(b_sharpes) / n_periods, 4),
                "ctrl_c": round(sum(c_sharpes) / n_periods, 4),
            },
            "g_vs_a": {
                "win_rate": round(g_beats_a / n_periods, 4),
                "wilcoxon_p": p_ga,
                "n_periods": n_periods,
            },
            "g_vs_c": {
                "win_rate": round(g_beats_c / n_periods, 4),
                "wilcoxon_p": p_gc,
                "n_periods": n_periods,
            },
            "dsr_gate": {
                "passed": dsr_passed,
                "total": len(dsr_gate_results),
                "survive_rate": round(dsr_survive_rate, 4),
            },
        },
        "layer_1_gate": {
            "note": "Sean judges — DO NOT auto-evaluate",
            "criteria": {
                "g_gt_a_60pct": g_beats_a / n_periods >= 0.6,
                "g_gt_a_p_lt_010": p_ga < 0.10,
                "g_gt_c_60pct": g_beats_c / n_periods >= 0.6,
                "g_gt_c_p_lt_010": p_gc < 0.10,
                "dsr_survive_50pct": dsr_survive_rate >= 0.5,
            },
        },
        "registry_summary": registry.summary(),
    }

    out_dir = Path(__file__).parent.parent.parent / "validation"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "grid_wfo_results.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nResults saved to {out_path}")

    # Also save registry
    reg_path = out_dir / "grid_wfo_registry.json"
    registry._path = Path(reg_path)
    registry.save()
    print(f"Registry saved to {reg_path}")


if __name__ == "__main__":
    asyncio.run(main())
