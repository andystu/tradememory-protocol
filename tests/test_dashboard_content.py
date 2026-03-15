"""Tests for content + dream dashboard endpoints.

Covers: reflections, adjustments, beliefs, dream-results.
Each endpoint has happy path, empty, and edge case tests.
"""

import json
import pytest
from fastapi.testclient import TestClient

from tradememory.db import Database
from tradememory.dashboard_models import (
    AdjustmentEvent,
    BeliefState,
    DreamSession,
    ReflectionSummary,
)
from tradememory.repositories.trade import TradeRepository
from tradememory.services.dashboard import DashboardService


@pytest.fixture
def db(tmp_path):
    """Create a temp SQLite database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def client(db):
    """TestClient with dashboard_api wired to temp DB."""
    from tradememory.server import app
    from tradememory.dashboard_api import get_trade_repository

    def override_repo():
        return TradeRepository(db=db)

    app.dependency_overrides[get_trade_repository] = override_repo
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def service(db):
    """DashboardService wired to temp DB for unit tests."""
    return DashboardService(repo=TradeRepository(db=db))


# ─── Helpers ─────────────────────────────────────────────────────


def _insert_adjustment(db, adj_id, parameter="RR_Ratio", old_val="1.5", new_val="3.5",
                       adj_type="parameter_change", reason="Backtest shows better RR",
                       status="proposed", created_at="2026-03-01T10:00:00Z",
                       pattern_id=None):
    """Helper to insert a strategy adjustment."""
    conn = db._get_connection()
    try:
        if pattern_id:
            conn.execute(
                """INSERT INTO patterns
                (pattern_id, pattern_type, description, confidence, sample_size,
                 date_range, strategy, metrics, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pattern_id, "session", "test pattern", 0.8, 50,
                 "2025-01-2026-02", "VolBreakout", "{}", "2026-03-01T00:00:00Z"),
            )
        conn.execute(
            """INSERT INTO strategy_adjustments
            (adjustment_id, adjustment_type, parameter, old_value, new_value,
             reason, source_pattern_id, confidence, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (adj_id, adj_type, parameter, old_val, new_val,
             reason, pattern_id, 0.85, status, created_at),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_belief(db, belief_id, proposition="VB wins in trending markets",
                   alpha=8.0, beta=2.0, sample_size=10, strategy="VolBreakout",
                   regime="trending_up", last_confirmed=None, last_contradicted=None):
    """Helper to insert a semantic memory (belief)."""
    conn = db._get_connection()
    try:
        conn.execute(
            """INSERT INTO semantic_memory
            (id, proposition, alpha, beta, sample_size, strategy, regime,
             last_confirmed, last_contradicted, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (belief_id, proposition, alpha, beta, sample_size, strategy, regime,
             last_confirmed, last_contradicted, "backtest",
             "2026-03-01T00:00:00Z", "2026-03-01T00:00:00Z"),
        )
        conn.commit()
    finally:
        conn.close()


# ─── Reflections Tests ───────────────────────────────────────────


class TestReflections:
    """Tests for GET /dashboard/reflections."""

    def test_empty_no_directory(self, service):
        """Returns empty list when reviews dir doesn't exist."""
        from pathlib import Path
        result = service.get_reflections(reviews_dir=Path("/nonexistent/path"))
        assert result == []

    def test_happy_path_with_temp_files(self, service, tmp_path):
        """Parses markdown files correctly."""
        reviews_dir = tmp_path / "daily_reviews"
        reviews_dir.mkdir()

        (reviews_dir / "2026-03-01.md").write_text(
            "# Daily Review\nGrade: A\n\nVolBreakout had a strong day...",
            encoding="utf-8",
        )
        (reviews_dir / "2026-03-02.md").write_text(
            "# Daily Review\nGrade: B\n\nIntradayMomentum triggered twice...",
            encoding="utf-8",
        )

        result = service.get_reflections(reviews_dir=reviews_dir)
        assert len(result) == 2
        # Sorted by date DESC
        assert result[0]["date"] == "2026-03-02"
        assert result[1]["date"] == "2026-03-01"
        # Grade parsing
        assert result[0]["grade"] == "B"
        assert result[1]["grade"] == "A"
        # Strategy detection
        assert result[0]["strategy"] == "IntradayMomentum"
        assert result[1]["strategy"] == "VolBreakout"

    def test_date_filter(self, service, tmp_path):
        """Start/end date filters work."""
        reviews_dir = tmp_path / "daily_reviews"
        reviews_dir.mkdir()

        for d in ["2026-03-01", "2026-03-02", "2026-03-03"]:
            (reviews_dir / f"{d}.md").write_text(f"Review for {d}", encoding="utf-8")

        result = service.get_reflections(
            start_date="2026-03-02", end_date="2026-03-02", reviews_dir=reviews_dir
        )
        assert len(result) == 1
        assert result[0]["date"] == "2026-03-02"

    def test_no_grade_returns_none(self, service, tmp_path):
        """Files without Grade: line return grade=None."""
        reviews_dir = tmp_path / "daily_reviews"
        reviews_dir.mkdir()
        (reviews_dir / "2026-03-01.md").write_text("No grade here.", encoding="utf-8")

        result = service.get_reflections(reviews_dir=reviews_dir)
        assert len(result) == 1
        assert result[0]["grade"] is None

    def test_skips_non_date_files(self, service, tmp_path):
        """Files not matching YYYY-MM-DD.md are skipped."""
        reviews_dir = tmp_path / "daily_reviews"
        reviews_dir.mkdir()
        (reviews_dir / "README.md").write_text("Not a review", encoding="utf-8")
        (reviews_dir / "2026-03-01.md").write_text("Grade: C\nReview", encoding="utf-8")

        result = service.get_reflections(reviews_dir=reviews_dir)
        assert len(result) == 1
        assert result[0]["date"] == "2026-03-01"

    def test_api_endpoint_returns_list(self, client):
        """API returns 200 with a list (may have real data or be empty)."""
        resp = client.get("/dashboard/reflections")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_response_schema(self, service, tmp_path):
        """Response validates against ReflectionSummary model."""
        reviews_dir = tmp_path / "daily_reviews"
        reviews_dir.mkdir()
        (reviews_dir / "2026-03-01.md").write_text("Grade: A\nTest", encoding="utf-8")

        for item in service.get_reflections(reviews_dir=reviews_dir):
            ReflectionSummary(**item)


# ─── Adjustments Tests ───────────────────────────────────────────


class TestAdjustments:
    """Tests for GET /dashboard/adjustments."""

    def test_empty_db(self, client):
        """Empty database returns empty list."""
        resp = client.get("/dashboard/adjustments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_happy_path(self, client, db):
        """Returns adjustments sorted by created_at DESC."""
        _insert_adjustment(db, "adj1", created_at="2026-03-01T10:00:00Z",
                           pattern_id="p1")
        _insert_adjustment(db, "adj2", created_at="2026-03-02T10:00:00Z",
                           parameter="Threshold", old_val="0.6", new_val="0.55")

        resp = client.get("/dashboard/adjustments")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # DESC order
        assert data[0]["id"] == "adj2"
        assert data[1]["id"] == "adj1"
        # Strategy from joined pattern
        assert data[1]["strategy"] == "VolBreakout"

    def test_response_schema(self, client, db):
        """Response validates against AdjustmentEvent model."""
        _insert_adjustment(db, "adj1")
        resp = client.get("/dashboard/adjustments")
        for item in resp.json():
            AdjustmentEvent(**item)


# ─── Beliefs Tests ───────────────────────────────────────────────


class TestBeliefs:
    """Tests for GET /dashboard/beliefs."""

    def test_empty_db(self, client):
        """Empty database returns empty list."""
        resp = client.get("/dashboard/beliefs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_happy_path(self, client, db):
        """Returns beliefs with computed confidence and trend."""
        _insert_belief(db, "b1", alpha=8.0, beta=2.0, sample_size=10,
                       last_confirmed="2026-03-02T00:00:00Z",
                       last_contradicted="2026-03-01T00:00:00Z")
        _insert_belief(db, "b2", alpha=3.0, beta=7.0, sample_size=5,
                       last_confirmed="2026-03-01T00:00:00Z",
                       last_contradicted="2026-03-02T00:00:00Z")

        resp = client.get("/dashboard/beliefs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        # Sorted by sample_size DESC
        assert data[0]["id"] == "b1"
        assert data[1]["id"] == "b2"

        # Confidence = alpha / (alpha + beta)
        assert data[0]["confidence"] == pytest.approx(0.8, abs=0.01)
        assert data[1]["confidence"] == pytest.approx(0.3, abs=0.01)

        # Trend: b1 confirmed > contradicted = improving
        assert data[0]["trend"] == "improving"
        # b2 contradicted > confirmed = declining
        assert data[1]["trend"] == "declining"

    def test_trend_stable(self, service, db):
        """Belief with no confirmed/contradicted = stable."""
        _insert_belief(db, "b1", last_confirmed=None, last_contradicted=None)
        result = service.get_beliefs()
        assert result[0]["trend"] == "stable"

    def test_response_schema(self, client, db):
        """Response validates against BeliefState model."""
        _insert_belief(db, "b1")
        resp = client.get("/dashboard/beliefs")
        for item in resp.json():
            BeliefState(**item)


# ─── Dream Results Tests ─────────────────────────────────────────


class TestDreamResults:
    """Tests for GET /dashboard/dream-results."""

    def test_empty_no_directory(self, service):
        """Returns empty list when dream data path doesn't exist."""
        from pathlib import Path
        result = service.get_dream_results(dream_path=Path("/nonexistent/path"))
        assert result == []

    def test_empty_no_json_files(self, service, tmp_path):
        """Returns empty list when directory has no JSON files."""
        result = service.get_dream_results(dream_path=tmp_path)
        assert result == []

    def test_happy_path_with_json(self, service, tmp_path):
        """Parses dream session JSON files."""
        dream_data = {
            "id": "dream-001",
            "timestamp": "2026-03-01T12:00:00Z",
            "condition": "trending_up",
            "trades": 50,
            "pf": 1.85,
            "pnl": 1200.50,
            "wr": 0.62,
            "has_memory": True,
            "memory_type": "episodic",
            "resonance_detected": True,
        }
        (tmp_path / "session_001.json").write_text(
            json.dumps(dream_data), encoding="utf-8"
        )

        result = service.get_dream_results(dream_path=tmp_path)
        assert len(result) == 1
        assert result[0]["id"] == "dream-001"
        assert result[0]["pf"] == 1.85
        assert result[0]["resonance_detected"] is True

    def test_api_endpoint_empty(self, client, monkeypatch):
        """API returns empty list when dream path doesn't exist."""
        monkeypatch.setenv("DREAM_DATA_PATH", "/nonexistent/dream/path")
        resp = client.get("/dashboard/dream-results")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_malformed_json_skipped(self, service, tmp_path):
        """Malformed JSON files are skipped with warning, not 500."""
        (tmp_path / "bad.json").write_text("not valid json", encoding="utf-8")
        (tmp_path / "good.json").write_text(
            json.dumps({"id": "ok", "timestamp": "", "condition": "test",
                        "trades": 1, "pf": 1.0, "pnl": 0, "wr": 0.5,
                        "has_memory": False, "resonance_detected": False}),
            encoding="utf-8",
        )

        result = service.get_dream_results(dream_path=tmp_path)
        assert len(result) == 1
        assert result[0]["id"] == "ok"

    def test_response_schema(self, service, tmp_path):
        """Response validates against DreamSession model."""
        (tmp_path / "s.json").write_text(
            json.dumps({"id": "d1", "timestamp": "2026-03-01", "condition": "x",
                        "trades": 10, "pf": 1.0, "pnl": 100, "wr": 0.5,
                        "has_memory": True, "memory_type": "semantic",
                        "resonance_detected": False}),
            encoding="utf-8",
        )
        for item in service.get_dream_results(dream_path=tmp_path):
            DreamSession(**item)
