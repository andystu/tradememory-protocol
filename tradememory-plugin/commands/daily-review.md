---
description: Run a daily reflection on recent trades and behavioral patterns
argument-hint: "[date or 'today']"
---

# Daily Review

Trigger an AI-powered reflection on recent trading activity. Analyzes trades, identifies behavioral patterns, updates affective state, and produces actionable insights.

## Workflow

### Step 1: Determine Review Period

If a date is provided, review that day's trades. Default: review all trades since last reflection.

### Step 2: Gather Data

Load the `trading-memory` skill context, then:

1. Use `get_strategy_performance` to pull recent trade stats
2. Use `get_behavioral_analysis` to check behavioral drift
3. Use `get_agent_state` to read current affective state
4. Use `recall_memories` with recent context to surface relevant patterns

### Step 3: Analyze Patterns

The reflection should cover:

**Trade Execution Quality**
- Did entries match the strategy rules? Or were they impulsive?
- Were stop losses honored? Any manual overrides?
- Position sizing: consistent with risk rules or erratic?

**Behavioral Drift Detection**
- Disposition effect: cutting winners, holding losers?
- Revenge trading: increased size after losses?
- Overtrading: more trades than the strategy signals justify?
- Session discipline: trading outside designated sessions?

**Strategy Performance**
- Which strategies fired today?
- Win/loss breakdown per strategy
- Any strategy consistently underperforming?

### Step 4: Update Affective State

Based on the review, the affective state should be recalibrated:
- Confidence: up after good execution, down after poor discipline
- Risk appetite: reduce after drawdown, normalize after recovery
- Streak awareness: flag tilt risk after consecutive losses

### Step 5: Produce Report

Structure:

```
## Daily Review — [Date]

### Summary
- Trades today: N (W wins, L losses)
- P&L: $XXX
- Best: [trade details]
- Worst: [trade details]

### Behavioral Check
- Disposition ratio: X.X (target < 1.0)
- Hold time balance: [OK / Winners cut short / Losers held too long]
- Position sizing: [Consistent / Erratic]

### Insights
1. [Specific, data-backed observation]
2. [Specific, data-backed observation]

### Tomorrow's Focus
- [One concrete action item based on today's data]
```

## Important Notes

- Requires trades in the database. If no recent trades, report "no activity" instead of generating fluff.
- LLM reflection requires `ANTHROPIC_API_KEY`. Without it, uses rule-based analysis (still useful, less nuanced).
- Be honest. If performance is bad, say so. No sugar-coating.

## Example

```
User: /daily-review today
```
