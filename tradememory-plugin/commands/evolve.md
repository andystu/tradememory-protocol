---
description: Run the Evolution Engine to discover and validate trading strategies
argument-hint: "[symbol] [timeframe] [generations]"
---

# Evolve Strategy

Trigger the Evolution Engine to autonomously discover trading patterns from raw OHLCV data. The engine generates candidate strategies via LLM, backtests them vectorized, validates out-of-sample, and graduates survivors.

## Workflow

### Step 1: Configure Evolution

If parameters are provided, use them. Otherwise ask:
- **Symbol**: e.g., BTCUSDT, ETHUSDT (Binance pairs)
- **Timeframe**: 1h, 4h, 1d
- **Generations**: How many evolution cycles (default: 3)
- **Candidates per generation**: How many strategies to test (default: 10)
- **Data period**: How many days of historical data (default: 90)

### Step 2: Fetch Market Data

Use the `evolution_fetch_market_data` MCP tool:

```
evolution_fetch_market_data({
  symbol: "BTCUSDT",
  timeframe: "1h",
  days: 90
})
```

### Step 3: Discover Patterns

Use the `evolution_discover_patterns` MCP tool:

```
evolution_discover_patterns({
  symbol: "BTCUSDT",
  timeframe: "1h",
  num_patterns: 10
})
```

The LLM analyzes price data and generates candidate trading rules (entry/exit conditions, position sizing, stop loss).

### Step 4: Run Evolution Loop

Use the `evolution_evolve_strategy` MCP tool:

```
evolution_evolve_strategy({
  symbol: "BTCUSDT",
  timeframe: "1h",
  generations: 3,
  candidates_per_gen: 10
})
```

Each generation:
1. **Generate** — LLM creates N candidate strategies
2. **Backtest** — Vectorized backtesting with Sharpe, win rate, max drawdown
3. **Select** — Top performers survive, bottom eliminated
4. **Mutate** — LLM evolves survivors with variations
5. **Validate** — Out-of-sample test on held-out data

### Step 5: Report Results

For each graduated strategy:

| Metric | In-Sample | Out-of-Sample |
|--------|-----------|---------------|
| Sharpe Ratio | X.XX | X.XX |
| Win Rate | X% | X% |
| Max Drawdown | X% | X% |
| Total Return | X% | X% |
| # Trades | N | N |

Plus:
- Strategy description (entry/exit rules in plain language)
- Graveyard summary (why eliminated strategies failed)
- Confidence assessment (how robust is the OOS performance?)

## Important Notes

- Requires `ANTHROPIC_API_KEY` for LLM-powered pattern discovery
- Uses Binance public API for OHLCV data (no API key needed)
- Each generation takes 30-60 seconds depending on candidate count
- Always validate OOS before live trading — in-sample results are not reliable alone

## Example

```
User: /evolve BTCUSDT 1h 3
```
