#!/usr/bin/env python3
"""Analyze trader behavior from CSV trade history.

Pure statistical analysis — no LLM. Outputs a markdown fingerprint report
with behavior patterns, strengths/weaknesses, and actionable recommendations.

Usage:
    cd C:/Users/johns/projects/tradememory-protocol
    python scripts/analyze_trader.py trades.csv
    python scripts/analyze_trader.py trades.csv --symbol XAUUSD
"""

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median, stdev

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- Column name detection ---

COLUMN_ALIASES = {
    "open_time": ["open_time", "entry_time", "open_date", "entry_date", "entry_datetime", "time"],
    "close_time": ["close_time", "exit_time", "close_date", "exit_date", "exit_datetime"],
    "side": ["side", "direction", "type", "order_type", "trade_type", "action"],
    "open_price": ["open_price", "entry_price", "price", "entry"],
    "close_price": ["close_price", "exit_price", "close", "exit"],
    "volume": ["volume", "lot", "lots", "size", "quantity", "qty", "amount"],
    "pnl": ["pnl", "profit", "net_profit", "realized_pnl", "pl", "p&l", "gain_loss"],
    "pnl_pct": ["pnl_pct", "pnl_percent", "return", "return_pct", "roi"],
    "symbol": ["symbol", "instrument", "pair", "ticker", "asset"],
    "strategy": ["strategy", "strategy_name", "system", "signal"],
}

TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%Y-%m-%d",
]

SESSION_RANGES = {
    "亞洲": (0, 8),    # UTC 00:00-08:00
    "倫敦": (8, 13),   # UTC 08:00-13:00
    "紐約": (13, 21),  # UTC 13:00-21:00
    "收盤": (21, 24),  # UTC 21:00-24:00
}

DAY_NAMES_ZH = {
    0: "週一", 1: "週二", 2: "週三",
    3: "週四", 4: "週五", 5: "週六", 6: "週日",
}


def detect_columns(headers: list[str]) -> dict[str, str | None]:
    """Map canonical field names to actual CSV column names."""
    mapping = {}
    lower_headers = {h.lower().strip(): h for h in headers}
    for canonical, aliases in COLUMN_ALIASES.items():
        mapping[canonical] = None
        for alias in aliases:
            if alias.lower() in lower_headers:
                mapping[canonical] = lower_headers[alias.lower()]
                break
    return mapping


def parse_time(value: str) -> datetime | None:
    """Try multiple datetime formats."""
    value = value.strip()
    if not value:
        return None
    for fmt in TIME_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Try unix timestamp
    try:
        ts = float(value)
        if ts > 1e12:
            ts /= 1000  # milliseconds
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (ValueError, OSError):
        pass
    return None


