import { useState } from "react";
import { TopBar } from "../layouts/TopBar";
import { DataTable, type Column } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { StatusDot } from "../components/StatusDot";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import { useToast } from "../services/toast";
import {
  formatCost,
  formatInteger,
  formatLatency,
  formatPercent,
} from "../services/format";
import type { Period, ProvidersResponse } from "../types/api";

interface ProviderRow {
  name: string;
  status: "ok" | "degraded" | "down" | "neutral";
  models: string;
  requests: number;
  avgLatency: number;
  errorRate: number;
  cost: number;
  registered: boolean;
}

export function ProvidersPage() {
  const [period, setPeriod] = useState<Period>("all");
  const toast = useToast();
  const asyncState = useAsync(() => api.providers(period), [period]);

  const refresh = () => asyncState.reload();
  if (asyncState.error && !(asyncState.error instanceof ApiError && asyncState.error.isAuth)) {
    toast.show("error", "Could not load providers", asyncState.error.message);
  }

  const data = asyncState.data;
  const rows = buildRows(data);

  const columns: Column<ProviderRow>[] = [
    {
      key: "provider",
      header: "Provider",
      cell: (row) => (
        <div className="provider-cell">
          <StatusDot status={row.status} />
          <div>
            <div className="provider-cell__name">{row.name}</div>
            <div className="provider-cell__sub">
              {row.registered ? "Registered" : "Observed in traffic"}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: "models",
      header: "Models",
      cell: (row) => <span className="mono">{row.models}</span>,
    },
    {
      key: "status",
      header: "Status",
      cell: (row) => <StatusDot status={row.status} label={statusLabel(row.status)} />,
      width: "140px",
    },
    {
      key: "requests",
      header: "Requests",
      align: "right",
      cell: (row) => formatInteger(row.requests),
      width: "110px",
    },
    {
      key: "latency",
      header: "Avg latency",
      align: "right",
      cell: (row) => formatLatency(row.avgLatency),
      width: "120px",
    },
    {
      key: "errors",
      header: "Error rate",
      align: "right",
      cell: (row) => formatPercent(row.errorRate, 2),
      width: "120px",
    },
    {
      key: "cost",
      header: "Cost",
      align: "right",
      cell: (row) => formatCost(row.cost),
      width: "120px",
    },
  ];

  return (
    <>
      <TopBar
        title="Providers"
        description="Registered providers, configured models, and traffic health."
        period={period}
        onPeriodChange={setPeriod}
        onRefresh={refresh}
        loading={asyncState.loading}
      />
      <div className="page">
        <section className="card card--padded">
          <DataTable
            columns={columns}
            data={rows}
            rowKey={(row) => row.name}
            isLoading={asyncState.loading}
            emptyState={
              <EmptyState
                title="No provider activity"
                description="Once requests flow through the gateway, providers will appear here."
              />
            }
          />
        </section>
      </div>
    </>
  );
}

function buildRows(data: ProvidersResponse | null | undefined): ProviderRow[] {
  if (!data) return [];
  const byName = new Map<string, ProviderRow>();
  const registered = new Set(data.registered);
  for (const name of data.known_providers) {
    const live = data.health?.[name];
    const status: ProviderRow["status"] = name in (data.health ?? {})
      ? live
        ? "ok"
        : "down"
      : "neutral";
    const modelList = (data.models[name] ?? data.catalog[name] ?? []).join(", ");
    byName.set(name, {
      name,
      status,
      models: modelList || "—",
      requests: 0,
      avgLatency: 0,
      errorRate: 0,
      cost: 0,
      registered: registered.has(name),
    });
  }
  for (const metric of data.metrics) {
    const row =
      byName.get(metric.name) ??
      ({
        name: metric.name,
        status: "neutral",
        models: "—",
        requests: 0,
        avgLatency: 0,
        errorRate: 0,
        cost: 0,
        registered: false,
      } as ProviderRow);
    row.requests = metric.requests;
    row.avgLatency = metric.average_latency;
    row.errorRate = metric.error_rate;
    row.cost = metric.total_cost;
    if (row.status === "neutral" && metric.requests > 0) {
      row.status = metric.error_rate > 0.05 ? "degraded" : "ok";
    }
    byName.set(metric.name, row);
  }
  return Array.from(byName.values()).sort((a, b) => {
    if (a.registered !== b.registered) return a.registered ? -1 : 1;
    return b.requests - a.requests;
  });
}

function statusLabel(status: ProviderRow["status"]): string {
  switch (status) {
    case "ok":
      return "Healthy";
    case "degraded":
      return "Degraded";
    case "down":
      return "Unreachable";
    default:
      return "Inactive";
  }
}
