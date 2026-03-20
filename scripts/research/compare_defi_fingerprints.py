#!/usr/bin/env python3
"""Compare DeFi behavior fingerprints across multiple wallets.

Generates side-by-side comparison with similarity metrics:
1. Session overlap (cosine similarity of 24h tx count vectors)
2. Token preference divergence (Jaccard distance of top-10 sold/bought)
3. Tempo classification (burst vs steady)
4. Aave usage ratio
5. Gas sensitivity comparison
6. USD volume comparison

Usage:
    cd C:/Users/johns/projects/tradememory-protocol
    python scripts/research/compare_defi_fingerprints.py \
        data/whale_0xb99a2c_trades.csv data/whale_0x7a16fF_trades.csv \
        --labels "Abraxas Capital" "0x7a16fF"
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_defi_behavior import build_report, load_trades


# =============================================================================
# Comparison metrics
# =============================================================================


def _hour_vector(time_pref: dict) -> list[int]:
    """Extract 24-element tx count vector from time_preference.hour_histogram."""
    hist = time_pref.get("hour_histogram", {})
    vec = []
    for h in range(24):
        key = f"{h:02d}:00"
        entry = hist.get(key, {})
        vec.append(entry.get("count", 0))
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 if either is zero."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def session_overlap(report_a: dict, report_b: dict) -> float:
    """Cosine similarity of 24-hour tx count vectors."""
    vec_a = _hour_vector(report_a.get("time_preference", {}))
    vec_b = _hour_vector(report_b.get("time_preference", {}))
    return cosine_similarity(vec_a, vec_b)


def _top_tokens(token_shifts: dict, key: str, n: int = 10) -> set[str]:
    """Get top-N token symbols from token_shifts."""
    tokens = token_shifts.get(key, {})
    sorted_tokens = sorted(tokens.items(), key=lambda x: x[1], reverse=True)
    return {t[0] for t in sorted_tokens[:n]}


def jaccard_distance(set_a: set, set_b: set) -> float:
    """Jaccard distance = 1 - |intersection| / |union|. Returns 1.0 if both empty."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return 1.0 - len(set_a & set_b) / len(union)


def token_preference_divergence(report_a: dict, report_b: dict) -> dict:
    """Jaccard distance of top-10 sold and bought tokens."""
    ts_a = report_a.get("token_shifts", {})
    ts_b = report_b.get("token_shifts", {})

    sold_a = _top_tokens(ts_a, "top_sold_tokens")
    sold_b = _top_tokens(ts_b, "top_sold_tokens")
    bought_a = _top_tokens(ts_a, "top_bought_tokens")
    bought_b = _top_tokens(ts_b, "top_bought_tokens")

    return {
        "sold_jaccard_distance": round(jaccard_distance(sold_a, sold_b), 4),
        "bought_jaccard_distance": round(jaccard_distance(bought_a, bought_b), 4),
        "sold_overlap": sorted(sold_a & sold_b),
        "bought_overlap": sorted(bought_a & bought_b),
    }


def classify_tempo(report: dict) -> str:
    """Label wallet as 'burst' (stdev/mean > 1.0) or 'steady'."""
    tempo = report.get("tempo", {})
    stats = tempo.get("txs_per_active_day", {})
    mean_val = stats.get("mean", 0)
    stdev_val = stats.get("stdev", 0)
    if mean_val <= 0:
        return "steady"
    ratio = stdev_val / mean_val
    return "burst" if ratio > 1.0 else "steady"


def tempo_cv(report: dict) -> float:
    """Coefficient of variation for tempo."""
    tempo = report.get("tempo", {})
    stats = tempo.get("txs_per_active_day", {})
    mean_val = stats.get("mean", 0)
    stdev_val = stats.get("stdev", 0)
    if mean_val <= 0:
        return 0.0
    return round(stdev_val / mean_val, 4)


