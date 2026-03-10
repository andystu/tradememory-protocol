"""
Dashboard API router — request/response layer only.

All business logic lives in services/dashboard.py.
All data access lives in repositories/trade.py.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .dashboard_models import (
    AdjustmentEvent,
    BeliefState,
    CalibrationPoint,
    DreamSession,
    EquityPoint,
    MemoryGrowthPoint,
    OWMScorePoint,
    OverviewResponse,
    ReflectionSummary,
    RollingMetricPoint,
    StrategyDetailResponse,
)
from .exceptions import DatabaseConnectionError, DatabaseQueryError, StrategyNotFoundError
from .repositories.trade import TradeRepository
from .services.dashboard import DashboardService

logger = logging.getLogger(__name__)

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_trade_repository() -> TradeRepository:
    return TradeRepository()


def get_dashboard_service(
    repo: TradeRepository = Depends(get_trade_repository),
) -> DashboardService:
    return DashboardService(repo=repo)


@dashboard_router.get("/overview", response_model=OverviewResponse)
async def overview(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get dashboard overview with key trading metrics."""
    try:
        return service.get_overview()
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query trading data"
        )


@dashboard_router.get("/equity-curve", response_model=List[EquityPoint])
async def equity_curve(
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get equity curve with cumulative PnL and drawdown per day."""
    try:
        return service.get_equity_curve(
            start_date=start_date, end_date=end_date, strategy=strategy
        )
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query equity curve"
        )


@dashboard_router.get("/rolling-metrics", response_model=List[RollingMetricPoint])
async def rolling_metrics(
    window_size: int = Query(10, ge=2, description="Rolling window size in trades"),
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    strategy: Optional[str] = Query(None, description="Filter by strategy name"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get rolling performance metrics over a sliding window of trades."""
    try:
        return service.get_rolling_metrics(
            window_size=window_size,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
        )
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query rolling metrics"
        )


@dashboard_router.get("/memory-growth", response_model=List[MemoryGrowthPoint])
async def memory_growth(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get memory growth over time, broken down by market regime."""
    try:
        return service.get_memory_growth()
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query memory growth"
        )


@dashboard_router.get("/owm-score-trend", response_model=List[OWMScorePoint])
async def owm_score_trend():
    """Get OWM recall score trend grouped by day.

    Queries recall_events from PostgreSQL. Returns empty list if
    PostgreSQL is unavailable or table is empty — this is expected
    until Task 8 hybrid recall is live.
    """
    try:
        from .database import get_async_session
        from sqlalchemy import text

        async with get_async_session() as session:
            result = await session.execute(text("""
                SELECT
                    DATE(timestamp) as date,
                    AVG(avg_total) as avg_total,
                    AVG(avg_q) as avg_q,
                    AVG(avg_sim) as avg_sim,
                    AVG(avg_rec) as avg_rec,
                    AVG(avg_conf) as avg_conf,
                    AVG(avg_aff) as avg_aff,
                    COUNT(*) as query_count
                FROM recall_events
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp) ASC
            """))
            rows = result.fetchall()
            return [
                {
                    "date": str(r.date),
                    "avg_total": round(r.avg_total, 6),
                    "avg_q": round(r.avg_q, 6),
                    "avg_sim": round(r.avg_sim, 6),
                    "avg_rec": round(r.avg_rec, 6),
                    "avg_conf": round(r.avg_conf, 6),
                    "avg_aff": round(r.avg_aff, 6),
                    "query_count": r.query_count,
                }
                for r in rows
            ]
    except Exception as e:
        logger.warning(f"OWM score trend unavailable (expected if no PG): {e}")
        return []


@dashboard_router.get("/confidence-cal", response_model=List[CalibrationPoint])
async def confidence_calibration(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get confidence calibration data for scatter plot."""
    try:
        return service.get_confidence_calibration()
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query calibration data"
        )


@dashboard_router.get("/strategy/{name}", response_model=StrategyDetailResponse)
async def strategy_detail(
    name: str,
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get detailed strategy performance and session heatmap."""
    try:
        return service.get_strategy_detail(name)
    except StrategyNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{name}' not found"
        )
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query strategy detail"
        )


@dashboard_router.get("/reflections", response_model=List[ReflectionSummary])
async def reflections(
    start_date: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get daily review reflections parsed from markdown files."""
    try:
        return service.get_reflections(start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error(f"Failed to load reflections: {e}")
        raise HTTPException(status_code=500, detail="Failed to load reflections")


@dashboard_router.get("/adjustments", response_model=List[AdjustmentEvent])
async def adjustments(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get strategy adjustment events from L3 layer."""
    try:
        return service.get_adjustments()
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query adjustments"
        )


@dashboard_router.get("/beliefs", response_model=List[BeliefState])
async def beliefs(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get Bayesian beliefs from semantic memory."""
    try:
        return service.get_beliefs()
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(
            status_code=503, detail="Database temporarily unavailable"
        )
    except DatabaseQueryError as e:
        logger.error(f"Database query error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to query beliefs"
        )


@dashboard_router.get("/dream-results", response_model=List[DreamSession])
async def dream_results(
    service: DashboardService = Depends(get_dashboard_service),
):
    """Get trade dreaming simulation results.

    Returns empty list if dream data path doesn't exist — this is
    expected until Trade Dreaming Phase 2 is implemented.
    """
    try:
        return service.get_dream_results()
    except Exception as e:
        logger.error(f"Failed to load dream results: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dream results")
