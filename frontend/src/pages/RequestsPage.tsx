import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { TopBar } from "../layouts/TopBar";
import { Button } from "../components/Button";
import { DataTable, type Column } from "../components/DataTable";
import { Modal } from "../components/Modal";
import { EmptyState } from "../components/EmptyState";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import { useToast } from "../services/toast";
import {
  formatCost,
  formatInteger,
  formatLatency,
  formatTimestamp,
} from "../services/format";
import type { Period, RequestEvent, RequestStatus } from "../types/api";

const PAGE_SIZE = 25;

export function RequestsPage() {
  const [period, setPeriod] = useState<Period>("all");
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [status, setStatus] = useState<RequestStatus>("all");
  const [search, setSearch] = useState<string>("");
  const [appliedSearch, setAppliedSearch] = useState<string>("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<RequestEvent | null>(null);
  const toast = useToast();

  const filtersAsync = useAsync(() => api.filters(), []);

  const query = useMemo(
    () => ({
      period,
      provider: provider || null,
      model: model || null,
      status,
      search: appliedSearch || null,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [period, provider, model, status, appliedSearch, page],
  );

  const requestsAsync = useAsync(() => api.requests(query), [
    period,
    provider,
    model,
    status,
    appliedSearch,
    page,
  ]);

  // Reset paging when filters change.
  useEffect(() => {
    setPage(0);
  }, [period, provider, model, status, appliedSearch]);

  const total = requestsAsync.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const refresh = () => {
    requestsAsync.reload();
    filtersAsync.reload();
  };

  const handleError = (err: Error) => {
    if (err instanceof ApiError && err.isAuth) return;
    toast.show("error", "Could not load requests", err.message);
  };

  if (requestsAsync.error) handleError(requestsAsync.error);
  if (filtersAsync.error) handleError(filtersAsync.error);

  const providerOptions = filtersAsync.data?.providers ?? [];
  const modelOptions = filtersAsync.data?.models ?? [];

  const columns: Column<RequestEvent>[] = [
    {
      key: "time",
      header: "Time",
      cell: (row) => (
        <div>
          <div>{formatTimestamp(row.created_at)}</div>
        </div>
      ),
      width: "180px",
    },
    { key: "provider", header: "Provider", cell: (row) => row.provider ?? "—", width: "120px" },
    {
      key: "model",
      header: "Model",
      cell: (row) => <span className="mono">{row.model ?? "—"}</span>,
    },
    {
      key: "tokens",
      header: "Tokens",
      align: "right",
      cell: (row) => formatInteger(row.total_tokens),
      width: "100px",
    },
    {
      key: "latency",
      header: "Latency",
      align: "right",
      cell: (row) => formatLatency(row.latency_ms),
      width: "100px",
    },
    {
      key: "status",
      header: "Status",
      cell: (row) => (row.success ? <span className="pill pill--success">{row.cached ? "Cached" : "Success"}</span> : <span className="pill pill--danger">Failed</span>),
      width: "100px",
    },
    {
      key: "cost",
      header: "Cost",
      align: "right",
      cell: (row) => formatCost(row.cost),
      width: "100px",
    },
  ];

  return (
    <>
      <TopBar
        title="Requests"
        description="Inspect every request handled by the SmartLLM gateway."
        period={period}
        onPeriodChange={setPeriod}
        onRefresh={refresh}
        loading={requestsAsync.loading}
      />
      <div className="page">
        <section className="filter-bar">
          <div className="filter-bar__group filter-bar__group--grow">
            <label className="form-field form-field--inline">
              <span className="form-field__label">Search</span>
              <div className="form-field__input-wrapper">
                <Search size={14} className="form-field__icon" />
                <input
                  className="form-field__input form-field__input--with-icon"
                  type="search"
                  placeholder="Request ID, model, provider, key…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      setAppliedSearch(search.trim());
                    }
                  }}
                />
                {search && (
                  <button
                    type="button"
                    className="form-field__clear"
                    onClick={() => {
                      setSearch("");
                      setAppliedSearch("");
                    }}
                    aria-label="Clear search"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
            </label>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setAppliedSearch(search.trim())}
            >
              Apply
            </Button>
          </div>
          <div className="filter-bar__group">
            <label className="form-field form-field--inline">
              <span className="form-field__label">Provider</span>
              <select
                className="form-field__select"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="">All providers</option>
                {providerOptions.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-field form-field--inline">
              <span className="form-field__label">Model</span>
              <select
                className="form-field__select"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                <option value="">All models</option>
                {modelOptions
                  .filter((m) => !provider || m.provider === provider)
                  .map((m) => (
                    <option key={`${m.provider ?? "?"}-${m.model}`} value={m.model}>
                      {m.model}
                      {m.provider ? ` (${m.provider})` : ""}
                    </option>
                  ))}
              </select>
            </label>
            <label className="form-field form-field--inline">
              <span className="form-field__label">Status</span>
              <select
                className="form-field__select"
                value={status}
                onChange={(e) => setStatus(e.target.value as RequestStatus)}
              >
                <option value="all">All</option>
                <option value="success">Successful</option>
                <option value="failed">Failed</option>
                <option value="cached">Cached</option>
              </select>
            </label>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setProvider("");
                setModel("");
                setStatus("all");
                setSearch("");
                setAppliedSearch("");
              }}
            >
              Reset
            </Button>
          </div>
        </section>

        <section className="card card--padded">
          <DataTable
            columns={columns}
            data={requestsAsync.data?.data ?? []}
            rowKey={(row) => row.id}
            isLoading={requestsAsync.loading}
            onRowClick={(row) => setSelected(row)}
            emptyState={
              <EmptyState
                title="No requests match these filters"
                description="Try widening the time range or removing a filter."
              />
            }
          />
          <footer className="pagination">
            <div className="pagination__summary">
              {total === 0
                ? "0 results"
                : `Showing ${page * PAGE_SIZE + 1}–${Math.min(
                    (page + 1) * PAGE_SIZE,
                    total,
                  )} of ${total}`}
            </div>
            <div className="pagination__controls">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                Previous
              </Button>
              <span className="pagination__page">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
              >
                Next
              </Button>
            </div>
          </footer>
        </section>
      </div>
      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Request ${shortId(selected.id)}` : ""}
        size="md"
      >
        {selected && <RequestDetail request={selected} />}
      </Modal>
    </>
  );
}

function shortId(id: string): string {
  if (id.length <= 10) return id;
  return `${id.slice(0, 8)}…`;
}

function RequestDetail({ request }: { request: RequestEvent }) {
  return (
    <div className="detail">
      <dl className="detail__grid">
        <DetailRow label="Timestamp" value={formatTimestamp(request.created_at)} />
        <DetailRow label="Provider" value={request.provider ?? "—"} />
        <DetailRow label="Model" value={request.model ?? "—"} mono />
        <DetailRow label="API key" value={shortId(request.api_key_id)} mono />
        <DetailRow label="Status" value={
          request.success
            ? request.cached ? "Cached" : "Successful"
            : "Failed"
        } />
        <DetailRow label="Latency" value={formatLatency(request.latency_ms)} />
        <DetailRow label="Input tokens" value={formatInteger(request.input_tokens)} mono />
        <DetailRow label="Output tokens" value={formatInteger(request.output_tokens)} mono />
        <DetailRow label="Total tokens" value={formatInteger(request.total_tokens)} mono />
        <DetailRow label="Cost" value={formatCost(request.cost)} />
        <DetailRow label="Cache" value={request.cached ? "Hit" : "Miss"} />
        <DetailRow label="Request ID" value={request.id} mono />
      </dl>
    </div>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="detail__row">
      <dt className="detail__label">{label}</dt>
      <dd className={`detail__value${mono ? " mono" : ""}`}>{value}</dd>
    </div>
  );
}
