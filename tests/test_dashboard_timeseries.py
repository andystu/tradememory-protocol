"""Tests for time-series dashboard endpoints.

Covers: equity-curve, rolling-metrics, memory-growth.
Each endpoint has happy path, empty DB, edge case, and filtering tests.
"""

import pytest
from fastapi.testclient import TestClient

from src.tradememory.db import Database
from src.tradememory.dashboard_models import EquityPoint, RollingMetricPoint, MemoryGrowthPoint
from src.tradememory.repositories.trade import TradeRepository
from src.tradememory.services.dashboard import DashboardService


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


def _insert_trade(db, trade_id, pnl, strategy="VolBreakout", timestamp="2026-03-01T10:00:00Z", pnl_r=None):
    """Helper to insert a closed trade with configurable timestamp and pnl_r."""
    conn = db._get_connection()
    try:
        conn.execute(
            """
            INSERT INTO trade_records
            (id, timestamp, symbol, direction, lot_size, strategy,
             confidence, reasoning, market_context, trade_references, pnl, pnl_r)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id, timestamp, "XAUUSD", "BUY", 0.10, strategy,
                0.8, "test", "{}", "[]", pnl, pnl_r,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_episodic(db, mem_id, regime="trending_up", created_at="2026-03-01T00:00:00Z"):
    """Helper to insert an episodic memory with configurable regime and created_at."""
    conn = db._get_connection()
    try:
        conn.execute(
            """
            INSERT INTO episodic_memory
            (id, timestamp, context_json, context_regime, strategy, direction,
             entry_price, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mem_id, "2026-03-01T00:00:00Z", "{}", regime, "VB", "BUY", 5000.0, 0.7, created_at),
        )
        conn.commit()
    finally:
        conn.close()


# ─── Equity Curve Tests ────────────────────────────────────────────


class TestEquityCurveEndpoint:
    """Tests for GET /dashboard/equity-curve."""

    def test_empty_db(self, client):
        """Empty database returns empty list."""
        resp = client.get("/dashboard/equity-curve")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_happy_path(self, client, db):
        """Multiple trades produce correct cumulative PnL and drawdown."""
        _insert_trade(db, "t1", pnl=100.0, timestamp="2026-03-01T10:00:00Z")
        _insert_trade(db, "t2", pnl=-30.0, timestamp="2026-03-01T14:00:00Z")
        _insert_trade(db, "t3", pnl=50.0, timestamp="2026-03-02T10:00:00Z")

        resp = client.get("/dashboard/equity-curve")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # 2 dates

        # Day 1: cumulative = 100 + (-30) = 70, peak = 70, drawdown = 0
        # Actually cumulative builds trade by trade: after t1=100, peak=100; after t2=70
        # So peak=100, drawdown = (100-70)/100 = 30%
        day1 = data[0]
        assert day1["date"] == "2026-03-01"
        assert day1["cumulative_pnl"] == 70.0
        assert day1["drawdown_pct"] == 30.0
        assert day1["trade_count"] == 2

        # Day 2: cumulative = 70 + 50 = 120, peak = 120, drawdown = 0
        day2 = data[1]
        assert day2["date"] == "2026-03-02"
        assert day2["cumulative_pnl"] == 120.0
        assert day2["drawdown_pct"] == 0.0
        assert day2["trade_count"] == 1

    def test_single_trade(self, client, db):
        """Single trade edge case."""
        _insert_trade(db, "t1", pnl=50.0)

        resp = client.get("/dashboard/equity-curve")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cumulative_pnl"] == 50.0
        assert data[0]["drawdown_pct"] == 0.0
        assert data[0]["trade_count"] == 1

    def test_all_losses(self, client, db):
        """All losing trades — drawdown stays at 0% (peak never goes above 0)."""
        _insert_trade(db, "t1", pnl=-50.0, timestamp="2026-03-01T10:00:00Z")
        _insert_trade(db, "t2", pnl=-30.0, timestamp="2026-03-02T10:00:00Z")

        resp = client.get("/dashboard/equity-curve")
        data = resp.json()
        # Peak never > 0, so drawdown_pct = 0.0
        assert data[0]["cumulative_pnl"] == -50.0
        assert data[0]["drawdown_pct"] == 0.0
        assert data[1]["cumulative_pnl"] == -80.0

    def test_date_filtering(self, client, db):
        """start_date and end_date filter trades."""
        _insert_trade(db, "t1", pnl=100.0, timestamp="2026-03-01T10:00:00Z")
        _insert_trade(db, "t2", pnl=50.0, timestamp="2026-03-05T10:00:00Z")
        _insert_trade(db, "t3", pnl=75.0, timestamp="2026-03-10T10:00:00Z")

        resp = client.get("/dashboard/equity-curve?start_date=2026-03-04&end_date=2026-03-06")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2026-03-05"
        assert data[0]["cumulative_pnl"] == 50.0

    def test_strategy_filter(self, client, db):
        """strategy param filters to specific strategy."""
        _insert_trade(db, "t1", pnl=100.0, strategy="VolBreakout")
        _insert_trade(db, "t2", pnl=50.0, strategy="IntradayMomentum")

        resp = client.get("/dashboard/equity-curve?strategy=VolBreakout")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cumulative_pnl"] == 100.0

    def test_response_schema(self, client, db):
        """Response validates against EquityPoint Pydantic model."""
        _insert_trade(db, "t1", pnl=100.0)
        resp = client.get("/dashboard/equity-curve")
        for point in resp.json():
            EquityPoint(**point)


