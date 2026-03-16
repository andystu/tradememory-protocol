---
description: Recall similar past trades using outcome-weighted memory
argument-hint: "[market context or query]"
---

# Recall Similar Trades

Search your trading memory for past trades that match the current market context. Results are ranked by Outcome-Weighted Memory (OWM) score — winning trades in similar contexts surface first.

## Workflow

### Step 1: Define Query Context

If context is provided, use it. Otherwise ask:
- **Symbol**: What are you trading?
- **Market conditions**: Trending/ranging, volatility level, session
- **Strategy**: Which strategy are you considering?
- **Timeframe**: What timeframe are you analyzing?

### Step 2: Execute Recall

Use the `recall_memories` MCP tool:

```
recall_memories({
  query: "market context description",
  memory_types: ["episodic", "semantic", "procedural"],
  limit: 10
})
```

OWM scoring formula weights:
- **P&L outcome** (40%) — profitable trades score higher
- **Context similarity** (30%) — matching market conditions
- **Recency** (20%) — recent trades weighted more
- **Confidence calibration** (10%) — well-calibrated confidence scores weighted more

### Step 3: Present Results

For each recalled trade, show:
1. **OWM Score** — composite relevance score
2. **Trade summary** — symbol, direction, entry/exit, P&L
3. **Context match** — what made this trade similar
4. **Lesson** — the reflection/takeaway from that trade

### Step 4: Synthesize

After listing individual trades, provide:
- **Pattern summary**: What do the top results have in common?
- **Win rate** in similar contexts
- **Average P&L** in similar contexts
- **Recommendation**: Based on past experience, should you take this trade?

## Example

```
User: /recall ranging market, low volatility, Asian session, XAUUSD