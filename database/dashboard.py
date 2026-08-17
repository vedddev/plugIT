"""Read and write operations for the SmartLLM dashboard."""

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from database.connection import session


DashboardPeriod = Literal["today", "7d", "30d", "all"]
PERIODS = {"today", "7d", "30d", "all"}


def period_start(period: DashboardPeriod) -> str | None:
    now = datetime.now(timezone.utc)
    if period == "all":
        return None
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    return (now - timedelta(days=7 if period == "7d" else 30)).isoformat().replace("+00:00", "Z")


def _where(user_id: str, period: DashboardPeriod) -> tuple[str, tuple]:
    start = period_start(period)
    return (" WHERE user_id = ?", (user_id,)) if start is None else (" WHERE user_id = ? AND created_at >= ?", (user_id, start))


def record_request(
    *,
    api_key_id: str,
    user_id: str = "legacy-system",
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    latency_ms: float,
    cost: float,
    cached: bool,
    success: bool,
    database_url: str | None = None,
    created_at: str | None = None,
) -> None:
    """Persist a future request event and its all-time per-key summary."""
    created_at = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with session(database_url) as connection:
        connection.execute(
            """INSERT INTO request_events
               (id, api_key_id, user_id, input_tokens, output_tokens, total_tokens, cost,
                success, created_at, provider, model, latency_ms, cached)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), api_key_id, user_id, input_tokens, output_tokens, total_tokens, cost,
             int(success), created_at, provider, model, latency_ms, int(cached)),
        )
        connection.execute(
            """INSERT INTO usage_summaries
               (api_key_id, user_id, requests, successful_requests, failed_requests, input_tokens,
                output_tokens, total_tokens, cost, last_request_at)
               VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(api_key_id) DO UPDATE SET
                 requests = requests + 1,
                 successful_requests = successful_requests + excluded.successful_requests,
                 failed_requests = failed_requests + excluded.failed_requests,
                 input_tokens = input_tokens + excluded.input_tokens,
                 output_tokens = output_tokens + excluded.output_tokens,
                 total_tokens = total_tokens + excluded.total_tokens,
                 cost = cost + excluded.cost,
                 last_request_at = excluded.last_request_at""",
            (api_key_id, user_id, int(success), int(not success), input_tokens, output_tokens,
             total_tokens, cost, created_at),
        )


def stats(user_id: str, period: DashboardPeriod = "today", database_url: str | None = None) -> dict:
    where, params = _where(user_id, period)
    query = f"""SELECT COUNT(*) AS total_requests,
                       COALESCE(SUM(success), 0) AS successful_requests,
                       COALESCE(SUM(1 - success), 0) AS failed_requests,
                       COALESCE(SUM(input_tokens), 0) AS total_input_tokens,
                       COALESCE(SUM(output_tokens), 0) AS total_output_tokens,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(cost), 0) AS total_cost,
                       COALESCE(AVG(latency_ms), 0) AS average_latency,
                       COALESCE(SUM(CASE WHEN cached = 1 THEN 1 ELSE 0 END), 0) AS cache_hits,
                       COALESCE(SUM(CASE WHEN cached = 0 THEN 1 ELSE 0 END), 0) AS cache_misses
                FROM request_events{where}"""
    with session(database_url) as connection:
        row = dict(connection.execute(query, params).fetchone())
        today_requests = connection.execute(
            "SELECT COUNT(*) FROM request_events WHERE user_id = ? AND created_at >= ?",
            (user_id, period_start("today")),
        ).fetchone()[0]
    row["total_cost"] = round(float(row["total_cost"]), 12)
    cache_recorded = row["cache_hits"] + row["cache_misses"]
    row["cache_hit_rate"] = (row["cache_hits"] / cache_recorded) if cache_recorded else 0.0
    return {"period": period, "requests_today": today_requests, **row}


def usage(user_id: str, period: DashboardPeriod = "today", database_url: str | None = None) -> dict:
    where, params = _where(user_id, period)
    def query(field: str) -> str:
        filter_sql = f"{where} AND {field} IS NOT NULL" if where else f" WHERE {field} IS NOT NULL"
        return f"""SELECT {field} AS name, COUNT(*) AS requests,
                                      COALESCE(SUM(total_tokens), 0) AS total_tokens,
                                      COALESCE(SUM(cost), 0) AS total_cost
                               FROM request_events{filter_sql} GROUP BY {field} ORDER BY requests DESC, name ASC"""
    with session(database_url) as connection:
        providers = [dict(row) for row in connection.execute(query("provider"), params)]
        models = [dict(row) for row in connection.execute(query("model"), params)]
        # ISO-8601 timestamps sort correctly as strings, so this works for the
        # UTC timestamps stored by the tracker and keeps the existing API shape.
        time_series = [dict(row) for row in connection.execute(
            f"""SELECT substr(created_at, 1, 10) AS date,
                       COUNT(*) AS requests,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(cost), 0) AS total_cost
                FROM request_events{where}
                GROUP BY substr(created_at, 1, 10) ORDER BY date ASC""",
            params,
        )]
    return {
        "period": period,
        "provider_usage": providers,
        "model_usage": models,
        "time_series": time_series,
    }


def recent(user_id: str, period: DashboardPeriod = "today", limit: int = 20, database_url: str | None = None) -> list[dict]:
    where, params = _where(user_id, period)
    query = f"""SELECT id, api_key_id, provider, model, input_tokens, output_tokens,
                       total_tokens, cost, success, latency_ms, cached, created_at
                FROM request_events{where} ORDER BY created_at DESC LIMIT ?"""
    with session(database_url) as connection:
        return [{**dict(row), "success": bool(row["success"]), "cached": bool(row["cached"])}
                for row in connection.execute(query, (*params, limit))]


def list_requests(
    *,
    period: DashboardPeriod = "all",
    user_id: str,
    provider: str | None = None,
    model: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    database_url: str | None = None,
) -> dict:
    """Return a paginated, filtered request-events page for the admin UI."""
    clauses: list[str] = ["user_id = ?"]
    params: list = [user_id]
    if period and period != "all":
        start = period_start(period)
        clauses.append("created_at >= ?")
        params.append(start)
    if provider:
        clauses.append("provider = ?")
        params.append(provider)
    if model:
        clauses.append("model = ?")
        params.append(model)
    if status == "success":
        clauses.append("success = 1")
    elif status == "failed":
        clauses.append("success = 0")
    elif status == "cached":
        clauses.append("cached = 1")
    if search:
        clauses.append("(CAST(id AS TEXT) LIKE ? OR api_key_id LIKE ? OR CAST(provider AS TEXT) LIKE ? OR CAST(model AS TEXT) LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with session(database_url) as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM request_events{where_sql}", tuple(params)
        ).fetchone()[0]
        rows = connection.execute(
            f"""SELECT id, api_key_id, provider, model, input_tokens, output_tokens,
                       total_tokens, cost, success, latency_ms, cached, created_at
                FROM request_events{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        ).fetchall()
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "data": [
            {**dict(row), "success": bool(row["success"]), "cached": bool(row["cached"])}
            for row in rows
        ],
    }


