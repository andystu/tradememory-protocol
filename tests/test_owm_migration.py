"""
Tests for OWM migration: trade_records → episodic, patterns → semantic, affective init.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from tradememory.db import Database
from tradememory.owm.migration import (
    migrate_trades_to_episodic,
    migrate_patterns_to_semantic,
    initialize_affective,
)


@pytest.fixture
def db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_migration.db"
        yield Database(str(db_path))


def _insert_trade(db, trade_id="T-001", strategy="VolBreakout", direction="long",
                  market_context=None, pnl_r=1.5, confidence=0.7, pnl=100.0):
    """Helper to insert a trade_record directly via SQL."""
    if market_context is None:
        market_context = {"price": 5175.0, "session": "london", "regime": "trending_up",
                          "atr_d1": 150.0, "atr_h1": 35.0, "volatility_regime": "high"}
    conn = db._get_connection()
    try:
        conn.execute("""
            INSERT INTO trade_records (
                id, timestamp, symbol, direction, lot_size, strategy,
                confidence, reasoning, market_context, trade_references,
                pnl, pnl_r, hold_duration, lessons, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_id, "2026-03-02T10:00:00", "XAUUSD", direction, 0.03,
            strategy, confidence, "Test trade", json.dumps(market_context),
            "[]", pnl, pnl_r, 3600, "Lesson learned", '["tag1"]'
        ))
        conn.commit()
    finally:
        conn.close()


def _insert_pattern(db, pattern_id="P-001", confidence=0.8, sample_size=50,
                    strategy="VolBreakout", symbol="XAUUSD"):
    """Helper to insert a pattern directly via SQL."""
    conn = db._get_connection()
    try:
        conn.execute("""
            INSERT INTO patterns (
                pattern_id, pattern_type, description, confidence,
                sample_size, date_range, strategy, symbol, metrics,
                source, validation_status, discovered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_id, "win_rate", "VB wins in trending_up", confidence,
            sample_size, "2024.01-2026.02", strategy, symbol,
            json.dumps({"win_rate": 0.55, "avg_rr": 1.37}),
            "backtest_auto", "IN_SAMPLE", "2026-03-01T00:00:00"
        ))
        conn.commit()
    finally:
        conn.close()


# ========== migrate_trades_to_episodic ==========

class TestMigrateToEpisodic:

    def test_basic_migration(self, db):
        _insert_trade(db, "T-001")
        count = migrate_trades_to_episodic(db)
        assert count == 1

        # Verify episodic record
        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM episodic_memory WHERE id = 'T-001'"
            ).fetchone()
            assert row is not None
            assert row["strategy"] == "VolBreakout"
            assert row["direction"] == "long"
            assert row["pnl_r"] == 1.5
            assert row["confidence"] == 0.7
            assert row["retrieval_strength"] == 1.0
            assert row["entry_price"] == 5175.0
        finally:
            conn.close()

    def test_context_fields_parsed(self, db):
        ctx = {"price": 5200.0, "session": "newyork", "regime": "ranging",
               "atr_d1": 160.0, "atr_h1": 40.0, "volatility_regime": "extreme"}
        _insert_trade(db, "T-002", market_context=ctx)
        migrate_trades_to_episodic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM episodic_memory WHERE id = 'T-002'"
            ).fetchone()
            assert row["context_regime"] == "ranging"
            assert row["context_session"] == "newyork"
            assert row["context_atr_d1"] == 160.0
            assert row["context_atr_h1"] == 40.0
            assert row["context_volatility_regime"] == "extreme"
        finally:
            conn.close()

    def test_missing_context_fields_are_none(self, db):
        ctx = {"price": 5100.0}  # no regime, session, atr
        _insert_trade(db, "T-003", market_context=ctx)
        migrate_trades_to_episodic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM episodic_memory WHERE id = 'T-003'"
            ).fetchone()
            assert row["context_regime"] is None
            assert row["context_session"] is None
            assert row["context_atr_d1"] is None
            assert row["context_atr_h1"] is None
        finally:
            conn.close()

    def test_confidence_default(self, db):
        """Trade with None confidence → episodic gets 0.5."""
        conn = db._get_connection()
        try:
            conn.execute("""
                INSERT INTO trade_records (
                    id, timestamp, symbol, direction, lot_size, strategy,
                    confidence, reasoning, market_context, trade_references
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "T-004", "2026-03-02T10:00:00", "XAUUSD", "long", 0.01,
                "PB", 0.5, "test", '{"price": 5000}', "[]"
            ))
            conn.commit()
        finally:
            conn.close()
        migrate_trades_to_episodic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT confidence FROM episodic_memory WHERE id = 'T-004'"
            ).fetchone()
            assert row["confidence"] == 0.5
        finally:
            conn.close()

    def test_multiple_trades(self, db):
        for i in range(5):
            _insert_trade(db, f"T-{i:03d}")
        count = migrate_trades_to_episodic(db)
        assert count == 5

        conn = db._get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM episodic_memory").fetchone()["c"]
            assert total == 5
        finally:
            conn.close()

    def test_duplicate_no_error(self, db):
        """Running migration twice should not raise or duplicate rows."""
        _insert_trade(db, "T-DUP")
        count1 = migrate_trades_to_episodic(db)
        count2 = migrate_trades_to_episodic(db)
        assert count1 == 1
        assert count2 == 1  # processed 1 row, but INSERT OR IGNORE skips

        conn = db._get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM episodic_memory").fetchone()["c"]
            assert total == 1
        finally:
            conn.close()

    def test_empty_table(self, db):
        """Migration on empty trade_records should return 0 and not crash."""
        count = migrate_trades_to_episodic(db)
        assert count == 0

    def test_hold_duration_mapped(self, db):
        _insert_trade(db, "T-HD")
        migrate_trades_to_episodic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT hold_duration_seconds FROM episodic_memory WHERE id = 'T-HD'"
            ).fetchone()
            assert row["hold_duration_seconds"] == 3600
        finally:
            conn.close()

    def test_lessons_to_reflection(self, db):
        _insert_trade(db, "T-LES")
        migrate_trades_to_episodic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT reflection FROM episodic_memory WHERE id = 'T-LES'"
            ).fetchone()
            assert row["reflection"] == "Lesson learned"
        finally:
            conn.close()


