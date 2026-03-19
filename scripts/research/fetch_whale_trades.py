#!/usr/bin/env python3
"""Fetch on-chain ERC-20 token transfers for a whale wallet and convert to trade CSV.

Pairs token transfers within the same tx hash into swaps (sell A → buy B).
Output is a CSV compatible with analyze_trader.py.

Usage:
    cd C:/Users/johns/projects/tradememory-protocol
    python scripts/research/fetch_whale_trades.py 0xb99a2c4c1c4f1fc27150681b740396f6ce1cbcf5
    python scripts/research/fetch_whale_trades.py 0xb99a... --output data/abraxas_trades.csv
    python scripts/research/fetch_whale_trades.py 0xb99a... --api-key YOUR_KEY
"""

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

# Etherscan API config
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
RATE_LIMIT_DELAY = 0.25  # 4 req/s (conservative, free tier = 5/s)
MAX_RESULTS_PER_PAGE = 10000

# Stablecoins and wrapped tokens (used to determine trade direction)
STABLECOINS = {
    "USDT", "USDC", "DAI", "BUSD", "TUSD", "FRAX", "LUSD", "GUSD",
    "USDP", "PYUSD", "FDUSD", "DOLA", "crvUSD", "GHO", "sUSD",
}
WRAPPED_ETH = {"WETH", "wstETH", "stETH", "eETH", "rETH", "cbETH", "AWETH", "AWSTETH"}
QUOTE_TOKENS = STABLECOINS | WRAPPED_ETH | {"ETH"}


def fetch_erc20_transfers(
    address: str,
    api_key: str | None = None,
    start_block: int = 0,
    end_block: int = 99999999,
) -> list[dict]:
    """Fetch all ERC-20 token transfers for an address from Etherscan."""
    all_transfers = []
    page = 1

    while True:
        params = {
            "chainid": 1,
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": MAX_RESULTS_PER_PAGE,
            "sort": "asc",
        }
        if api_key:
            params["apikey"] = api_key

        try:
            resp = httpx.get(ETHERSCAN_BASE, params=params, timeout=30)
            data = resp.json()
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
            break

        if data.get("status") != "1" or not data.get("result"):
            if data.get("message") == "No transactions found":
                break
            if "rate limit" in str(data.get("result", "")).lower():
                print("  [RATE LIMIT] Waiting 5s...")
                time.sleep(5)
                continue
            print(f"  [WARN] Unexpected response: {data.get('message', 'unknown')}")
            break

        transfers = data["result"]
        all_transfers.extend(transfers)
        print(f"  Page {page}: {len(transfers)} transfers (total: {len(all_transfers)})")

        if len(transfers) < MAX_RESULTS_PER_PAGE:
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    return all_transfers


def pair_swaps(transfers: list[dict], wallet: str) -> list[dict]:
    """Group ERC-20 transfers by tx hash and pair into swaps.

    A swap = one tx where wallet sends token A and receives token B.
    Returns list of trade dicts compatible with analyze_trader.py CSV format.
    """
    wallet_lower = wallet.lower()

    # Group by tx hash
    by_tx: dict[str, list[dict]] = defaultdict(list)
    for t in transfers:
        by_tx[t["hash"]].append(t)

    trades = []
    for tx_hash, tx_transfers in by_tx.items():
        outgoing = []  # wallet sends tokens
        incoming = []  # wallet receives tokens

        for t in tx_transfers:
            token_symbol = t.get("tokenSymbol", "UNKNOWN")
            value = int(t.get("value", "0"))
            decimals = int(t.get("tokenDecimal", "18"))
            amount = value / (10 ** decimals) if decimals > 0 else value

            if amount == 0:
                continue

            entry = {
                "symbol": token_symbol,
                "amount": amount,
                "contract": t.get("contractAddress", ""),
                "timestamp": int(t.get("timeStamp", "0")),
                "gas_used": int(t.get("gasUsed", "0")),
                "gas_price": int(t.get("gasPrice", "0")),
            }

            if t.get("from", "").lower() == wallet_lower:
                outgoing.append(entry)
            elif t.get("to", "").lower() == wallet_lower:
                incoming.append(entry)

        # Skip if not a swap (need both outgoing and incoming)
        if not outgoing or not incoming:
            continue

        # Determine the "base" token (what was traded) vs "quote" (what was used to pay)
        # Heuristic: stablecoins/WETH are quote, everything else is base
        sold = outgoing[0]  # primary outgoing token
        bought = incoming[0]  # primary incoming token

        # Determine direction: if selling a quote token → BUY base, else SELL base
        sold_is_quote = sold["symbol"] in QUOTE_TOKENS
        bought_is_quote = bought["symbol"] in QUOTE_TOKENS

        if sold_is_quote and not bought_is_quote:
            # Paying with stablecoin/ETH → buying the other token
            side = "BUY"
            symbol = f"{bought['symbol']}/{sold['symbol']}"
            entry_price = sold["amount"] / bought["amount"] if bought["amount"] > 0 else 0
            volume = bought["amount"]
        elif bought_is_quote and not sold_is_quote:
            # Receiving stablecoin/ETH → selling the other token
            side = "SELL"
            symbol = f"{sold['symbol']}/{bought['symbol']}"
            entry_price = bought["amount"] / sold["amount"] if sold["amount"] > 0 else 0
            volume = sold["amount"]
        else:
            # Both are quote or both are base — use the outgoing as "sold"
            side = "SELL"
            symbol = f"{sold['symbol']}/{bought['symbol']}"
            entry_price = bought["amount"] / sold["amount"] if sold["amount"] > 0 else 0
            volume = sold["amount"]

        ts = datetime.fromtimestamp(sold["timestamp"], tz=timezone.utc)
        gas_cost_eth = (sold["gas_used"] * sold["gas_price"]) / 1e18

        trade = {
            "open_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "close_time": ts.strftime("%Y-%m-%d %H:%M:%S"),  # swaps are instant
            "symbol": symbol,
            "side": side,
            "open_price": round(entry_price, 8),
            "close_price": round(entry_price, 8),  # instant swap, no separate exit
            "volume": round(volume, 8),
            "pnl": 0,  # can't calculate PnL from single swap — need position tracking
            "tx_hash": tx_hash,
            "gas_cost_eth": round(gas_cost_eth, 6),
            "tokens_sold": f"{sold['symbol']}:{round(sold['amount'], 4)}",
            "tokens_bought": f"{bought['symbol']}:{round(bought['amount'], 4)}",
        }
        trades.append(trade)

    return trades


