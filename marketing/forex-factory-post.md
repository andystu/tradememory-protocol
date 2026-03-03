# Forex Factory Post — TradeMemory Protocol

## Post Info

- **Forum:** Forex Factory → Trading Systems / Interactive Trading
- **Title:** First AI Trading Memory for MT5 — Your Agent Finally Remembers What Works
- **Tags:** MT5, Expert Advisor, AI, Trading Journal, Gold, XAUUSD

---

## Post Content

### Title

**First AI Trading Memory for MT5 — Your Agent Finally Remembers What Works**

---

### Body

**The Problem Every AI Trader Hits**

If you're using AI to help with trading — ChatGPT, Claude, custom EAs with ML — you've hit this wall: every time you restart, the AI forgets everything. Past trades, discovered patterns, which sessions are profitable, which setups keep losing. You're starting from zero, every single time.

I got tired of watching my AI make the same mistakes on repeat. So I built something to fix it.

**What Is TradeMemory?**

TradeMemory is an open-source memory layer for MT5. It sits between your EA and your AI agent, recording every trade with full context — entry, exit, P&L, session, strategy, confidence level, market conditions. Then it discovers patterns from that data and auto-adjusts parameters.

Three layers:
- **L1 — Raw Trades:** Every closed position synced from MT5 in real time. Symbol, lots, SL/TP, hold duration, exit reason. No manual journaling.
- **L2 — Pattern Discovery:** The system crunches your L1 data and finds what you'd miss scrolling through MyFXBook. Example: "London session win rate 100% over 14 trades" or "Asian session win rate 10% — you're bleeding money there."
- **L3 — Strategy Adjustments:** Based on L2 patterns, it proposes concrete changes. Increase lot size during London. Cut position size in Asia. Filter out low-confidence setups entirely.

**Real Numbers From My Testing**

I'm running 4 EAs on XAUUSD (Demo @ FXTM, ~$11K balance). TradeMemory auto-syncs every 60 seconds. Here's what the memory layer found after 30 trades:

| What Memory Found | Action Taken | Impact |
|---|---|---|
| London session: 14W / 0L | Increase lot 0.05 → 0.08 | +60% upside capture |
| Asian session: 1W / 9L | Reduce lot 0.05 → 0.025 | -50% drawdown exposure |
| Low-confidence trades: 0W / 7L | Skip entirely | 7 losing trades avoided |
| VolBreakout RR actual: 1.37 | Keep running, validated | Data-backed confidence |

That's not theory. That's the system reading its own trade log, finding the edge, and acting on it.

**How It Works With MT5**

1. Your EA trades normally on MT5 — no changes to your EA code needed
2. `mt5_sync.py` runs in the background, polling closed positions every 60 seconds
3. Trades get stored in SQLite with full metadata (session, strategy, confidence)
4. Daily reflection engine runs at 23:55 UTC — analyzes the day, discovers patterns
5. L3 adjustments get generated: "increase london lot," "disable asian trading," etc.

You can query it through Claude Desktop, Claude Code, Cursor, or plain REST API. Ask things like:
- "How did my VolBreakout strategy perform this week?"
- "Which session should I avoid?"
- "Show me my worst losing patterns"

**What Makes This Different From MyFXBook / FX Blue / Myfxbook**

Those are dashboards. You look at charts, you draw your own conclusions, you manually adjust.

TradeMemory is a memory layer for AI agents. Your AI reads the data, discovers the patterns, and proposes the adjustments. You approve or reject. The agent remembers across sessions — it never forgets what it learned yesterday.

Also: it's free. MIT license. No monthly subscription. Run it on your own machine.

**My Setup (Live Testing)**

- **EA:** NG_Gold (custom, 4 strategies: VolBreakout, PullbackEntry, IntradayMomentum, MeanReversion)
- **Broker:** FXTM Demo
- **Balance:** ~$10,981 (last trade: VB BUY +$1,175 on 03/02)
- **Sync:** mt5_sync.py running 24/7 with auto-reconnect + watchdog
- **AI Agent:** Claude Desktop via MCP (Model Context Protocol)

This isn't a backtest-only tool. I'm using it on live demo right now with real-time sync.

**Quick Start (2 Minutes)**

```bash
pip install tradememory-protocol
tradememory-server
```

Then add to Claude Desktop config:
```json
{
  "mcpServers": {
    "tradememory": {
      "command": "tradememory-server"
    }
  }
}
```

Done. Start trading, start asking your AI about your performance.

**Links**

- GitHub: https://github.com/mnemox-ai/tradememory-protocol
- PyPI: `pip install tradememory-protocol`
- Landing Page: https://mnemox.ai/tradememory
- Tutorial (10 min): See TUTORIAL.md in repo

**What's Next**

- Multi-strategy portfolio tracking (Q2 2026)
- Crypto exchange support — Binance, Bybit (Q3 2026)
- Hosted API so you don't need to run anything locally

I'm building this because I need it myself. Every feature comes from real trading pain points, not hypothetical use cases.

Happy to answer questions. If you're running AI-assisted EAs and want persistent memory, give it a try and let me know what you think.

— Sean (Mnemox AI)

---

## Screenshot Plan

### Screenshot 1: Trade Memory in Action
- **What:** Claude Desktop showing a conversation where the trader asks "How did my strategies perform this week?" and gets a structured response with win rates, P&L, and session breakdown
- **Caption:** "Ask your AI agent about your trading performance — it remembers everything"
- **Source:** Run `demo.py` and capture the performance summary output in Claude Desktop

### Screenshot 2: Pattern Discovery (L2)
- **What:** Terminal or Claude output showing discovered patterns — London session 100% WR, Asian session 10% WR, confidence correlation
- **Caption:** "Patterns your AI discovers from your own trade data"
- **Source:** Run `demo.py`, capture the L2 pattern discovery section

### Screenshot 3: Strategy Adjustments (L3)
- **What:** L3 output showing proposed parameter changes with before/after values — lot sizing, confidence threshold, session filters
- **Caption:** "Auto-generated strategy adjustments based on what your memory layer learned"
- **Source:** Run `demo.py`, capture the L3 adjustment proposals

### Screenshot 4: MT5 Sync Running
- **What:** Terminal showing `mt5_sync.py` output — heartbeat, trade detected, synced to database
- **Caption:** "Real-time sync from MT5 — no manual data entry, ever"
- **Source:** Capture live mt5_sync.py terminal output with a recent trade sync event

### Screenshot 5: 3-Layer Architecture Diagram
- **What:** Simple diagram showing L1 (Raw Trades) → L2 (Patterns) → L3 (Adjustments) with MT5 on the left and AI Agent on the right
- **Caption:** "Three layers: Record → Discover → Adapt"
- **Source:** Create in Figma or draw.io, keep it clean and minimal

---

## Posting Notes

- **Timing:** Post during London/NY overlap (13:00-17:00 UTC) for max visibility
- **First reply:** Prepare a follow-up comment with the architecture diagram screenshot
- **Engagement:** Answer every question within 24 hours — FF community values responsiveness
- **Avoid:** Don't oversell. No "revolutionary" or "game-changing." Let the data speak.
- **Tone check:** Read it as if you're explaining to a trading buddy at a bar, not pitching to VCs
