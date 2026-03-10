"""Tests for intelligence + strategy dashboard endpoints.

Covers: owm-score-trend, confidence-cal, strategy/{name}.
Each endpoint has happy path, empty DB, and edge case tests.
"""

import pytest
from fastapi.testclient import TestClient

from src.tradememory.db import Database
from src.tradememory.dashboard_models import CalibrationPoint, StrategyDetailResponse
from src.tradememory.repositories.trade import TradeRepository
from src.tradememory.services.dashboard import DashboardService, BATCH_001_BASELINES


@pytest.fixture
def db(tmp_path):
    """Create a temp SQLite database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def client(db):
    """TestClient with dashboard_api wired to temp DB."""
    from src.tradememory.server import app
    from src.tradememory.dashboard_api import get_trade_repository

    def override_repo():
        return TradeRepository(db=db)

    app.dependency_overrides[get_trade_repository] = override_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def service(db):
    """DashboardService wired to temp DB for unit tests."""
    return DashboardService(repo=TradeRepository(db=db))


def _insert_trade(db, trade_id, pnl, strategy="VolBreakout",
                  timestamp="2026-03-01T10:00:00Z", pnl_r=None, hold_duration=None):
    """Helper to insert a closed trade."""
    conn = db._get_connection()
    try:
        conn.execute(
            """
            INSERT INTO trade_records
            (id, timestamp, symbol, direction, lot_size, strategy,
             confidence, reasoning, market_context, trade_references, pnl, pnl_r, hold_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id, timestamp, "XAUUSD", "BUY", 0.10, strategy,
                0.8, "test", "{}", "[]", pnl, pnl_r, hold_duration,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_episodic(db, mem_id, strategy="VolBreakout", confidence=None, pnl_r=None,
                     context_session=None, created_at="2026-03-01T00:00:00Z"):
    """Helper to insert an episodic memory with optional confidence and pnl_r."""
    conn = db._get_connection()
    try:
        conn.execute(
            """
            INSERT INTO episodic_memory
            (id, timestamp, context_json, context_regime, context_session, strategy,
             direction, entry_price, confidence, pnl_r, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mem_id, "2026-03-01T00:00:00Z", "{}", "trending_up", context_session,
             strategy, "BUY", 5000.0, confidence, pnl_r, created_at),
        )
        conn.commit()
    finally:
        conn.close()


# ─── OWM Score Trend Tests ─────────────────────────────────────────


class TestOWMScoreTrend:
    """Tests for GET /dashboard/owm-score-trend."""

    def test_returns_empty_without_pg(self, client):
        """Without PostgreSQL, returns empty list (graceful degradation)."""
        resp = client.get("/dashboard/owm-score-trend")
        assert resp.status_code == 200
        assert resp.json() == []


# ─── Confidence Calibration Tests ──────────────────────────────────


class TestConfidenceCalibration:
    """Tests for GET /dashboard/confidence-cal."""

    def test_empty_db(self, client):
        """Empty database returns empty list."""
        resp = client.get("/dashboard/confidence-cal")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_happy_path(self, client, db):
        """Returns calibration points for memories with confidence AND pnl_r."""
        _insert_episodic(db, "m1", confidence=0.8, pnl_r=1.5, strategy="VolBreakout",
                         created_at="2026-03-01T10:00:00Z")
        _insert_episodic(db, "m2", confidence=0.6, pnl_r=-0.5, strategy="IntradayMomentum",
                         created_at="2026-03-02T10:00:00Z")

        resp = client.get("/dashboard/confidence-cal")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {d["trade_id"] for d in data}
        assert ids == {"m1", "m2"}
        m1 = next(d for d in data if d["trade_id"] == "m1")
        assert m1["entry_confidence"] == 0.8
        assert m1["actual_pnl_r"] == 1.5
        assert m1["strategy"] == "VolBreakout"

    def test_skips_null_confidence(self, client, db):
        """Memories with NULL confidence are excluded."""
        _insert_episodic(db, "m1", confidence=None, pnl_r=1.0)
        _insert_episodic(db, "m2", confidence=0.7, pnl_r=0.5)

        resp = client.get("/dashboard/confidence-cal")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["trade_id"] == "m2"

    def test_skips_null_pnl_r(self, client, db):
        """Memories with NULL pnl_r are excluded."""
        _insert_episodic(db, "m1", confidence=0.8, pnl_r=None)
        _insert_episodic(db, "m2", confidence=0.7, pnl_r=0.5)

        resp = client.get("/dashboard/confidence-cal")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["trade_id"] == "m2"

    def test_response_schema(self, client, db):
        """Response validates against CalibrationPoint model."""
        _insert_episodic(db, "m1", confidence=0.8, pnl_r=1.5, strategy="VB")
        resp = client.get("/dashboard/confidence-cal")
        for point in resp.json():
            CalibrationPoint(**point)


# ─── Strategy Detail Tests ─────────────────────────────────────────


class TestStrategyDetail:
    """Tests for GET /dashboard/strategy/{name}."""

    def test_strategy_not_found(self, client):
        """Non-existent strategy returns 404."""
        resp = client.get("/dashboard/strategy/NonExistent")
        assert resp.status_code == 404
        assert "NonExistent" in resp.json()["detail"]

    def test_happy_path(self, client, db):
        """Strategy with trades returns valid detail response."""
        _insert_trade(db, "t1", pnl=100.0, strategy="VolBreakout",
                      timestamp="2026-03-03T10:00:00Z", pnl_r=1.5, hold_duration=3600)
        _insert_trade(db, "t2", pnl=-30.0, strategy="VolBreakout",
                      timestamp="2026-03-04T10:00:00Z", pnl_r=-0.5, hold_duration=1800)
        _insert_trade(db, "t3", pnl=50.0, strategy="VolBreakout",
                      timestamp="2026-03-05T10:00:00Z", pnl_r=0.8, hold_duration=7200)

        resp = client.get("/dashboard/strategy/VolBreakout")
        assert resp.status_code == 200
        data = resp.json()

        assert data["name"] == "VolBreakout"
        assert data["total_trades"] == 3
        assert data["win_rate"] == pytest.approx(2 / 3, abs=0.01)
        assert data["profit_factor"] == pytest.approx(150.0 / 30.0, abs=0.01)
        assert data["avg_pnl_r"] == pytest.approx((1.5 - 0.5 + 0.8) / 3, abs=0.01)
        assert data["avg_hold_seconds"] == int((3600 + 1800 + 7200) / 3)
        assert len(data["trades"]) == 3

    def test_baseline_values_present(self, client, db):
        """Baselines from BATCH-001 are included in response."""
        _insert_trade(db, "t1", pnl=100.0, strategy="VolBreakout")

        resp = client.get("/dashboard/strategy/VolBreakout")
        data = resp.json()
        assert data["baseline_pf"] == 1.17
        assert data["baseline_wr"] == 0.55

    def test_unknown_strategy_baseline_zeros(self, client, db):
        """Strategy not in BATCH-001 baselines gets 0.0 defaults."""
        _insert_trade(db, "t1", pnl=100.0, strategy="CustomStrat")

        resp = client.get("/dashboard/strategy/CustomStrat")
        data = resp.json()
        assert data["baseline_pf"] == 0.0
        assert data["baseline_wr"] == 0.0

    def test_response_schema(self, client, db):
        """Response validates against StrategyDetailResponse model."""
        _insert_trade(db, "t1", pnl=100.0, strategy="VolBreakout")
        resp = client.get("/dashboard/strategy/VolBreakout")
        StrategyDetailResponse(**resp.json())

    def test_session_heatmap_present(self, client, db):
        """Session heatmap is included in response."""
        _insert_trade(db, "t1", pnl=100.0, strategy="VolBreakout",
                      timestamp="2026-03-03T10:00:00Z")

        resp = client.get("/dashboard/strategy/VolBreakout")
        data = resp.json()
        assert "session_heatmap" in data
        assert isinstance(data["session_heatmap"], list)


# ─── Service Unit Tests ─────────────────────────────────────────────


class TestCalibrationService:
    """Unit tests for DashboardService.get_confidence_calibration."""

    def test_empty(self, service):
        """Empty DB returns empty list."""
        assert service.get_confidence_calibration() == []

    def test_data_shape(self, db, service):
        """Returned dicts have correct keys."""
        _insert_episodic(db, "m1", confidence=0.8, pnl_r=1.5, strategy="VB")
        result = service.get_confidence_calibration()
        assert len(result) == 1
        assert set(result[0].keys()) == {"trade_id", "entry_confidence", "actual_pnl_r", "strategy"}


class TestStrategyDetailService:
    """Unit tests for DashboardService.get_strategy_detail."""

    def test_not_found_raises(self, service):
        """Non-existent strategy raises StrategyNotFoundError."""
        from src.tradememory.exceptions import StrategyNotFoundError
        with pytest.raises(StrategyNotFoundError):
            service.get_strategy_detail("NonExistent")

    def test_baselines_constant(self):
        """BATCH_001_BASELINES has expected strategies."""
        assert "VolBreakout" in BATCH_001_BASELINES
        assert "IntradayMomentum" in BATCH_001_BASELINES
        assert "Pullback" in BATCH_001_BASELINES
        assert BATCH_001_BASELINES["IntradayMomentum"]["pf"] == 1.78