# ─── Rolling Metrics Tests ──────────────────────────────────────────


class TestRollingMetricsEndpoint:
    """Tests for GET /dashboard/rolling-metrics."""

    def test_empty_db(self, client):
        """Empty database returns empty list."""
        resp = client.get("/dashboard/rolling-metrics")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_fewer_than_window(self, client, db):
        """Fewer trades than window_size returns empty list."""
        for i in range(5):
            _insert_trade(db, f"t{i}", pnl=10.0, timestamp=f"2026-03-0{i+1}T10:00:00Z")

        resp = client.get("/dashboard/rolling-metrics?window_size=10")
        assert resp.json() == []

    def test_happy_path(self, client, db):
        """10 trades with window=5 produces correct rolling stats."""
        pnls = [100, -30, 50, -20, 80, 40, -10, 60, -15, 90]
        for i, pnl in enumerate(pnls):
            _insert_trade(
                db, f"t{i}", pnl=float(pnl), pnl_r=pnl / 100.0,
                timestamp=f"2026-03-{i+1:02d}T10:00:00Z"
            )

        resp = client.get("/dashboard/rolling-metrics?window_size=5")
        data = resp.json()
        # 10 trades, window 5 → 6 data points (indices 5..10)
        assert len(data) == 6

        # First window: trades 0-4 = [100, -30, 50, -20, 80]
        first = data[0]
        assert first["window_size"] == 5
        # wins: 100, 50, 80 = 3. loss: -30, -20 = 2. wr = 3/5 = 0.6
        assert first["rolling_wr"] == pytest.approx(0.6)
        # pf = (100+50+80) / (30+20) = 230/50 = 4.6
        assert first["rolling_pf"] == pytest.approx(4.6)
        # avg_r = mean(1.0, -0.3, 0.5, -0.2, 0.8) = 1.8/5 = 0.36
        assert first["rolling_avg_r"] == pytest.approx(0.36)

    def test_all_wins_in_window(self, client, db):
        """Window with all positive PnL → pf = 9999.99 (JSON-safe sentinel)."""
        for i in range(3):
            _insert_trade(
                db, f"t{i}", pnl=50.0,
                timestamp=f"2026-03-0{i+1}T10:00:00Z"
            )

        resp = client.get("/dashboard/rolling-metrics?window_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rolling_wr"] == 1.0
        assert data[0]["rolling_pf"] == 9999.99

    def test_no_pnl_r(self, client, db):
        """Trades without pnl_r → rolling_avg_r = 0."""
        for i in range(5):
            _insert_trade(
                db, f"t{i}", pnl=10.0, pnl_r=None,
                timestamp=f"2026-03-0{i+1}T10:00:00Z"
            )

        resp = client.get("/dashboard/rolling-metrics?window_size=3")
        data = resp.json()
        assert len(data) == 3
        assert data[0]["rolling_avg_r"] == 0.0

    def test_custom_window_size(self, client, db):
        """Custom window_size param works."""
        for i in range(6):
            _insert_trade(
                db, f"t{i}", pnl=10.0 if i % 2 == 0 else -5.0,
                timestamp=f"2026-03-{i+1:02d}T10:00:00Z"
            )

        resp = client.get("/dashboard/rolling-metrics?window_size=3")
        data = resp.json()
        assert len(data) == 4  # 6 trades, window 3 → 4 points
        assert all(p["window_size"] == 3 for p in data)

    def test_response_schema(self, client, db):
        """Response validates against RollingMetricPoint model."""
        for i in range(5):
            _insert_trade(db, f"t{i}", pnl=10.0, timestamp=f"2026-03-0{i+1}T10:00:00Z")

        resp = client.get("/dashboard/rolling-metrics?window_size=3")
        for point in resp.json():
            RollingMetricPoint(**point)


# ─── Memory Growth Tests ────────────────────────────────────────────


