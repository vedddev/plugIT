"""Admin-only dashboard endpoints backed by the application SQLite database."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import require_admin
from api.dependencies import gateway
from providers.models import PROVIDER_MODELS
from database.dashboard import (
    distinct_models,
    distinct_providers,
    list_requests,
    model_breakdown,
    provider_breakdown,
    recent as recent_requests,
    request_detail,
    stats,
    usage,
)


DashboardPeriod = Literal["today", "7d", "30d", "all"]
router = APIRouter(prefix="/dashboard", tags=["Dashboard"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def dashboard_stats(period: DashboardPeriod = Query("today"), user=Depends(require_admin)):
    """Return totals, cache metrics, and average latency for a time period."""
    return stats(user["id"], period)


@router.get("/usage")
def dashboard_usage(period: DashboardPeriod = Query("today"), user=Depends(require_admin)):
    """Return provider and model usage groups for a time period."""
    return usage(user["id"], period)


@router.get("/recent")
def dashboard_recent(
    period: DashboardPeriod = Query("today"),
    limit: int = Query(20, ge=1, le=100), user=Depends(require_admin),
):
    """Return the newest application request events, newest first."""
    return {"period": period, "data": recent_requests(user["id"], period, limit)}


@router.get("/requests")
def dashboard_requests(
    period: DashboardPeriod = Query("all"),
    provider: str | None = Query(default=None),
    model: str | None = Query(default=None),
    status: Literal["success", "failed", "cached", "all"] | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0), user=Depends(require_admin),
):
    """Return a filtered, paginated list of request events."""
    return list_requests(
        user_id=user["id"], period=period,
        provider=provider,
        model=model,
        status=status if status and status != "all" else None,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/requests/{request_id}")
def dashboard_request_detail(request_id: str, user=Depends(require_admin)):
    """Return a single request event with derived metadata."""
    record = request_detail(request_id, user["id"])
    if record is None:
        raise HTTPException(status_code=404, detail="Request event not found.")
    return record


@router.get("/providers")
def dashboard_providers(period: DashboardPeriod = Query("all"), user=Depends(require_admin)):
    """Per-provider performance and a list of registered provider names."""
    registered = sorted(gateway.registry.list())
    models_by_provider = {
        name: list(gateway.registry.get(name).list_models()) for name in registered
    }
    catalog = {name: list(PROVIDER_MODELS.get(name, ())) for name in registered}
    health = {
        name: bool(gateway.registry.get(name).health_check())
        for name in registered
    }
    metrics = provider_breakdown(user["id"], period)
    return {
        "period": period,
        "registered": registered,
        "models": models_by_provider,
        "catalog": catalog,
        "health": health,
        "metrics": metrics,
        "known_providers": sorted(set(registered) | {item["name"] for item in metrics}),
    }


@router.get("/models")
def dashboard_models(period: DashboardPeriod = Query("all"), user=Depends(require_admin)):
    """All known models (catalog + observed) and their usage aggregates."""
    catalog: dict[str, list[str]] = {}
    for provider in gateway.registry.providers.values():
        catalog.setdefault(provider.name, []).extend(provider.list_models())
    known_pairs = set()
    for provider, models in catalog.items():
        for model in models:
            known_pairs.add((model, provider))
    for item in distinct_models(user["id"]):
        known_pairs.add((item["model"], item["provider"]))
    aggregated = {(item["name"], item["provider"]): item for item in model_breakdown(user["id"], period)}
    data = []
    for (model, provider) in sorted(known_pairs, key=lambda pair: (pair[0], pair[1] or "")):
        row = aggregated.get((model, provider), {})
        data.append({
            "model": model,
            "provider": provider,
            "in_catalog": (model, provider) in {(m, p) for p, models in catalog.items() for m in models},
            "requests": int(row.get("requests", 0)),
            "input_tokens": int(row.get("input_tokens", 0)),
            "output_tokens": int(row.get("output_tokens", 0)),
            "total_tokens": int(row.get("total_tokens", 0)),
            "total_cost": float(row.get("total_cost", 0.0)),
            "average_latency": float(row.get("average_latency", 0.0)),
            "error_rate": float(row.get("error_rate", 0.0)),
        })
    return {"period": period, "data": data, "observed_providers": distinct_providers(user["id"])}


@router.get("/filters")
def dashboard_filters(user=Depends(require_admin)):
    """Distinct provider/model values to populate filter controls."""
    return {
        "providers": distinct_providers(user["id"]),
        "models": distinct_models(user["id"]),
    }
