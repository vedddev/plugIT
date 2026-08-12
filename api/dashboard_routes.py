"""Admin-only dashboard endpoints backed by the application SQLite database."""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from api.admin_routes import require_admin
from database.dashboard import recent as recent_requests
from database.dashboard import stats, usage


DashboardPeriod = Literal["today", "7d", "30d", "all"]
router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def dashboard_stats(period: DashboardPeriod = Query("today")):
    """Return totals, cache metrics, and average latency for a time period."""
    return stats(period)


@router.get("/usage")
def dashboard_usage(period: DashboardPeriod = Query("today")):
    """Return provider and model usage groups for a time period."""
    return usage(period)


@router.get("/recent")
def dashboard_recent(
    period: DashboardPeriod = Query("today"),
    limit: int = Query(20, ge=1, le=100),
):
    """Return the newest application request events, newest first."""
    return {"period": period, "data": recent_requests(period, limit)}
