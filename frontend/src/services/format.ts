// Formatting helpers used across the dashboard. Locale-independent
// defaults are deliberate to keep numbers readable in English.

export function formatNumber(value: number | null | undefined): string {
  const safe = Number(value) || 0;
  if (Math.abs(safe) >= 1_000_000) {
    return `${(safe / 1_000_000).toFixed(safe >= 10_000_000 ? 1 : 2)}M`;
  }
  if (Math.abs(safe) >= 1_000) {
    return `${(safe / 1_000).toFixed(safe >= 10_000 ? 1 : 2)}K`;
  }
  return new Intl.NumberFormat().format(Math.round(safe));
}

export function formatInteger(value: number | null | undefined): string {
  return new Intl.NumberFormat().format(Math.round(Number(value) || 0));
}

export function formatCost(value: number | null | undefined): string {
  const safe = Number(value) || 0;
  if (safe === 0) return "$0.00";
  if (safe < 0.0001) return "<$0.0001";
  if (safe < 1) {
    return `$${safe.toFixed(4)}`;
  }
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(safe);
}

export function formatLatency(value: number | null | undefined): string {
  const safe = Number(value) || 0;
  if (safe < 1) return "<1 ms";
  if (safe < 1000) return `${Math.round(safe)} ms`;
  return `${(safe / 1000).toFixed(2)} s`;
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  const safe = Number(value) || 0;
  return `${(safe * 100).toFixed(digits)}%`;
}

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "never";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const diffMs = Date.now() - date.getTime();
  const sec = Math.round(diffMs / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 30) return `${day}d ago`;
  return date.toLocaleDateString();
}