def aave_usage_ratio(report: dict) -> float:
    """Percentage of txs involving Aave tokens."""
    fund_flow = report.get("fund_flow", {})
    total_aave = fund_flow.get("total_aave_txs", 0)
    total_trades = report.get("meta", {}).get("total_trades", 0)
    if total_trades == 0:
        return 0.0
    return round(total_aave / total_trades * 100, 2)


def gas_sensitive(report: dict) -> bool:
    """Whether wallet is gas-sensitive."""
    gs = report.get("gas_sensitivity", {})
    activity = gs.get("activity_by_gas_level", {})
    return activity.get("gas_sensitive", False)


def usd_volume_summary(report: dict) -> dict:
    """Extract USD volume summary."""
    usd = report.get("usd_volume", {})
    return {
        "total_volume_usd": usd.get("total_volume_usd", 0),
        "avg_tx_size_usd": usd.get("avg_tx_size_usd", 0),
        "median_tx_size_usd": usd.get("median_tx_size_usd", 0),
        "coverage_pct": usd.get("coverage_pct", 0),
    }


# =============================================================================
# Comparison builder
# =============================================================================


def compare_fingerprints(reports: list[dict]) -> dict:
    """Build pairwise comparison across all wallets."""
    wallets = []
    for r in reports:
        meta = r.get("meta", {})
        wallets.append({
            "wallet": meta.get("wallet", "unknown"),
            "total_trades": meta.get("total_trades", 0),
            "date_range": meta.get("date_range", {}),
            "tempo_class": classify_tempo(r),
            "tempo_cv": tempo_cv(r),
            "aave_usage_pct": aave_usage_ratio(r),
            "gas_sensitive": gas_sensitive(r),
            "usd_volume": usd_volume_summary(r),
            "peak_hour_utc": r.get("time_preference", {}).get("peak_hour_utc"),
            "peak_day": r.get("time_preference", {}).get("peak_day"),
        })

    # Pairwise comparisons
    pairwise = []
    for i in range(len(reports)):
        for j in range(i + 1, len(reports)):
            pair = {
                "wallet_a": wallets[i]["wallet"],
                "wallet_b": wallets[j]["wallet"],
                "session_overlap_cosine": round(
                    session_overlap(reports[i], reports[j]), 4
                ),
                "token_divergence": token_preference_divergence(
                    reports[i], reports[j]
                ),
                "same_tempo_class": wallets[i]["tempo_class"]
                == wallets[j]["tempo_class"],
                "both_gas_sensitive": wallets[i]["gas_sensitive"]
                and wallets[j]["gas_sensitive"],
                "neither_gas_sensitive": not wallets[i]["gas_sensitive"]
                and not wallets[j]["gas_sensitive"],
            }
            pairwise.append(pair)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wallet_count": len(reports),
        "wallets": wallets,
        "pairwise": pairwise,
    }


# =============================================================================
# Terminal output
# =============================================================================


