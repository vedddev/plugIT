import { useEffect, useState } from "react";
import { TopBar } from "../layouts/TopBar";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import { useToast } from "../services/toast";
import { formatRelative, formatTimestamp } from "../services/format";
import type { FiltersResponse, ProvidersResponse } from "../types/api";

interface SettingsGroup {
  title: string;
  description: string;
  rows: { label: string; value: string }[];
}

export function SettingsPage() {
  const toast = useToast();
  const [adminKey, setAdminKey] = useState<string>("");

  useEffect(() => {
    setAdminKey(sessionStorage.getItem("smartllm.adminKey") ?? "");
  }, []);

  const providersAsync = useAsync(() => api.providers("all"), []);
  const filtersAsync = useAsync(() => api.filters(), []);

  const handleError = (err: Error) => {
    if (err instanceof ApiError && err.isAuth) return;
    toast.show("error", "Could not load settings", err.message);
  };
  if (providersAsync.error) handleError(providersAsync.error);
  if (filtersAsync.error) handleError(filtersAsync.error);

  const providers: ProvidersResponse | null = providersAsync.data;
  const filters: FiltersResponse | null = filtersAsync.data;

  const groups: SettingsGroup[] = [
    {
      title: "Gateway",
      description: "General settings and current deployment of the SmartLLM gateway.",
      rows: [
        { label: "Admin API", value: window.location.origin },
        { label: "Dashboard", value: `${window.location.origin}/dashboard/` },
        { label: "Auth header", value: "X-Admin-Key" },
        { label: "Configured providers", value: providers?.registered?.join(", ") || "—" },
      ],
    },
    {
      title: "Provider catalog",
      description: "Models that are registered with the gateway, by provider.",
      rows:
        providers && Object.keys(providers.catalog).length > 0
          ? Object.entries(providers.catalog).map(([name, models]) => ({
              label: name,
              value: models.length > 0 ? models.join(", ") : "—",
            }))
          : [{ label: "Providers", value: "No providers registered." }],
    },
    {
      title: "Observed traffic",
      description: "Distinct provider and model names that have served requests.",
      rows: [
        {
          label: "Providers seen",
          value: filters?.providers?.length ? filters.providers.join(", ") : "No traffic yet.",
        },
        {
          label: "Models seen",
          value:
            filters?.models && filters.models.length > 0
              ? filters.models
                  .map((m) => `${m.model}${m.provider ? ` (${m.provider})` : ""}`)
                  .join(", ")
              : "No traffic yet.",
        },
      ],
    },
  ];

  return (
    <>
      <TopBar
        title="Settings"
        description="Configuration currently exposed by the SmartLLM backend."
      />
      <div className="page">
        <section className="card card--padded">
          <header className="card__header">
            <h2>Active session</h2>
            <span className="card__subtitle">Browser-stored admin key</span>
          </header>
          <dl className="detail__grid">
            <div className="detail__row">
              <dt className="detail__label">Status</dt>
              <dd className="detail__value">
                {adminKey ? (
                  <span className="pill pill--success">Signed in</span>
                ) : (
                  <span className="pill pill--muted">Not signed in</span>
                )}
              </dd>
            </div>
            <div className="detail__row">
              <dt className="detail__label">Key prefix</dt>
              <dd className="detail__value mono">
                {adminKey ? `${adminKey.slice(0, 4)}…${adminKey.slice(-2)}` : "—"}
              </dd>
            </div>
            <div className="detail__row">
              <dt className="detail__label">Last loaded</dt>
              <dd className="detail__value">
                {providersAsync.loading ? (
                  <span className="inline-flex">
                    <Spinner size={12} /> Loading…
                  </span>
                ) : (
                  formatRelative(new Date().toISOString())
                )}
              </dd>
            </div>
            <div className="detail__row">
              <dt className="detail__label">Timestamp</dt>
              <dd className="detail__value mono">{formatTimestamp(new Date().toISOString())}</dd>
            </div>
          </dl>
          <p className="muted small">
            The admin key is held in <code>sessionStorage</code> only. Closing
            the tab clears it.
          </p>
        </section>

        {groups.map((group) => (
          <section className="card card--padded" key={group.title}>
            <header className="card__header">
              <div>
                <h2>{group.title}</h2>
                <p className="muted small">{group.description}</p>
              </div>
            </header>
            <dl className="detail__grid">
              {group.rows.map((row) => (
                <div className="detail__row" key={row.label}>
                  <dt className="detail__label">{row.label}</dt>
                  <dd className="detail__value mono">{row.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
    </>
  );
}
