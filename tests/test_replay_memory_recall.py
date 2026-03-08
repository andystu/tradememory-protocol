"""Tests for replay memory_recall module."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.tradememory.replay.memory_recall import build_memory_context

_SCHEMA = """
CREATE TABLE episodic_memory (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    context_json TEXT NOT NULL,
    context_regime TEXT,
    context_volatility_regime TEXT,
    context_session TEXT,
    context_atr_d1 REAL,
    context_atr_h1 REAL,
    strategy TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    lot_size REAL,
    exit_price REAL,
    pnl REAL,
    pnl_r REAL,
    hold_duration_seconds INTEGER,
    max_adverse_excursion REAL,
    reflection TEXT,
    confidence REAL DEFAULT 0.5,
    tags TEXT,
    retrieval_strength REAL DEFAULT 1.0,
    retrieval_count INTEGER DEFAULT 0,
    last_retrieved TEXT,
    created_at TEXT NOT NULL
);
"""


def _insert(conn, id, strategy="VolBreakout", regime="trending", session="london",
            entry=5100.0, exit_=5150.0, pnl=50.0, pnl_r=1.5,
            reflection="Good entry on breakout", strength=1.0):
    conn.execute(
        """INSERT INTO episodic_memory
           (id, timestamp, context_json, context_regime, context_session,
            strategy, direction, entry_price, exit_price, pnl, pnl_r,
            reflection, retrieval_strength, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (id, "2026-03-01T10:00:00", "{}", regime, session,
         strategy, "long", entry, exit_, pnl, pnl_r,
         reflection, strength, "2026-03-01T10:00:00"),
    )


@pytest.fixture
def db_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "test.db")
        conn = sqlite3.connect(path)
        conn.executescript(_SCHEMA)
        conn.close()
        yield path


class TestEmptyDB:
    def test_returns_empty_string(self, db_path):
        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0)
        assert result == ""


class TestPopulatedDB:
    def test_returns_max_limit(self, db_path):
        conn = sqlite3.connect(db_path)
        for i in range(8):
            _insert(conn, f"E-{i:03d}", strength=float(i))
        conn.commit()
        conn.close()

        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0, limit=5)
        # Header + up to 5 trades (each with reflection line)
        assert "## Similar Past Trades" in result
        assert result.count("[VolBreakout]") == 5

    def test_ordered_by_retrieval_strength(self, db_path):
        conn = sqlite3.connect(db_path)
        _insert(conn, "E-low", pnl=10.0, strength=0.1)
        _insert(conn, "E-high", pnl=99.0, strength=9.0)
        conn.commit()
        conn.close()

        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0)
        assert result.index("pnl=$99.00") < result.index("pnl=$10.00")

    def test_reflection_truncated_at_150(self, db_path):
        long_text = "A" * 300
        conn = sqlite3.connect(db_path)
        _insert(conn, "E-long", reflection=long_text)
        conn.commit()
        conn.close()

        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0)
        # Reflection line should contain at most 150 A's
        assert "A" * 150 in result
        assert "A" * 151 not in result


class TestStrategyFiltering:
    def test_filters_by_strategy(self, db_path):
        conn = sqlite3.connect(db_path)
        _insert(conn, "E-vb", strategy="VolBreakout")
        _insert(conn, "E-im", strategy="IntradayMomentum")
        conn.commit()
        conn.close()

        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0)
        assert "[VolBreakout]" in result
        assert "[IntradayMomentum]" not in result

    def test_filters_by_regime(self, db_path):
        conn = sqlite3.connect(db_path)
        _insert(conn, "E-trend", regime="trending")
        _insert(conn, "E-range", regime="range_bound")
        conn.commit()
        conn.close()

        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0)
        assert result.count("[VolBreakout]") == 1

    def test_filters_by_session(self, db_path):
        conn = sqlite3.connect(db_path)
        _insert(conn, "E-ldn", session="london")
        _insert(conn, "E-asia", session="asian")
        conn.commit()
        conn.close()

        result = build_memory_context(db_path, "VolBreakout", "trending", "london", 150.0)
        assert result.count("[VolBreakout]") == 1
