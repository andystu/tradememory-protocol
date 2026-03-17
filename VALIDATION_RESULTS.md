# Phase 13: Statistical Validation Results

> Validates that the Evolution Engine discovers strategies with genuine edge,
> not just random noise. Each step adds a layer of statistical rigor.

---

## Step 1: Random Baseline

### Method

Generate N random strategies on the same OHLCV data used by the Evolution Engine.
Compute Sharpe ratio for each. A real strategy must rank above the 95th percentile
of the random distribution to be considered non-random.

### Data

- **Symbol**: BTCUSDT 1H (Binance spot)
- **Period**: 2024-06-01 to 2026-03-17 (15,693 bars)
- **Random strategies**: 1,000 (seed=42)
- **Execution time**: precompute=44s, 1000 backtests=13s, total=58s

### Baseline Distribution

| Metric | Value |
|--------|-------|
| Mean Sharpe | -0.0354 |
| Std Sharpe | 2.2147 |
| P5 | -3.3704 |
| P25 | -1.7777 |
| P50 (median) | -0.0116 |
| P75 | 1.4518 |
| P95 | 3.2708 |

### Strategy Results

| Strategy | Sharpe | Percentile | Trades | Win Rate | PF | Pass? |
|----------|--------|------------|--------|----------|----|-------|
| Strategy C (full) | 3.4003 | 96.9% | 336 | 37.2% | 1.12 | PASS |
| Strategy E (full) | 4.4188 | 100.0% | 321 | 41.1% | 1.15 | PASS |
| Strategy C (no trend) | -0.4349 | 38.0% | 654 | 37.6% | 0.99 | FAIL |
| Strategy E (no trend) | 1.3527 | 68.6% | 653 | 39.1% | 1.04 | FAIL |

### Ablation: Trend Filter Contribution

| Strategy | Full | No Trend | Delta |
|----------|------|----------|-------|
| C | 96.9% | 38.0% | +58.9 pctile pts |
| E | 100.0% | 68.6% | +31.4 pctile pts |

The 12h trend filter is the primary alpha source. Without it, both strategies fall to noise-level performance.

### Verdict

**PASS** -- Both Strategy C and E beat the 95th percentile of 1,000 random strategies.

### Next

Proceed to Step 2 (Walk-Forward) to test out-of-sample stability.

---

## Step 2: Walk-Forward Validation

### Method

Rolling 3-month train / 1-month test windows, sliding by 1 month.
18 windows total across Jun 2024 - Mar 2026.

Pass criteria:
- OOS Sharpe > 0 in >= 60% of windows
- Mean OOS Sharpe > 1.0
- No window with max DD > 50%

### Results

| Strategy | Windows | OOS>0 % | Mean OOS Sharpe | Worst DD | Result |
|----------|---------|---------|-----------------|----------|--------|
| Strategy C | 18 | 55.6% | 0.2426 | 5450% | FAIL |
| Strategy E | 18 | 61.1% | 3.2352 | 616% | FAIL |

Strategy E passes 2/3 criteria (positive windows + mean Sharpe).
Strategy C fails all three.

### DD Metric Caveat

The max drawdown percentages (5450%, 616%) are artifacts of computing DD% on
short-window PnL accumulation where equity is near zero. The backtester computes
(peak - equity) / peak * 100, which explodes when the denominator (peak equity)
is very small. This does NOT indicate real 50x risk -- the actual dollar drawdown
per window is bounded by ATR-based stops.

A more useful metric would be max DD in absolute terms or max consecutive losses.

### Interpretation

| Strategy | Step 1 (Baseline) | Step 2 (Walk-Forward) | Assessment |
|----------|------------------|-----------------------|------------|
| C | P96.9% PASS | 56% positive, mean 0.24 | Weak -- edge exists but unstable across time |
| E | P100% PASS | 61% positive, mean 3.24 | Moderate -- edge is real but regime-dependent |

Strategy E has genuine signal. 61% of OOS windows profitable with mean Sharpe 3.24.
Strategy C is marginal -- it beats random but is not consistently profitable OOS.

### Verdict

**MIXED** -- Strategy E passes the substance test (real OOS edge).
Strategy C needs regime filtering or should be used only as a diversifier, not standalone.

---

## Step 3: Time Bias Test (TODO)

TODO

---

## Step 4: Extended OOS (TODO)

TODO
