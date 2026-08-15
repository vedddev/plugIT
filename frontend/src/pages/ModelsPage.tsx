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
import type { ModelMetric, Period } from "../types/api";

interface ModelRow extends ModelMetric {
  status: "active" | "configured" | "inactive";
}

export function ModelsPage() {
  const [period, setPeriod] = useState<Period>("all");
  const toast = useToast();
  const asyncState = useAsync(() => api.models(period), [period]);

  const refresh = () => asyncState.reload();
  if (asyncState.error && !(asyncState.error instanceof ApiError && asyncState.error.isAuth)) {
    toast.show("error", "Could not load models", asyncState.error.message);
  }

  const rows: ModelRow[] = (asyncState.data?.data ?? []).map((row) => ({
    ...row,
    status: row.requests > 0 ? "active" : row.in_catalog ? "configured" : "inactive",
  }));

  const columns: Column<ModelRow>[] = [
    {
      key: "model",
      header: "Model",
      cell: (row) => <span className="mono">{row.model}</span>,
    },
    {
      key: "provider",
      header: "Provider",
      cell: (row) => row.provider ?? "—",
      width: "140px",
    },
    {
      key: "capability",
      header: "Task capability",
      cell: (row) => (
        <span className="muted">
          {row.in_catalog ? "Routing / direct" : "Direct only"}
        </span>
      ),
      width: "160px",
    },
    {
      key: "requests",
      header: "Requests",
      align: "right",
      cell: (row) => formatInteger(row.requests),
      width: "110px",
    },
    {
      key: "tokens",
      header: "Tokens",
      align: "right",
      cell: (row) => formatInteger(row.total_tokens),
      width: "120px",
    },
    {
      key: "latency",
      header: "Avg latency",
      align: "right",
      cell: (row) => formatLatency(row.average_latency),
      width: "120px",
    },
    {
      key: "status",
      header: "Status",
      cell: (row) => <StatusDot status={statusFor(row.status)} label={labelFor(row.status)} />,
      width: "140px",
    },
  ];

  return (
    <>
      <TopBar
        title="Models"
        description="Configured model catalog and observed traffic by model."
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
            rowKey={(row) => `${row.provider ?? "?"}-${row.model}`}
            isLoading={asyncState.loading}
            emptyState={
              <EmptyState
                title="No models known"
                description="Once a provider is registered and traffic flows, models will appear here."
              />
            }
          />
        </section>
      </div>
    </>
  );
}

function statusFor(status: ModelRow["status"]): "ok" | "neutral" {
  return status === "active" ? "ok" : "neutral";
}

function labelFor(status: ModelRow["status"]): string {
  switch (status) {
    case "active":
      return "Active";
    case "configured":
      return "Configured";
    default:
      return "Observed";
  }
}