def request_detail(request_id: str, user_id: str, database_url: str | None = None) -> dict | None:
    """Return a single request event with derived fields, or None if missing."""
    with session(database_url) as connection:
        row = connection.execute(
            """SELECT id, api_key_id, provider, model, input_tokens, output_tokens,
                      total_tokens, cost, success, latency_ms, cached, created_at
               FROM request_events WHERE id = ? AND user_id = ?""",
            (request_id, user_id),
        ).fetchone()
    if row is None:
        return None
    record = {**dict(row), "success": bool(row["success"]), "cached": bool(row["cached"])}
    # Provide a task hint derived from the routed model. ``task`` itself is not
    # stored today, so the frontend can use the model name as a label.
    return record


def provider_breakdown(user_id: str, period: DashboardPeriod = "all", database_url: str | None = None) -> list[dict]:
    """Per-provider aggregates (requests, tokens, cost, latency, error rate)."""
    where, params = _where(user_id, period)
    filter_sql = f"{where} AND provider IS NOT NULL" if where else " WHERE provider IS NOT NULL"
    with session(database_url) as connection:
        rows = connection.execute(
            f"""SELECT provider AS name,
                       COUNT(*) AS requests,
                       COALESCE(SUM(success), 0) AS successful_requests,
                       COALESCE(SUM(1 - success), 0) AS failed_requests,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(cost), 0) AS total_cost,
                       COALESCE(AVG(latency_ms), 0) AS average_latency
                FROM request_events{filter_sql}
                GROUP BY provider ORDER BY requests DESC, name ASC""",
            params,
        ).fetchall()
    return [
        {
            "name": row["name"],
            "requests": int(row["requests"]),
            "successful_requests": int(row["successful_requests"]),
            "failed_requests": int(row["failed_requests"]),
            "total_tokens": int(row["total_tokens"]),
            "total_cost": round(float(row["total_cost"]), 12),
            "average_latency": float(row["average_latency"] or 0),
            "error_rate": (row["failed_requests"] / row["requests"]) if row["requests"] else 0.0,
        }
        for row in rows
    ]