def parse_float(value: str) -> float | None:
    """Parse float, stripping currency symbols."""
    if not value or not value.strip():
        return None
    cleaned = value.strip().replace(",", "").replace("$", "").replace("€", "").replace("¥", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_side(value: str) -> str | None:
    """Normalize buy/sell direction."""
    if not value:
        return None
    v = value.strip().lower()
    if v in ("buy", "long", "b", "1"):
        return "long"
    if v in ("sell", "short", "s", "-1", "0"):
        return "short"
    return None


def get_session(hour: int) -> str:
    """Get trading session name from UTC hour."""
    for name, (start, end) in SESSION_RANGES.items():
        if start <= hour < end:
            return name
    return "收盤"


def confidence_stars(n: int) -> str:
    """Return star rating based on sample size."""
    if n >= 30:
        return "★★★"
    if n >= 15:
        return "★★☆"
    return "★☆☆"


def load_trades(csv_path: str, symbol_override: str | None = None) -> list[dict]:
    """Load and normalize trades from CSV."""
    path = Path(csv_path)
    if not path.exists():
        print(f"Error: file not found: {csv_path}")
        sys.exit(1)

    # Read CSV
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("Error: CSV has no headers")
            sys.exit(1)
        col_map = detect_columns(list(reader.fieldnames))
        raw_rows = list(reader)

    if not raw_rows:
        print("Error: CSV has no data rows")
        sys.exit(1)

    # Report detected columns
    detected = {k: v for k, v in col_map.items() if v is not None}
    missing = {k for k, v in col_map.items() if v is None}
    print(f"偵測到欄位: {detected}")
    if missing - {"pnl_pct", "strategy", "symbol", "volume"}:
        print(f"警告: 未偵測到欄位: {missing}")

    trades = []
    for row in raw_rows:
        t = {}

        # Times
        if col_map["open_time"]:
            t["open_time"] = parse_time(row[col_map["open_time"]])
        if col_map["close_time"]:
            t["close_time"] = parse_time(row[col_map["close_time"]])

        # Side
        if col_map["side"]:
            t["side"] = normalize_side(row[col_map["side"]])

        # Prices
        if col_map["open_price"]:
            t["open_price"] = parse_float(row[col_map["open_price"]])
        if col_map["close_price"]:
            t["close_price"] = parse_float(row[col_map["close_price"]])

        # Volume
        if col_map["volume"]:
            t["volume"] = parse_float(row[col_map["volume"]])

        # PnL
        if col_map["pnl"]:
            t["pnl"] = parse_float(row[col_map["pnl"]])

        # PnL pct
        if col_map["pnl_pct"]:
            t["pnl_pct"] = parse_float(row[col_map["pnl_pct"]])

        # Symbol
        if col_map["symbol"]:
            t["symbol"] = row[col_map["symbol"]].strip() if row[col_map["symbol"]] else None
        if symbol_override:
            t["symbol"] = symbol_override

        # Strategy
        if col_map["strategy"]:
            t["strategy"] = row[col_map["strategy"]].strip() if row[col_map["strategy"]] else None

        # Compute missing pnl_pct from prices
        if t.get("pnl_pct") is None and t.get("open_price") and t.get("close_price") and t.get("side"):
            op, cp = t["open_price"], t["close_price"]
            if op != 0:
                if t["side"] == "long":
                    t["pnl_pct"] = (cp - op) / op * 100
                else:
                    t["pnl_pct"] = (op - cp) / op * 100

        # Compute missing pnl from prices + volume (rough estimate)
        if t.get("pnl") is None and t.get("open_price") and t.get("close_price") and t.get("side"):
            op, cp = t["open_price"], t["close_price"]
            vol = t.get("volume", 1.0) or 1.0
            if t["side"] == "long":
                t["pnl"] = (cp - op) * vol
            else:
                t["pnl"] = (op - cp) * vol

        trades.append(t)

    # Sort by open_time if available
    if any(t.get("open_time") for t in trades):
        trades.sort(key=lambda x: x.get("open_time") or datetime.min.replace(tzinfo=timezone.utc))

    return trades


def compute_stats(trades: list[dict]) -> dict:
    """Compute all statistical metrics."""
    stats = {}
    n = len(trades)
    stats["total_trades"] = n

    # PnL stats
    pnls = [t["pnl"] for t in trades if t.get("pnl") is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    breakeven = [p for p in pnls if p == 0]

    stats["has_pnl"] = len(pnls) > 0
    if pnls:
        stats["total_pnl"] = sum(pnls)
        stats["avg_pnl"] = mean(pnls)
        stats["median_pnl"] = median(pnls)
        stats["win_count"] = len(wins)
        stats["loss_count"] = len(losses)
        stats["breakeven_count"] = len(breakeven)
        stats["win_rate"] = len(wins) / len(pnls) * 100 if pnls else 0
        stats["avg_win"] = mean(wins) if wins else 0
        stats["avg_loss"] = mean(losses) if losses else 0
        stats["best_trade"] = max(pnls)
        stats["worst_trade"] = min(pnls)
        stats["profit_factor"] = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")
        if len(pnls) > 1:
            stats["pnl_stdev"] = stdev(pnls)
        else:
            stats["pnl_stdev"] = 0
        # Expectancy
        stats["expectancy"] = stats["avg_pnl"]
        # Payoff ratio
        stats["payoff_ratio"] = abs(stats["avg_win"] / stats["avg_loss"]) if stats["avg_loss"] != 0 else float("inf")

    # Hold time
    hold_times = []
    for t in trades:
        if t.get("open_time") and t.get("close_time"):
            dt = t["close_time"] - t["open_time"]
            if dt.total_seconds() >= 0:
                hold_times.append(dt)
    stats["has_hold_time"] = len(hold_times) > 0
    if hold_times:
        secs = [h.total_seconds() for h in hold_times]
        stats["avg_hold_seconds"] = mean(secs)
        stats["median_hold_seconds"] = median(secs)
        stats["min_hold_seconds"] = min(secs)
        stats["max_hold_seconds"] = max(secs)

    # Max drawdown (sequential equity curve)
    if pnls:
        equity = 0
        peak = 0
        max_dd = 0
        dd_trades = []
        current_dd_start = 0
        for i, p in enumerate(pnls):
            equity += p
            if equity > peak:
                peak = equity
                current_dd_start = i
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
                dd_trades = (current_dd_start, i)
        stats["max_drawdown"] = max_dd
        stats["max_drawdown_trades"] = dd_trades

    # Session breakdown
    session_stats = defaultdict(lambda: {"pnls": [], "count": 0})
    for t in trades:
        hour = None
        if t.get("open_time"):
            hour = t["open_time"].hour
        if hour is not None and t.get("pnl") is not None:
            session = get_session(hour)
            session_stats[session]["pnls"].append(t["pnl"])
            session_stats[session]["count"] += 1
    stats["session_stats"] = {}
    for session_name in ["亞洲", "倫敦", "紐約", "收盤"]:
        s = session_stats[session_name]
        if s["count"] > 0:
            s_pnls = s["pnls"]
            s_wins = [p for p in s_pnls if p > 0]
            stats["session_stats"][session_name] = {
                "count": s["count"],
                "total_pnl": sum(s_pnls),
                "avg_pnl": mean(s_pnls),
                "win_rate": len(s_wins) / len(s_pnls) * 100,
            }

    # Day-of-week breakdown
    dow_stats = defaultdict(lambda: {"pnls": [], "count": 0})
    for t in trades:
        if t.get("open_time") and t.get("pnl") is not None:
            dow = t["open_time"].weekday()
            dow_stats[dow]["pnls"].append(t["pnl"])
            dow_stats[dow]["count"] += 1
    stats["dow_stats"] = {}
    for dow in range(7):
        d = dow_stats[dow]
        if d["count"] > 0:
            d_pnls = d["pnls"]
            d_wins = [p for p in d_pnls if p > 0]
            stats["dow_stats"][dow] = {
                "count": d["count"],
                "total_pnl": sum(d_pnls),
                "avg_pnl": mean(d_pnls),
                "win_rate": len(d_wins) / len(d_pnls) * 100,
            }

    # Streak analysis
    if pnls:
        streaks_win = []
        streaks_loss = []
        current_streak = 0
        streak_type = None
        for p in pnls:
            if p > 0:
                if streak_type == "win":
                    current_streak += 1
                else:
                    if streak_type == "loss" and current_streak > 0:
                        streaks_loss.append(current_streak)
                    current_streak = 1
                    streak_type = "win"
            elif p < 0:
                if streak_type == "loss":
                    current_streak += 1
                else:
                    if streak_type == "win" and current_streak > 0:
                        streaks_win.append(current_streak)
                    current_streak = 1
                    streak_type = "loss"
        # Close last streak
        if streak_type == "win" and current_streak > 0:
            streaks_win.append(current_streak)
        elif streak_type == "loss" and current_streak > 0:
            streaks_loss.append(current_streak)

        stats["max_win_streak"] = max(streaks_win) if streaks_win else 0
        stats["max_loss_streak"] = max(streaks_loss) if streaks_loss else 0
        stats["avg_win_streak"] = mean(streaks_win) if streaks_win else 0
        stats["avg_loss_streak"] = mean(streaks_loss) if streaks_loss else 0

    # Post-loss behavior: does trader increase size after losses?
    post_loss_behavior = {"size_after_loss": [], "size_after_win": [], "size_normal": []}
    for i in range(1, len(trades)):
        prev_pnl = trades[i - 1].get("pnl")
        curr_vol = trades[i].get("volume")
        if prev_pnl is not None and curr_vol is not None:
            if prev_pnl < 0:
                post_loss_behavior["size_after_loss"].append(curr_vol)
            elif prev_pnl > 0:
                post_loss_behavior["size_after_win"].append(curr_vol)
    stats["post_loss_behavior"] = post_loss_behavior

    # Side breakdown
    side_stats = defaultdict(lambda: {"pnls": [], "count": 0})
    for t in trades:
        if t.get("side") and t.get("pnl") is not None:
            side_stats[t["side"]]["pnls"].append(t["pnl"])
            side_stats[t["side"]]["count"] += 1
    stats["side_stats"] = {}
    for side_name in ["long", "short"]:
        s = side_stats[side_name]
        if s["count"] > 0:
            s_pnls = s["pnls"]
            s_wins = [p for p in s_pnls if p > 0]
            stats["side_stats"][side_name] = {
                "count": s["count"],
                "total_pnl": sum(s_pnls),
                "avg_pnl": mean(s_pnls),
                "win_rate": len(s_wins) / len(s_pnls) * 100,
            }

    return stats


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.0f}秒"
    if seconds < 3600:
        return f"{seconds / 60:.1f}分"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}時"
    return f"{seconds / 86400:.1f}天"