def write_csv(trades: list[dict], output_path: Path):
    """Write trades to CSV."""
    if not trades:
        print("No trades to write.")
        return

    fieldnames = [
        "open_time", "close_time", "symbol", "side", "open_price",
        "close_price", "volume", "pnl", "tx_hash", "gas_cost_eth",
        "tokens_sold", "tokens_bought",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)

    print(f"\nWrote {len(trades)} trades to {output_path}")


def print_summary(trades: list[dict]):
    """Print a quick summary of extracted trades."""
    if not trades:
        print("No trades extracted.")
        return

    symbols = defaultdict(int)
    sides = defaultdict(int)
    for t in trades:
        symbols[t["symbol"]] += 1
        sides[t["side"]] += 1

    timestamps = [t["open_time"] for t in trades]
    print(f"\n{'='*60}")
    print(f"WHALE TRADE EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total swaps: {len(trades)}")
    print(f"Date range: {min(timestamps)} → {max(timestamps)}")
    print(f"Buy/Sell: {sides.get('BUY', 0)} buys, {sides.get('SELL', 0)} sells")
    print(f"\nTop pairs:")
    for sym, count in sorted(symbols.items(), key=lambda x: -x[1])[:10]:
        print(f"  {sym}: {count} trades")

    total_gas = sum(float(t["gas_cost_eth"]) for t in trades)
    print(f"\nTotal gas cost: {total_gas:.4f} ETH")


def main():
    parser = argparse.ArgumentParser(description="Fetch whale wallet trades from Etherscan")
    parser.add_argument("address", help="Ethereum wallet address (0x...)")
    parser.add_argument("--output", "-o", default=None, help="Output CSV path")
    parser.add_argument("--api-key", default=None, help="Etherscan API key (optional)")
    parser.add_argument("--start-block", type=int, default=0, help="Start block")
    parser.add_argument("--end-block", type=int, default=99999999, help="End block")
    args = parser.parse_args()

    address = args.address.strip()
    if not address.startswith("0x") or len(address) != 42:
        print(f"Invalid Ethereum address: {address}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else Path(f"data/whale_{address[:8]}_trades.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching ERC-20 transfers for {address}...")
    print(f"Using Etherscan API {'with' if args.api_key else 'without'} API key")
    print()

    transfers = fetch_erc20_transfers(
        address, api_key=args.api_key,
        start_block=args.start_block, end_block=args.end_block,
    )
    print(f"\nTotal transfers fetched: {len(transfers)}")

    if not transfers:
        print("No transfers found. Check the address.")
        sys.exit(1)

    print("\nPairing transfers into swaps...")
    trades = pair_swaps(transfers, address)

    print_summary(trades)
    write_csv(trades, output_path)

    print(f"\nNext step: python scripts/analyze_trader.py {output_path}")


if __name__ == "__main__":
    main()