def print_comparison(result: dict) -> None:
    """Print side-by-side comparison table."""
    wallets = result["wallets"]
    pairwise = result["pairwise"]

    # Header
    print("\n" + "=" * 80)
    print("DeFi Fingerprint Comparison")
    print("=" * 80)

    # Wallet summary table
    col_w = max(30, max(len(w["wallet"]) for w in wallets) + 2)
    header = f"{'Metric':<25}"
    for w in wallets:
        header += f" | {w['wallet']:<{col_w}}"
    print(f"\n{header}")
    print("-" * len(header))

    rows = [
        ("Total trades", [str(w["total_trades"]) for w in wallets]),
        ("Date range", [
            f"{w['date_range'].get('start', '?')} → {w['date_range'].get('end', '?')}"
            for w in wallets
        ]),
        ("Tempo class", [
            f"{w['tempo_class']} (CV={w['tempo_cv']:.2f})" for w in wallets
        ]),
        ("Aave usage %", [f"{w['aave_usage_pct']:.1f}%" for w in wallets]),
        ("Gas sensitive", [str(w["gas_sensitive"]) for w in wallets]),
        ("Peak hour (UTC)", [
            f"{w['peak_hour_utc']:02d}:00" if w["peak_hour_utc"] is not None else "N/A"
            for w in wallets
        ]),
        ("Peak day", [w.get("peak_day", "N/A") for w in wallets]),
        ("USD volume", [
            f"${w['usd_volume']['total_volume_usd']:,.0f}"
            if w["usd_volume"]["total_volume_usd"] > 0
            else "N/A"
            for w in wallets
        ]),
        ("Avg tx size (USD)", [
            f"${w['usd_volume']['avg_tx_size_usd']:,.0f}"
            if w["usd_volume"]["avg_tx_size_usd"] > 0
            else "N/A"
            for w in wallets
        ]),
        ("USD coverage", [
            f"{w['usd_volume']['coverage_pct']:.1f}%" for w in wallets
        ]),
    ]

    for label, values in rows:
        row = f"{label:<25}"
        for v in values:
            row += f" | {v:<{col_w}}"
        print(row)

    # Pairwise metrics
    if pairwise:
        print(f"\n{'─' * 80}")
        print("Pairwise Comparisons")
        print(f"{'─' * 80}")
        for p in pairwise:
            print(f"\n  {p['wallet_a']}  vs  {p['wallet_b']}")
            print(f"  {'Session overlap (cosine)':<35} {p['session_overlap_cosine']:.4f}")
            td = p["token_divergence"]
            print(f"  {'Sold token Jaccard distance':<35} {td['sold_jaccard_distance']:.4f}")
            print(f"  {'Bought token Jaccard distance':<35} {td['bought_jaccard_distance']:.4f}")
            if td["sold_overlap"]:
                print(f"  {'Sold token overlap':<35} {', '.join(td['sold_overlap'])}")
            if td["bought_overlap"]:
                print(f"  {'Bought token overlap':<35} {', '.join(td['bought_overlap'])}")
            print(f"  {'Same tempo class':<35} {p['same_tempo_class']}")
            gas_label = (
                "both sensitive" if p["both_gas_sensitive"]
                else "neither sensitive" if p["neither_gas_sensitive"]
                else "different"
            )
            print(f"  {'Gas sensitivity':<35} {gas_label}")

    print(f"\n{'=' * 80}\n")


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Compare DeFi behavior fingerprints across multiple wallets"
    )
    parser.add_argument(
        "csv_paths",
        nargs="+",
        help="Paths to whale trade CSVs (2 or more)",
    )
    parser.add_argument(
        "--labels", "-l",
        nargs="+",
        help="Wallet labels (same order as CSVs). Defaults to filenames.",
    )
    parser.add_argument(
        "--output", "-o",
        default="scripts/research/output/fingerprint_comparison.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    if len(args.csv_paths) < 2:
        print("ERROR: Need at least 2 CSV paths to compare.")
        sys.exit(1)

    labels = args.labels or [Path(p).stem for p in args.csv_paths]
    if len(labels) != len(args.csv_paths):
        print(f"ERROR: {len(labels)} labels for {len(args.csv_paths)} CSVs.")
        sys.exit(1)

    # Build reports
    reports = []
    for csv_path, label in zip(args.csv_paths, labels):
        path = Path(csv_path)
        if not path.exists():
            print(f"ERROR: CSV not found: {path}")
            sys.exit(1)
        print(f"Loading {label} from {path}...")
        trades = load_trades(str(path))
        if not trades:
            print(f"ERROR: No trades loaded from {path}")
            sys.exit(1)
        print(f"  → {len(trades)} trades loaded. Building fingerprint...")
        report = build_report(trades, wallet_label=label)
        reports.append(report)

    # Compare
    result = compare_fingerprints(reports)

    # Terminal output
    print_comparison(result)

    # Save JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"Comparison saved to {output_path}")


if __name__ == "__main__":
    main()