def model_breakdown(user_id: str, period: DashboardPeriod = "all", database_url: str | None = None) -> list[dict]:
    """Per-model aggregates (requests, tokens, cost, latency, error rate)."""
    where, params = _where(user_id, period)
    filter_sql = f"{where} AND model IS NOT NULL" if where else " WHERE model IS NOT NULL"
    with session(database_url) as connection:
        rows = connection.execute(
            f"""SELECT model AS name,
                       provider AS provider,
                       COUNT(*) AS requests,
                       COALESCE(SUM(success), 0) AS successful_requests,
                       COALESCE(SUM(1 - success), 0) AS failed_requests,
                       COALESCE(SUM(input_tokens), 0) AS input_tokens,
                       COALESCE(SUM(output_tokens), 0) AS output_tokens,
                       COALESCE(SUM(total_tokens), 0) AS total_tokens,
                       COALESCE(SUM(cost), 0) AS total_cost,
                       COALESCE(AVG(latency_ms), 0) AS average_latency
                FROM request_events{filter_sql}
                GROUP BY model, provider ORDER BY requests DESC, name ASC""",
            params,
        ).fetchall()
    return [
        {
            "name": row["name"],
            "provider": row["provider"],
            "requests": int(row["requests"]),
            "successful_requests": int(row["successful_requests"]),
            "failed_requests": int(row["failed_requests"]),
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "total_tokens": int(row["total_tokens"]),
            "total_cost": round(float(row["total_cost"]), 12),
            "average_latency": float(row["average_latency"] or 0),
            "error_rate": (row["failed_requests"] / row["requests"]) if row["requests"] else 0.0,
        }
        for row in rows
    ]


def distinct_providers(user_id: str, database_url: str | None = None) -> list[str]:
    """All distinct provider names recorded in request events."""
    with session(database_url) as connection:
        rows = connection.execute(
            "SELECT DISTINCT provider FROM request_events WHERE user_id = ? AND provider IS NOT NULL ORDER BY provider ASC", (user_id,)
        ).fetchall()
    return [row["provider"] for row in rows]


def distinct_models(user_id: str, database_url: str | None = None) -> list[dict]:
    """All distinct model/provider pairs recorded in request events."""
    with session(database_url) as connection:
        rows = connection.execute(
            """SELECT DISTINCT model, provider FROM request_events
               WHERE user_id = ? AND model IS NOT NULL ORDER BY model ASC""", (user_id,)
        ).fetchall()
    return [{"model": row["model"], "provider": row["provider"]} for row in rows]