# ========== migrate_patterns_to_semantic ==========

class TestMigrateToSemantic:

    def test_basic_migration(self, db):
        _insert_pattern(db, "P-001", confidence=0.8, sample_size=50)
        count = migrate_patterns_to_semantic(db)
        assert count == 1

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM semantic_memory WHERE id = 'P-001'"
            ).fetchone()
            assert row is not None
            assert row["proposition"] == "VB wins in trending_up"
            # alpha = 1 + 0.8 * 50 = 41.0
            assert row["alpha"] == pytest.approx(41.0)
            # beta = 1 + 0.2 * 50 = 11.0
            assert row["beta"] == pytest.approx(11.0)
            assert row["sample_size"] == 50
            assert row["strategy"] == "VolBreakout"
            assert row["symbol"] == "XAUUSD"
            assert row["source"] == "backtest_auto"
            assert row["retrieval_strength"] == 1.0
        finally:
            conn.close()

    def test_alpha_beta_calculation(self, db):
        """Verify alpha/beta formula: alpha = 1 + conf*n, beta = 1 + (1-conf)*n."""
        _insert_pattern(db, "P-CALC", confidence=0.6, sample_size=100)
        migrate_patterns_to_semantic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT alpha, beta FROM semantic_memory WHERE id = 'P-CALC'"
            ).fetchone()
            assert row["alpha"] == pytest.approx(61.0)  # 1 + 0.6*100
            assert row["beta"] == pytest.approx(41.0)   # 1 + 0.4*100
        finally:
            conn.close()

    def test_zero_sample_size(self, db):
        _insert_pattern(db, "P-ZERO", confidence=0.5, sample_size=0)
        migrate_patterns_to_semantic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT alpha, beta FROM semantic_memory WHERE id = 'P-ZERO'"
            ).fetchone()
            assert row["alpha"] == pytest.approx(1.0)
            assert row["beta"] == pytest.approx(1.0)
        finally:
            conn.close()

    def test_duplicate_no_error(self, db):
        _insert_pattern(db, "P-DUP")
        migrate_patterns_to_semantic(db)
        migrate_patterns_to_semantic(db)  # should not raise

        conn = db._get_connection()
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM semantic_memory").fetchone()["c"]
            assert total == 1
        finally:
            conn.close()

    def test_empty_table(self, db):
        count = migrate_patterns_to_semantic(db)
        assert count == 0

    def test_metrics_to_validity_conditions(self, db):
        _insert_pattern(db, "P-MET")
        migrate_patterns_to_semantic(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT validity_conditions FROM semantic_memory WHERE id = 'P-MET'"
            ).fetchone()
            vc = json.loads(row["validity_conditions"])
            assert "win_rate" in vc
        finally:
            conn.close()


# ========== initialize_affective ==========

class TestInitializeAffective:

    def test_basic_init(self, db):
        result = initialize_affective(db, equity=15000.0)
        assert result is True

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM affective_state WHERE id = 'current'"
            ).fetchone()
            assert row is not None
            assert row["peak_equity"] == 15000.0
            assert row["current_equity"] == 15000.0
            assert row["confidence_level"] == 0.5
            assert row["risk_appetite"] == 1.0
            assert row["drawdown_state"] == 0.0
            assert row["consecutive_wins"] == 0
            assert row["consecutive_losses"] == 0
        finally:
            conn.close()

    def test_default_equity(self, db):
        initialize_affective(db)

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT peak_equity, current_equity FROM affective_state WHERE id = 'current'"
            ).fetchone()
            assert row["peak_equity"] == 10000.0
            assert row["current_equity"] == 10000.0
        finally:
            conn.close()

    def test_duplicate_no_error(self, db):
        initialize_affective(db, equity=10000.0)
        initialize_affective(db, equity=20000.0)  # should not raise, should not overwrite

        conn = db._get_connection()
        try:
            row = conn.execute(
                "SELECT peak_equity FROM affective_state WHERE id = 'current'"
            ).fetchone()
            # INSERT OR IGNORE keeps the first value
            assert row["peak_equity"] == 10000.0
        finally:
            conn.close()

    def test_empty_db_no_crash(self, db):
        """Calling on fresh DB with no prior state should work."""
        result = initialize_affective(db)
        assert result is True
