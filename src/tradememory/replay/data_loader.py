"""MT5 CSV parser and sliding window iterator for replay engine."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Tuple

from src.tradememory.replay.models import Bar


def parse_mt5_csv(file_path: str) -> List[Bar]:
    """Parse MT5-exported CSV into Bar objects, sorted oldest-first.

    Auto-detects tab vs comma delimiter.
    Expected columns: Date, Time, Open, High, Low, Close, Tickvol, Volume, Spread.
    Date format: "2024.06.10", Time format: "00:00".
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8-sig")  # handle BOM
    lines = [line for line in text.splitlines() if line.strip()]

    if not lines:
        return []

    # Auto-detect delimiter from header
    header_line = lines[0]
    delimiter = "\t" if "\t" in header_line else ","

    # Skip header
    bars: List[Bar] = []
    reader = csv.reader(lines[1:], delimiter=delimiter)

    for row in reader:
        if len(row) < 7:
            continue

        date_str = row[0].strip()
        time_str = row[1].strip()
        timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H:%M")

        bars.append(
            Bar(
                timestamp=timestamp,
                open=float(row[2]),
                high=float(row[3]),
                low=float(row[4]),
                close=float(row[5]),
                tick_volume=int(row[6]),
                spread=int(row[8]) if len(row) > 8 else 0,
            )
        )

    bars.sort(key=lambda b: b.timestamp)
    return bars


def sliding_window(
    bars: List[Bar], window_size: int, step: int = 1
) -> Iterator[Tuple[int, List[Bar], Bar]]:
    """Yield (bar_idx, window_bars, current_bar) over the bar series.

    Args:
        bars: List of Bar objects sorted oldest-first.
        window_size: Number of bars in each window.
        step: Advance step between yields.

    Yields:
        (bar_idx, window_bars, current_bar) where bar_idx is the index
        of the current (last) bar in the window.
    """
    if len(bars) < window_size:
        return

    for i in range(window_size - 1, len(bars), step):
        start = i - window_size + 1
        window_bars = bars[start : i + 1]
        yield i, window_bars, bars[i]