def format_pnl(value: float) -> str:
    """Format PnL with sign."""
    if value >= 0:
        return f"+${value:,.2f}"
    return f"-${abs(value):,.2f}"


def generate_report(trades: list[dict], stats: dict, symbol: str) -> str:
    """Generate markdown report in Traditional Chinese."""
    lines = []
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    lines.append(f"# 交易者指紋分析 — {symbol}")
    lines.append(f"")
    lines.append(f"> 生成時間: {now.strftime('%Y-%m-%d %H:%M UTC')} | 純統計分析（無 LLM）")
    lines.append(f"")

    # --- Section 1: Trading Overview ---
    lines.append("## 一、交易概覽")
    lines.append("")

    lines.append("| 指標 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 總交易數 | {stats['total_trades']} |")

    if stats.get("has_pnl"):
        lines.append(f"| 總損益 | {format_pnl(stats['total_pnl'])} |")
        lines.append(f"| 勝率 | {stats['win_rate']:.1f}% ({stats['win_count']}勝 / {stats['loss_count']}敗 / {stats['breakeven_count']}平) |")
        lines.append(f"| 獲利因子 | {stats['profit_factor']:.2f} |")
        lines.append(f"| 期望值 | {format_pnl(stats['expectancy'])} |")
        lines.append(f"| 報酬/風險比 | {stats['payoff_ratio']:.2f} |")
        lines.append(f"| 平均獲利 | {format_pnl(stats['avg_win'])} |")
        lines.append(f"| 平均虧損 | {format_pnl(stats['avg_loss'])} |")
        lines.append(f"| 最佳單筆 | {format_pnl(stats['best_trade'])} |")
        lines.append(f"| 最差單筆 | {format_pnl(stats['worst_trade'])} |")
        lines.append(f"| 最大回撤 | ${stats['max_drawdown']:,.2f} |")
        if stats.get("pnl_stdev"):
            lines.append(f"| 損益標準差 | ${stats['pnl_stdev']:,.2f} |")

    if stats.get("has_hold_time"):
        lines.append(f"| 平均持倉時間 | {format_duration(stats['avg_hold_seconds'])} |")
        lines.append(f"| 中位數持倉時間 | {format_duration(stats['median_hold_seconds'])} |")
        lines.append(f"| 最短持倉 | {format_duration(stats['min_hold_seconds'])} |")
        lines.append(f"| 最長持倉 | {format_duration(stats['max_hold_seconds'])} |")

    # Side breakdown
    if stats.get("side_stats"):
        lines.append("")
        lines.append("### 方向分析")
        lines.append("")
        lines.append("| 方向 | 交易數 | 勝率 | 平均損益 | 總損益 |")
        lines.append("|------|--------|------|----------|--------|")
        for side_name, label in [("long", "做多"), ("short", "做空")]:
            if side_name in stats["side_stats"]:
                s = stats["side_stats"][side_name]
                lines.append(f"| {label} | {s['count']} | {s['win_rate']:.1f}% | {format_pnl(s['avg_pnl'])} | {format_pnl(s['total_pnl'])} |")

    lines.append("")

    # --- Section 2: Behavior Patterns ---
    lines.append("## 二、行為模式")
    lines.append("")

    # Session patterns
    if stats.get("session_stats"):
        lines.append("### 交易時段分佈")
        lines.append("")
        lines.append("| 時段 | 交易數 | 勝率 | 平均損益 | 總損益 | 信心度 |")
        lines.append("|------|--------|------|----------|--------|--------|")
        for session_name in ["亞洲", "倫敦", "紐約", "收盤"]:
            if session_name in stats["session_stats"]:
                s = stats["session_stats"][session_name]
                stars = confidence_stars(s["count"])
                lines.append(f"| {session_name} (UTC) | {s['count']} | {s['win_rate']:.1f}% | {format_pnl(s['avg_pnl'])} | {format_pnl(s['total_pnl'])} | {stars} |")
        lines.append("")

    # Day-of-week patterns
    if stats.get("dow_stats"):
        lines.append("### 星期分佈")
        lines.append("")
        lines.append("| 星期 | 交易數 | 勝率 | 平均損益 | 總損益 | 信心度 |")
        lines.append("|------|--------|------|----------|--------|--------|")
        for dow in range(7):
            if dow in stats["dow_stats"]:
                d = stats["dow_stats"][dow]
                stars = confidence_stars(d["count"])
                lines.append(f"| {DAY_NAMES_ZH[dow]} | {d['count']} | {d['win_rate']:.1f}% | {format_pnl(d['avg_pnl'])} | {format_pnl(d['total_pnl'])} | {stars} |")
        lines.append("")

    # Streak patterns
    if stats.get("has_pnl"):
        lines.append("### 連勝/連敗分析")
        lines.append("")
        lines.append(f"- 最長連勝: {stats.get('max_win_streak', 0)} 筆")
        lines.append(f"- 最長連敗: {stats.get('max_loss_streak', 0)} 筆")
        lines.append(f"- 平均連勝: {stats.get('avg_win_streak', 0):.1f} 筆")
        lines.append(f"- 平均連敗: {stats.get('avg_loss_streak', 0):.1f} 筆")
        lines.append("")

    # Post-loss behavior
    plb = stats.get("post_loss_behavior", {})
    size_after_loss = plb.get("size_after_loss", [])
    size_after_win = plb.get("size_after_win", [])
    if size_after_loss and size_after_win:
        avg_after_loss = mean(size_after_loss)
        avg_after_win = mean(size_after_win)
        lines.append("### 虧損後行為")
        lines.append("")
        lines.append(f"- 虧損後平均倉位: {avg_after_loss:.4f}")
        lines.append(f"- 獲利後平均倉位: {avg_after_win:.4f}")
        if avg_after_win > 0:
            ratio = avg_after_loss / avg_after_win
            if ratio > 1.15:
                lines.append(f"- **⚠️ 虧損後加碼傾向**: 虧損後倉位是獲利後的 {ratio:.2f}x（報復性交易風險）")
            elif ratio < 0.85:
                lines.append(f"- **縮手傾向**: 虧損後倉位是獲利後的 {ratio:.2f}x（可能過度保守）")
            else:
                lines.append(f"- **倉位穩定**: 虧損後/獲利後比例 {ratio:.2f}x（紀律良好）")
        n_plb = len(size_after_loss) + len(size_after_win)
        lines.append(f"- 信心度: {confidence_stars(n_plb)} (n={n_plb})")
        lines.append("")

    # --- Section 3: Strengths and Weaknesses ---
    lines.append("## 三、優勢與劣勢")
    lines.append("")

    if stats.get("session_stats"):
        # Best/worst sessions
        sessions_sorted = sorted(
            stats["session_stats"].items(),
            key=lambda x: x[1]["avg_pnl"],
            reverse=True,
        )
        if len(sessions_sorted) >= 2:
            best_s = sessions_sorted[0]
            worst_s = sessions_sorted[-1]
            lines.append(f"**最強時段**: {best_s[0]} — 平均 {format_pnl(best_s[1]['avg_pnl'])}/筆, 勝率 {best_s[1]['win_rate']:.1f}% (n={best_s[1]['count']})")
            lines.append("")
            lines.append(f"**最弱時段**: {worst_s[0]} — 平均 {format_pnl(worst_s[1]['avg_pnl'])}/筆, 勝率 {worst_s[1]['win_rate']:.1f}% (n={worst_s[1]['count']})")
            lines.append("")

    if stats.get("dow_stats"):
        # Best/worst days
        days_sorted = sorted(
            stats["dow_stats"].items(),
            key=lambda x: x[1]["avg_pnl"],
            reverse=True,
        )
        if len(days_sorted) >= 2:
            best_d = days_sorted[0]
            worst_d = days_sorted[-1]
            lines.append(f"**最強日**: {DAY_NAMES_ZH[best_d[0]]} — 平均 {format_pnl(best_d[1]['avg_pnl'])}/筆, 勝率 {best_d[1]['win_rate']:.1f}% (n={best_d[1]['count']})")
            lines.append("")
            lines.append(f"**最弱日**: {DAY_NAMES_ZH[worst_d[0]]} — 平均 {format_pnl(worst_d[1]['avg_pnl'])}/筆, 勝率 {worst_d[1]['win_rate']:.1f}% (n={worst_d[1]['count']})")
            lines.append("")

    # Consecutive loss behavior
    if stats.get("has_pnl"):
        max_loss_streak = stats.get("max_loss_streak", 0)
        if max_loss_streak >= 3:
            # Analyze PnL of trades right after streaks of 3+
            pnls = [t.get("pnl") for t in trades if t.get("pnl") is not None]
            post_streak_pnls = []
            streak = 0
            for i, p in enumerate(pnls):
                if p < 0:
                    streak += 1
                else:
                    if streak >= 3 and i < len(pnls):
                        post_streak_pnls.append(p)
                    streak = 0
            if post_streak_pnls:
                avg_post = mean(post_streak_pnls)
                lines.append(f"**連續 3+ 敗後表現**: 下一筆平均 {format_pnl(avg_post)} (n={len(post_streak_pnls)})")
                if avg_post > 0:
                    lines.append("  → 連敗後能回穩，心態控制尚可")
                else:
                    lines.append("  → ⚠️ 連敗後繼續虧損，可能有情緒交易問題")
                lines.append("")

    # --- Section 4: Specific Recommendations ---
    lines.append("## 四、具體建議")
    lines.append("")

    rec_num = 1

    if stats.get("session_stats"):
        sessions_sorted = sorted(
            stats["session_stats"].items(),
            key=lambda x: x[1]["avg_pnl"],
        )
        worst_s = sessions_sorted[0]
        if worst_s[1]["avg_pnl"] < 0 and worst_s[1]["count"] >= 5:
            lines.append(f"{rec_num}. **停止在{worst_s[0]}時段交易**（或縮減倉位 50%）— 該時段 {worst_s[1]['count']} 筆交易平均虧損 {format_pnl(worst_s[1]['avg_pnl'])}，總計 {format_pnl(worst_s[1]['total_pnl'])}")
            rec_num += 1

    if stats.get("dow_stats"):
        days_sorted = sorted(
            stats["dow_stats"].items(),
            key=lambda x: x[1]["avg_pnl"],
        )
        worst_d = days_sorted[0]
        if worst_d[1]["avg_pnl"] < 0 and worst_d[1]["count"] >= 3:
            lines.append(f"{rec_num}. **避開{DAY_NAMES_ZH[worst_d[0]]}**（或只用觀望模式）— {worst_d[1]['count']} 筆交易平均虧損 {format_pnl(worst_d[1]['avg_pnl'])}")
            rec_num += 1

    plb = stats.get("post_loss_behavior", {})
    sal = plb.get("size_after_loss", [])
    saw = plb.get("size_after_win", [])
    if sal and saw:
        avg_al = mean(sal)
        avg_aw = mean(saw)
        if avg_aw > 0 and avg_al / avg_aw > 1.15:
            lines.append(f"{rec_num}. **虧損後禁止加碼** — 設定規則：連虧 2 筆後，下一筆倉位不得超過前一筆。目前虧損後倉位增加 {(avg_al / avg_aw - 1) * 100:.0f}%")
            rec_num += 1

    if stats.get("has_pnl"):
        max_loss_streak = stats.get("max_loss_streak", 0)
        if max_loss_streak >= 4:
            lines.append(f"{rec_num}. **設定每日停損上限** — 最長連敗 {max_loss_streak} 筆，建議連虧 3 筆後當日停止交易")
            rec_num += 1

        if stats.get("win_rate", 0) < 40 and stats.get("payoff_ratio", 0) < 2:
            lines.append(f"{rec_num}. **勝率和報酬比同時偏低** — 勝率 {stats['win_rate']:.1f}% + 報酬比 {stats['payoff_ratio']:.2f}，建議重新檢視進場條件，或擴大止盈/縮小止損")
            rec_num += 1

        if stats.get("payoff_ratio", 0) < 1 and stats.get("win_rate", 0) < 60:
            lines.append(f"{rec_num}. **停損過大或停利太早** — 報酬比僅 {stats['payoff_ratio']:.2f}，平均獲利 {format_pnl(stats['avg_win'])} vs 平均虧損 {format_pnl(stats['avg_loss'])}。建議將停利設為停損的至少 1.5 倍")
            rec_num += 1

    if stats.get("has_hold_time"):
        avg_hold = stats["avg_hold_seconds"]
        min_hold = stats["min_hold_seconds"]
        if min_hold < 60:
            lines.append(f"{rec_num}. **存在閃電單** — 最短持倉僅 {format_duration(min_hold)}，可能是誤操作或情緒交易。建議設定最低持倉時間限制")
            rec_num += 1

    if stats.get("side_stats"):
        for side_name, label in [("long", "做多"), ("short", "做空")]:
            if side_name in stats["side_stats"]:
                s = stats["side_stats"][side_name]
                other = "short" if side_name == "long" else "long"
                if other in stats["side_stats"]:
                    o = stats["side_stats"][other]
                    if s["avg_pnl"] < 0 and o["avg_pnl"] > 0 and s["count"] >= 5:
                        other_label = "做空" if side_name == "long" else "做多"
                        lines.append(f"{rec_num}. **減少{label}交易** — {label} {s['count']} 筆平均 {format_pnl(s['avg_pnl'])}，{other_label}平均 {format_pnl(o['avg_pnl'])}。考慮只做{other_label}或{label}時縮減倉位")
                        rec_num += 1

    if rec_num == 1:
        lines.append("數據量不足以給出具體建議，建議累積至少 30 筆交易後再做分析。")

    lines.append("")

    # --- Section 5: AI Confidence Assessment ---
    lines.append("## 五、分析信心度評估")
    lines.append("")

    n = stats["total_trades"]
    lines.append(f"樣本數: **{n} 筆交易**")
    lines.append("")

    if n >= 100:
        lines.append("- 整體統計指標（勝率、獲利因子、期望值）: **高度可靠** ★★★")
    elif n >= 30:
        lines.append("- 整體統計指標（勝率、獲利因子、期望值）: **中度可靠** ★★☆")
    else:
        lines.append("- 整體統計指標（勝率、獲利因子、期望值）: **僅供參考** ★☆☆")

    # Session confidence
    if stats.get("session_stats"):
        for session_name, s in stats["session_stats"].items():
            stars = confidence_stars(s["count"])
            reliability = "高度可靠" if s["count"] >= 30 else "中度可靠" if s["count"] >= 15 else "需更多數據"
            lines.append(f"- {session_name}時段分析 (n={s['count']}): **{reliability}** {stars}")

    # Day confidence
    if stats.get("dow_stats"):
        low_n_days = [DAY_NAMES_ZH[d] for d, s in stats["dow_stats"].items() if s["count"] < 10]
        if low_n_days:
            lines.append(f"- ⚠️ 以下星期樣本數偏低，結論可能不穩定: {', '.join(low_n_days)}")

    # Post-loss behavior confidence
    plb = stats.get("post_loss_behavior", {})
    sal_n = len(plb.get("size_after_loss", []))
    if sal_n > 0:
        stars = confidence_stars(sal_n)
        lines.append(f"- 虧損後行為分析 (n={sal_n}): {stars}")

    lines.append("")
    lines.append("### 需要更多數據的結論")
    lines.append("")

    needs_more = []
    if n < 30:
        needs_more.append("所有結論都需要更多數據（建議至少 30 筆）")
    if stats.get("session_stats"):
        for session_name, s in stats["session_stats"].items():
            if s["count"] < 15:
                needs_more.append(f"{session_name}時段: 僅 {s['count']} 筆，勝率和平均損益可能波動大")
    if stats.get("max_loss_streak", 0) < 3:
        needs_more.append("連敗分析: 最長連敗不足 3 筆，無法判斷連敗後行為")

    if needs_more:
        for item in needs_more:
            lines.append(f"- {item}")
    else:
        lines.append("- 目前所有分析均有足夠樣本支撐")

    lines.append("")
    lines.append("---")
    lines.append(f"*由 TradeMemory analyze_trader.py 生成 | {date_str}*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="交易者行為統計分析")
    parser.add_argument("csv_path", help="CSV 交易紀錄檔案路徑")
    parser.add_argument("--symbol", default=None, help="交易標的（如 XAUUSD, BTCUSDT）")
    parser.add_argument("--output", default=None, help="輸出檔案路徑（預設 reports/trader_fingerprint_{symbol}_{date}.md）")
    args = parser.parse_args()

    print(f"讀取 CSV: {args.csv_path}")
    trades = load_trades(args.csv_path, args.symbol)
    print(f"載入 {len(trades)} 筆交易")

    # Detect symbol
    symbols = set(t.get("symbol") for t in trades if t.get("symbol"))
    symbol = args.symbol or (symbols.pop() if len(symbols) == 1 else "MIXED") if symbols else "UNKNOWN"

    stats = compute_stats(trades)
    report = generate_report(trades, stats, symbol)

    # Output path
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path(__file__).parent.parent / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_symbol = symbol.replace("/", "_").replace("\\", "_")
        output_path = output_dir / f"trader_fingerprint_{safe_symbol}_{date_str}.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"報告已輸出: {output_path}")


if __name__ == "__main__":
    main()
