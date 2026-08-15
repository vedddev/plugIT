import { useEffect, useState } from "react";
import { RefreshCcw, LogOut, Cpu } from "lucide-react";
import { Button } from "../components/Button";
import { api, ApiError } from "../services/api";
import { useAdminKey } from "../services/adminKey";
import { useToast } from "../services/toast";
import type { Period } from "../types/api";
import { formatRelative } from "../services/format";

interface TopBarProps {
  title: string;
  description?: string;
  period?: Period;
  onPeriodChange?: (period: Period) => void;
  onRefresh?: () => void;
  loading?: boolean;
}

const periodOptions: { value: Period; label: string }[] = [
  { value: "today", label: "Today" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "all", label: "All time" },
];

export function TopBar({
  title,
  description,
  period,
  onPeriodChange,
  onRefresh,
  loading,
}: TopBarProps) {
  const { adminKey, clearAdminKey } = useAdminKey();
  const toast = useToast();
  const [health, setHealth] = useState<"ok" | "down" | "unknown">("unknown");
  const [lastSync, setLastSync] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      api
        .health()
        .then((res) => {
          if (cancelled) return;
          setHealth(res.status === "ok" ? "ok" : "down");
          setLastSync(new Date());
        })
        .catch(() => {
          if (cancelled) return;
          setHealth("down");
        });
    void check();
    const timer = window.setInterval(check, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <header className="topbar">
      <div className="topbar__title">
        <h1>{title}</h1>
        {description && <p className="topbar__description">{description}</p>}
      </div>
      <div className="topbar__controls">
        {onPeriodChange && period && (
          <div className="topbar__period" role="tablist" aria-label="Time range">
            {periodOptions.map((opt) => (
              <button
                key={opt.value}
                role="tab"
                aria-selected={period === opt.value}
                className={`topbar__period-btn${
                  period === opt.value ? " topbar__period-btn--active" : ""
                }`}
                onClick={() => onPeriodChange(opt.value)}
                type="button"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
        <div className="topbar__meta">
          <span
            className={`topbar__health topbar__health--${health}`}
            title={
              lastSync
                ? `Last check: ${formatRelative(lastSync.toISOString())}`
                : "Checking…"
            }
          >
            <Cpu size={14} />
            {health === "ok"
              ? "API online"
              : health === "down"
                ? "API unreachable"
                : "Checking…"}
          </span>
          {onRefresh && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                try {
                  onRefresh();
                } catch (error) {
                  if (error instanceof ApiError) {
                    toast.show("error", "Refresh failed", error.message);
                  } else {
                    throw error;
                  }
                }
              }}
              disabled={loading}
            >
              <RefreshCcw size={14} className={loading ? "icon-spin" : undefined} />
              Refresh
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              clearAdminKey();
              toast.show("info", "Signed out", "Admin key cleared from this browser session.");
            }}
            title="Clear stored admin key"
          >
            <LogOut size={14} />
            Sign out
          </Button>
        </div>
        {adminKey && (
          <div className="topbar__key" title="Active admin key prefix">
            <span className="topbar__key-dot" />
            <span className="topbar__key-text">
              {adminKey.slice(0, 4)}…{adminKey.slice(-2)}
            </span>
          </div>
        )}
      </div>
    </header>
  );
}
