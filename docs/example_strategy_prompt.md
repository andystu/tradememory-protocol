# Example: Custom Strategy Prompt for Replay Engine

The Replay Engine supports pluggable strategy prompts via `ReplayConfig.system_prompt`.
This lets you provide your own trading rules without modifying the engine code.

## How It Works

```python
from tradememory.replay.models import ReplayConfig
from tradememory.replay.engine import ReplayEngine

MY_STRATEGY_PROMPT = """You are a trading agent using an SMA crossover strategy on M15 bars.

## Strategy: SMA Crossover
- When SMA(50) crosses ABOVE SMA(200), enter a BUY.
- When SMA(50) crosses BELOW SMA(200), enter a SELL.
- SL = 1.5 × ATR(14, M15) from entry.
- TP = 3.0 × ATR(14, M15) from entry (RR = 2.0).
- Max 1 position at a time.

## Rules
- If no crossover is happening, output HOLD with confidence = 0.
- If you have an open position, decide HOLD or CLOSE.
- Output JSON with: decision, strategy_used, entry_price, stop_loss, take_profit,
  confidence, market_observation, reasoning_trace.
- strategy_used must be: SMACrossover or NONE.
"""

config = ReplayConfig(
    data_path="data/my_instrument_m15.csv",
    system_prompt=MY_STRATEGY_PROMPT,
    llm_provider="deepseek",
    max_decisions=200,
)

engine = ReplayEngine(config)
summary = engine.run()
```

## Prompt Guidelines

1. **Be specific about entry/exit rules.** The LLM needs concrete conditions.
2. **Reference indicators by name.** The user prompt already includes ATR, RSI, SMA values.
3. **Define SL/TP as formulas.** Use ATR multiples for consistency.
4. **Specify strategy_used values.** The engine tracks per-strategy performance.
5. **Include JSON output format.** The engine parses `AgentDecision` from LLM output.

## Default Prompt

If no `system_prompt` is provided, the engine uses a generic placeholder that
outputs HOLD for all decisions. Override it with your own rules to get actual trades.