class TestMemoryGrowthEndpoint:
    """Tests for GET /dashboard/memory-growth."""

    def test_empty_db(self, client):
        """Empty database returns empty list."""
        resp = client.get("/dashboard/memory-growth")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_happy_path(self, client, db):
        """Multiple memories across dates and regimes."""
        _insert_episodic(db, "m1", regime="trending_up", created_at="2026-03-01T10:00:00Z")
        _insert_episodic(db, "m2", regime="trending_up", created_at="2026-03-01T12:00:00Z")
        _insert_episodic(db, "m3", regime="ranging", created_at="2026-03-01T14:00:00Z")
        _insert_episodic(db, "m4", regime="volatile", created_at="2026-03-02T10:00:00Z")

        resp = client.get("/dashboard/memory-growth")
        data = resp.json()
        assert len(data) == 2

        day1 = data[0]
        assert day1["date"] == "2026-03-01"
        assert day1["total_memories"] == 3  # cumulative
        assert day1["trending_up"] == 2
        assert day1["ranging"] == 1
        assert day1["volatile"] == 0

        day2 = data[1]
        assert day2["date"] == "2026-03-02"
        assert day2["total_memories"] == 4  # cumulative
        assert day2["volatile"] == 1

    def test_single_memory(self, client, db):
        """Single memory edge case."""
        _insert_episodic(db, "m1", regime="trending_down")

        resp = client.get("/dashboard/memory-growth")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["total_memories"] == 1
        assert data[0]["trending_down"] == 1

    def test_null_regime_becomes_unknown(self, client, db):
        """NULL context_regime is counted as 'unknown'."""
        _insert_episodic(db, "m1", regime=None, created_at="2026-03-01T10:00:00Z")

        resp = client.get("/dashboard/memory-growth")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["unknown"] == 1

    def test_unrecognized_regime_becomes_unknown(self, client, db):
        """Unrecognized regime string is counted as 'unknown'."""
        _insert_episodic(db, "m1", regime="some_new_regime", created_at="2026-03-01T10:00:00Z")

        resp = client.get("/dashboard/memory-growth")
        data = resp.json()
        assert data[0]["unknown"] == 1

    def test_cumulative_total(self, client, db):
        """total_memories is cumulative across dates."""
        _insert_episodic(db, "m1", created_at="2026-03-01T10:00:00Z")
        _insert_episodic(db, "m2", created_at="2026-03-01T12:00:00Z")
        _insert_episodic(db, "m3", created_at="2026-03-02T10:00:00Z")
        _insert_episodic(db, "m4", created_at="2026-03-03T10:00:00Z")
        _insert_episodic(db, "m5", created_at="2026-03-03T12:00:00Z")

        resp = client.get("/dashboard/memory-growth")
        data = resp.json()
        totals = [d["total_memories"] for d in data]
        assert totals == [2, 3, 5]

    def test_response_schema(self, client, db):
        """Response validates against MemoryGrowthPoint model."""
        _insert_episodic(db, "m1")
        resp = client.get("/dashboard/memory-growth")
        for point in resp.json():
            MemoryGrowthPoint(**point)


# ─── Service Unit Tests ─────────────────────────────────────────────


class TestEquityCurveService:
    """Unit tests for DashboardService.get_equity_curve (no HTTP)."""

    def test_empty(self, service):
        """Empty DB returns empty list."""
        assert service.get_equity_curve() == []

    def test_drawdown_calculation(self, db, service):
        """Drawdown is computed as (peak - current) / peak * 100."""
        _insert_trade(db, "t1", pnl=200.0, timestamp="2026-03-01T10:00:00Z")
        _insert_trade(db, "t2", pnl=-50.0, timestamp="2026-03-02T10:00:00Z")

        result = service.get_equity_curve()
        # Day 1: cum=200, peak=200, dd=0
        assert result[0]["drawdown_pct"] == 0.0
        # Day 2: cum=150, peak=200, dd=(200-150)/200*100 = 25%
        assert result[1]["drawdown_pct"] == 25.0

    def test_strategy_filter(self, db, service):
        """Strategy filter only includes matching trades."""
        _insert_trade(db, "t1", pnl=100.0, strategy="VB")
        _insert_trade(db, "t2", pnl=50.0, strategy="IM")

        result = service.get_equity_curve(strategy="VB")
        assert len(result) == 1
        assert result[0]["cumulative_pnl"] == 100.0


class TestRollingMetricsService:
    """Unit tests for DashboardService.get_rolling_metrics (no HTTP)."""

    def test_empty(self, service):
        """Empty DB returns empty list."""
        assert service.get_rolling_metrics() == []

    def test_exact_window_size(self, db, service):
        """Exactly window_size trades produces 1 data point."""
        for i in range(5):
            _insert_trade(db, f"t{i}", pnl=10.0, timestamp=f"2026-03-0{i+1}T10:00:00Z")

        result = service.get_rolling_metrics(window_size=5)
        assert len(result) == 1


class TestMemoryGrowthService:
    """Unit tests for DashboardService.get_memory_growth (no HTTP)."""

    def test_empty(self, service):
        """Empty DB returns empty list."""
        assert service.get_memory_growth() == []

    def test_all_regimes(self, db, service):
        """All known regimes are counted correctly."""
        for i, regime in enumerate(["trending_up", "trending_down", "ranging", "volatile", "unknown"]):
            _insert_episodic(db, f"m{i}", regime=regime)

        result = service.get_memory_growth()
        assert len(result) == 1
        assert result[0]["trending_up"] == 1
        assert result[0]["trending_down"] == 1
        assert result[0]["ranging"] == 1
        assert result[0]["volatile"] == 1
        assert result[0]["unknown"] == 1
        assert result[0]["total_memories"] == 5
