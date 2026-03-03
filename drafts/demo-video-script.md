# TradeMemory Demo Video Script (2 min)

> Target: MQL5 Forum + r/algotrading + r/Forex
> Tone: Developer showing experiment, NOT salesman pitching product
> Language: English (subtitles可後加中文)
> Tool: OBS screen recording + terminal + optional voiceover

---

## [0:00-0:10] HOOK — The Problem (10 sec)

**Screen:** Split screen. Left: MT5 terminal showing a losing trade. Right: Same chart, same mistake, 3 weeks later.

**Text overlay / voiceover:**
> "Your EA made the same mistake again. Asian session, low liquidity, stopped out. For the third time this month."

---

## [0:10-0:25] The Concept (15 sec)

**Screen:** Terminal, type command to start demo.

```bash
cd tradememory-protocol
python demo.py
```

**Voiceover:**
> "What if your AI agent could remember every trade it ever made — and learn from its own mistakes?"

**Screen shows:** demo.py Step 1 output — 30 simulated XAUUSD trades streaming in.

```
Recording 30 XAUUSD trades over 7 simulated days...
[Day 1] Trade 1: VolBreakout LONG london  +$850  confidence=0.82
[Day 1] Trade 2: Pullback   SHORT asian   -$320  confidence=0.45
[Day 1] Trade 3: VolBreakout LONG london  +$620  confidence=0.78
...
```

---

## [0:25-0:50] L1 → L2: Pattern Discovery (25 sec)

**Screen:** demo.py Step 2 — pattern discovery runs.

**Voiceover:**
> "After 30 trades, TradeMemory discovers patterns automatically. No human intervention."

**Screen shows discovery output:**
```
=== L2 PATTERN DISCOVERY ===

SESSION WIN RATES:
  london:   85.7% (12/14 trades)  ← Best
  newyork:  58.3% (7/12 trades)
  asian:    25.0% (1/4 trades)    ← Worst

STRATEGY PERFORMANCE:
  VolBreakout: +$4,230  WR 78%  PF 2.31
  Pullback:    -$890    WR 38%  PF 0.67

CONFIDENCE CORRELATION:
  conf > 0.6:  WR 75%, avg +$380
  conf < 0.6:  WR 33%, avg -$210
```

**Text overlay:** "Pattern: Asian session = 25% win rate. Your EA keeps trading it anyway."

---

## [0:50-1:10] L3: Automatic Strategy Adjustments (20 sec)

**Screen:** demo.py Step 3 — L3 adjustments generated.

**Voiceover:**
> "TradeMemory doesn't just find patterns. It generates actionable adjustments."

**Screen shows:**
```
=== L3 STRATEGY ADJUSTMENTS ===

[ADJ-001] SESSION_REDUCE: asian
  → Reduce max lot by 50% during Asian session
  Reason: WR 25.0% (< 35% threshold), 4 trades
  Confidence: 0.85

[ADJ-002] STRATEGY_PREFER: VolBreakout
  → Set high priority
  Reason: avg PnL +$352, WR 78%, PF 2.31
  Confidence: 0.90

[ADJ-003] DIRECTION_RESTRICT: VolBreakout → BUY-only
  → Restrict to BUY direction
  Reason: BUY WR 87% vs BOTH WR 71% (delta > 15%)
  Confidence: 0.75
```

**Text overlay:** "Next session → AI agent automatically trades smaller lots in Asian, bigger in London."

---

## [1:10-1:30] Before vs After (20 sec)

**Screen:** demo.py Step 5 — Before/After comparison table.

**Voiceover:**
> "Here's the difference after 30 trades."

**Screen shows side-by-side:**
```
               STATELESS AGENT    MEMORY AGENT
Asian trades:  4 trades, -$890    2 trades, -$180 (lot halved)
London trades: 14 trades, +$3,200 14 trades, +$4,800 (lot increased)
Low-conf skip: 0 skipped          3 skipped (saved -$630)
Net PnL:       +$2,310            +$4,620
```

**Text overlay:** "+100% improvement. Same strategy. Same market. Just memory."

---

## [1:30-1:50] How It Works — Architecture (20 sec)

**Screen:** Simple architecture diagram (pre-made image or ASCII art).

```
MT5 Terminal
    ↓ trades
mcp-metatrader5-server (88★)  ← connection layer
    ↓ standardized data
TradeMemory Protocol (34★)    ← memory + intelligence
    ├── L1: Raw trade journal
    ├── L2: Pattern discovery (5 detectors)
    ├── L3: Strategy adjustments (5 rules)
    └── Adaptive Risk (Kelly + DD scaling)
    ↓ insights
Your AI Agent (Claude, GPT, etc.)
    ↓ smarter decisions
MT5 Terminal
```

**Voiceover:**
> "TradeMemory sits between your MT5 and your AI agent. It doesn't trade. It remembers. And it learns."

---

## [1:50-2:00] CTA — Soft Close (10 sec)

**Screen:** GitHub repo page (github.com/mnemox-ai/tradememory-protocol).

**Voiceover:**
> "Open source. MCP protocol. Works with Claude, GPT, any AI agent. Star it if you want to try it."

**Text overlay:**
```
github.com/mnemox-ai/tradememory-protocol
pip install tradememory-protocol

Open source · MCP Server · 4 tools · 181 tests
```

**DO NOT say:**
- "Limited spots" / "Founding member" (too salesy for dev community)
- "AI trading bot" (triggers scam detectors)
- "Guaranteed profits" (obvious)

**DO say:**
- "experiment" / "open source" / "feedback welcome"
- "works with any AI agent" (protocol, not product)

---

## Recording Instructions

### Setup
1. Terminal: Windows Terminal, dark theme, font size 16+
2. OBS: 1920x1080, 30fps, mkv → convert to mp4
3. Browser tab with GitHub repo open (for final shot)

### demo.py Modifications for Video
The current `demo.py` already has all 6 steps. For the video:
- Run `python demo.py` and let it stream naturally
- Pause at each step header for 2-3 seconds (let viewer read)
- If demo.py output is too fast, add `time.sleep()` between steps

### Post-production (optional)
- Add zoom-in on key numbers (Asian 25% WR, adjustment rules)
- Add text overlays at key moments
- Background music: lo-fi / ambient (not distracting)
- Subtitles: English → can add 繁中 for FB audience

### Where to Post
1. **MQL5 Forum** → "Coding & Libraries" or "General" section
   - Title: "Open-source experiment: AI memory layer for MT5 trading"
   - Tone: sharing, not selling
2. **r/algotrading** (250K members)
   - Title: "I built an MCP server that gives AI trading agents persistent memory [open source]"
3. **r/Forex** (1M members)
   - Title: "What if your EA could remember every trade and learn from mistakes? [open source experiment]"
4. **X/Twitter**
   - Tag @AnthropicAI @ModelContext #MCP #AlgoTrading
   - Short clip (30 sec cut of the before/after)

---

## Key Message Framework

**For developers (MQL5/Reddit):** "Protocol, not product. Plug it into your existing setup."
**For traders (r/Forex):** "Your EA keeps making the same mistakes. This remembers them."
**For AI community (X/Twitter):** "First MCP server for financial trading memory. Open source."
