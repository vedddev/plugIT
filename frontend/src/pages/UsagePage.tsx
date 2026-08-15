import { useState } from "react";
import { TopBar } from "../layouts/TopBar";
import { StatCard } from "../components/StatCard";
import { DataTable, type Column } from "../components/DataTable";
import { HorizontalBars } from "../components/HorizontalBars";
import { EmptyState } from "../components/EmptyState";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import { useToast } from "../services/toast";
import {
  formatCost,
  formatInteger,
  formatNumber,
} from "../services/format";
import type { Period, UsageBucket } from "../types/api";

export function UsagePage() {
  const [period, setPeriod] = useState<Period>("7d");
  const toast = useToast();

  const statsAsync = useAsync(() => api.stats(period), [period]);
  const usageAsync = useAsync(() => api.usage(period), [period]);

  const refresh = () => {
    statsAsync.reload();
    usageAsync.reload();
  };

  const handleError = (err: Error) => {
    if (err instanceof ApiError && err.isAuth) return;
    toast.show("error", "Could not load usage", err.message);
  };
  if (statsAsync.error) handleError(statsAsync.error);
  if (usageAsync.error) handleError(usageAsync.error);

  const stats = statsAsync.data;
  const usage = usageAsync.data;

  const providerColumns: Column<UsageBucket>[] = [
    { key: "name", header: "Provider", cell: (row) => <span className="provider-pill">{row.name}</span> },
    { key: "requests", header: "Requests", align: "right", cell: (row) => formatInteger(row.requests), width: "120px" },
    { key: "tokens", header: "Tokens", align: "right", cell: (row) => formatInteger(row.total_tokens), width: "120px" },
    { key: "cost", header: "Cost", align: "right", cell: (row) => formatCost(row.total_cost), width: "120px" },
  ];

  const modelColumns: Column<UsageBucket>[] = [
    { key: "name", header: "Model", cell: (row) => <span className="mono">{row.name}</span> },
    { key: "requests", header: "Requests", align: "right", cell: (row) => formatInteger(row.requests), width: "120px" },
    { key: "tokens", header: "Tokens", align: "right", cell: (row) => formatInteger(row.total_tokens), width: "120px" },
    { key: "cost", header: "Cost", align: "right", cell: (row) => formatCost(row.total_cost), width: "120px" },
  ];

  const providerBars = (usage?.provider_usage ?? []).map((p) => ({
    label: p.name,
    value: p.requests,
    secondary: formatInteger(p.total_tokens) + " tokens · " + formatCost(p.total_cost),
  }));
  const modelBars = (usage?.model_usage ?? []).map((m) => ({
    label: m.name,
    value: m.requests,
    secondary: formatInteger(m.total_tokens) + " tokens · " + formatCost(m.total_cost),
  }));

  return (
    <>
      <TopBar
        title="Usage"
        description="Aggregate cost and token consumption by provider and model."
        period={period}
        onPeriodChange={setPeriod}
        onRefresh={refresh}
        loading={statsAsync.loading || usageAsync.loading}
      />
      <div className="page">
        <section className="stat-grid">
          <StatCard label="Requests" value={formatNumber(stats?.total_requests)} detail={`${formatInteger(stats?.requests_today)} today`} />
          <StatCard label="Input tokens" value={formatNumber(stats?.total_input_tokens)} />
          <StatCard label="Output tokens" value={formatNumber(stats?.total_output_tokens)} />
          <StatCard label="Total tokens" value={formatNumber(stats?.total_tokens)} />
          <StatCard label="Estimated cost" value={formatCost(stats?.total_cost)} />
          <StatCard label="Cache hit rate" value={formatNumber((stats?.cache_hit_rate ?? 0) * 100) + "%"} />
        </section>

        <section className="grid-2">
          <article className="card">
            <header className="card__header">
              <h2>Provider breakdown</h2>
              <span className="card__subtitle">By request count</span>
            </header>
            {providerBars.length === 0 ? (
              <EmptyState title="No provider activity" description="No usage recorded for this period." />
            ) : (
              <HorizontalBars data={providerBars} valueFormat={(v) => formatInteger(v)} />
            )}
          </article>
          <article className="card">
            <header className="card__header">
              <h2>Model breakdown</h2>
              <span className="card__subtitle">By request count</span>
            </header>
            {modelBars.length === 0 ? (
              <EmptyState title="No model activity" description="No usage recorded for this period." />
            ) : (
              <HorizontalBars data={modelBars} valueFormat={(v) => formatInteger(v)} />
            )}
          </article>
        </section>

        <section className="grid-2">
          <article className="card">
            <header className="card__header">
              <h2>By provider</h2>
            </header>
            <DataTable
              columns={providerColumns}
              data={usage?.provider_usage ?? []}
              rowKey={(row) => row.name}
              isLoading={usageAsync.loading}
              emptyState="No provider activity."
            />
          </article>
          <article className="card">
            <header className="card__header">
              <h2>By model</h2>
            </header>
            <DataTable
              columns={modelColumns}
              data={usage?.model_usage ?? []}
              rowKey={(row) => row.name}
              isLoading={usageAsync.loading}
              emptyState="No model activity."
            />
          </article>
        </section>
      </div>
    </>
  );
}
