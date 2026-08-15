import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { TopBar } from "../layouts/TopBar";
import { StatCard } from "../components/StatCard";
import { LineChart } from "../components/LineChart";
import { DataTable, type Column } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import { useToast } from "../services/toast";
import {
  formatCost,
  formatInteger,
  formatLatency,
  formatNumber,
  formatPercent,
} from "../services/format";
import type { Period, ProviderMetric, RequestEvent } from "../types/api";

export function OverviewPage() {
  const [period, setPeriod] = useState<Period>("7d");
  const toast = useToast();

  const statsAsync = useAsync(() => api.stats(period), [period]);
  const usageAsync = useAsync(() => api.usage(period), [period]);
  const providersAsync = useAsync(() => api.providers(period), [period]);
  const recentAsync = useAsync(() => api.requests({ period, limit: 10 }), [period]);

  const refresh = () => {
    statsAsync.reload();
    usageAsync.reload();
    providersAsync.reload();
    recentAsync.reload();
  };

  const handleError = (err: Error) => {
    if (err instanceof ApiError && err.isAuth) return;
    toast.show("error", "Could not load dashboard", err.message);
  };

  useEffect(() => {
    [statsAsync.error, usageAsync.error, recentAsync.error, providersAsync.error]
      .filter((error): error is Error => error !== null)
      .forEach(handleError);
  }, [statsAsync.error, usageAsync.error, recentAsync.error, providersAsync.error]);

  const stats = statsAsync.data;
  const usage = usageAsync.data;
  const recent = recentAsync.data?.data ?? [];
  const timeSeries = usage?.time_series ?? [];
  const requestsSeries = timeSeries.map((p) => ({
    label: p.date.slice(5),
    value: p.requests,
  }));
  const tokensSeries = timeSeries.map((p) => ({
    label: p.date.slice(5),
    value: p.total_tokens,
  }));
  const costSeries = timeSeries.map((p) => ({
    label: p.date.slice(5),
    value: p.total_cost,
  }));
  const hasData = Boolean(stats && stats.total_requests > 0);

  const recentColumns: Column<RequestEvent>[] = [
    {
      key: "time",
      header: "Time",
      cell: (r) => new Date(r.created_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      width: "100px",
    },
    {
      key: "provider",
      header: "Provider",
      cell: (r) => r.provider ?? "—",
      width: "120px",
    },
    {
      key: "model",
      header: "Model",
      cell: (r) => <span className="mono">{r.model ?? "—"}</span>,
    },
    {
      key: "tokens",
      header: "Tokens",
      cell: (r) => formatInteger(r.total_tokens),
      align: "right",
      width: "100px",
    },
    {
      key: "latency",
      header: "Latency",
      cell: (r) => formatLatency(r.latency_ms),
      align: "right",
      width: "100px",
    },
    {
      key: "cost",
      header: "Cost",
      cell: (r) => formatCost(r.cost),
      align: "right",
      width: "100px",
    },
    {
      key: "status",
      header: "Status",
      cell: (r) =>
        r.success ? (
          <span className="pill pill--success">
            {r.cached ? "Cached" : "Success"}
          </span>
        ) : (
          <span className="pill pill--danger">Failed</span>
        ),
      width: "100px",
    },
  ];

  return (
    <>
      <TopBar
        title="Overview"
        description="Monitor gateway traffic, usage, latency, and provider performance."
        period={period}
        onPeriodChange={setPeriod}
        onRefresh={refresh}
        loading={statsAsync.loading || usageAsync.loading}
      />
      <div className="page">
        <section className="stat-grid">
          <StatCard
            label="Requests"
            value={formatNumber(stats?.total_requests)}
            detail={`${formatInteger(stats?.requests_today)} today`}
          />
          <StatCard
            label="Tokens"
            value={formatNumber(stats?.total_tokens)}
            detail={
              <span>
                <span className="mono">{formatInteger(stats?.total_input_tokens)}</span> in ·{" "}
                <span className="mono">{formatInteger(stats?.total_output_tokens)}</span> out
              </span>
            }
          />
          <StatCard
            label="Estimated cost"
            value={formatCost(stats?.total_cost)}
            detail="Across selected period"
          />
          <StatCard
            label="Average latency"
            value={formatLatency(stats?.average_latency)}
            detail="End-to-end response time"
          />
          <StatCard
            label="Cache hit rate"
            value={formatPercent(stats?.cache_hit_rate, 1)}
            detail={
              <span>
                <span className="mono">{formatInteger(stats?.cache_hits)}</span> hits ·{" "}
                <span className="mono">{formatInteger(stats?.cache_misses)}</span> misses
              </span>
            }
          />
          <StatCard
            label="Error rate"
            value={formatPercent(errorRate(stats), 2)}
            detail={
              <span>
                <span className="mono">{formatInteger(stats?.failed_requests)}</span> failed of{" "}
                <span className="mono">{formatInteger(stats?.total_requests)}</span>
              </span>
            }
          />
        </section>

        {!hasData ? (
          <EmptyState
            title="No requests yet"
            description={`No traffic has been recorded for the ${periodLabel(period)} range. Send a chat completion through the gateway to populate this view.`}
          />
        ) : (
          <>
            <section className="chart-grid">
              <article className="card chart-card chart-card--wide">
                <header className="card__header">
                  <h2>Request volume</h2>
                  <span className="card__subtitle">Requests per day</span>
                </header>
                <LineChart
                  data={requestsSeries}
                  yFormat={(v) => formatNumber(v)}
                />
              </article>
              <article className="card chart-card">
                <header className="card__header">
                  <h2>Token usage</h2>
                  <span className="card__subtitle">Total tokens per day</span>
                </header>
                <LineChart
                  data={tokensSeries}
                  yFormat={(v) => formatNumber(v)}
                />
              </article>
            </section>

            <section className="grid-2">
              <article className="card">
                <header className="card__header">
                  <h2>Provider performance</h2>
                  <span className="card__subtitle">Aggregated by provider</span>
                </header>
                <ProviderPerformanceTable metrics={providersAsync.data?.metrics ?? []} />
              </article>
              <article className="card">
                <header className="card__header">
                  <h2>Recent requests</h2>
                  <Link className="card__action" to="/requests">
                    View all <ArrowRight size={14} />
                  </Link>
                </header>
                <DataTable
                  columns={recentColumns}
                  data={recent}
                  rowKey={(r) => r.id}
                  isLoading={recentAsync.loading}
                  emptyState="No requests in this period yet."
                />
              </article>
            </section>

            <section className="card">
              <header className="card__header">
                <h2>Cost over time</h2>
                <span className="card__subtitle">Estimated spend per day</span>
              </header>
              <LineChart
                data={costSeries}
                yFormat={(v) => formatCost(v)}
                height={160}
              />
            </section>
          </>
        )}
      </div>
    </>
  );
}

function errorRate(stats?: { total_requests?: number; failed_requests?: number } | null): number {
  if (!stats || !stats.total_requests) return 0;
  return (stats.failed_requests ?? 0) / stats.total_requests;
}

function periodLabel(period: Period): string {
  switch (period) {
    case "today":
      return "today";
    case "7d":
      return "last 7 days";
    case "30d":
      return "last 30 days";
    default:
      return "all-time";
  }
}

function ProviderPerformanceTable({ metrics }: { metrics: ProviderMetric[] }) {
  if (!metrics.length) {
    return <EmptyState title="No provider activity" description="No requests were routed to any provider in this range." />;
  }
  return (
    <DataTable
      rowKey={(row) => row.name}
      data={metrics}
      isLoading={false}
      columns={[
        { key: "provider", header: "Provider", cell: (row) => <span className="provider-pill">{row.name}</span> },
        { key: "requests", header: "Requests", align: "right", cell: (row) => formatInteger(row.requests), width: "110px" },
        { key: "tokens", header: "Tokens", align: "right", cell: (row) => formatInteger(row.total_tokens), width: "120px" },
        { key: "latency", header: "Avg latency", align: "right", cell: (row) => formatLatency(row.average_latency), width: "120px" },
        { key: "error", header: "Error rate", align: "right", cell: (row) => formatPercent(row.error_rate, 2), width: "120px" },
        { key: "cost", header: "Cost", align: "right", cell: (row) => formatCost(row.total_cost), width: "120px" },
      ]}
    />
  );
}
