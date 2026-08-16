// Shared formatting helpers. Timestamp values from the backend are UTC and
// are intentionally rendered in the browser's local timezone.

export function formatNumber(value: number | null | undefined): string {
  const safe = Number(value) || 0;
  if (Math.abs(safe) >= 1_000_000) return `${(safe / 1_000_000).toFixed(safe >= 10_000_000 ? 1 : 2)}M`;
  if (Math.abs(safe) >= 1_000) return `${(safe / 1_000).toFixed(safe >= 10_000 ? 1 : 2)}K`;
  return new Intl.NumberFormat().format(Math.round(safe));
}

export function formatInteger(value: number | null | undefined): string { return new Intl.NumberFormat().format(Math.round(Number(value) || 0)); }
export function formatCost(value: number | null | undefined): string { const safe = Number(value) || 0; if (safe === 0) return "$0.00"; if (safe < 0.0001) return "<$0.0001"; if (safe < 1) return `$${safe.toFixed(4)}`; return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(safe); }
export function formatLatency(value: number | null | undefined): string { const safe = Number(value) || 0; if (safe < 1) return "<1 ms"; if (safe < 1000) return `${Math.round(safe)} ms`; return `${(safe / 1000).toFixed(2)} s`; }
export function formatPercent(value: number | null | undefined, digits = 1): string { return `${((Number(value) || 0) * 100).toFixed(digits)}%`; }

function parseTimestamp(value: string | Date | null | undefined): Date | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const text = String(value).trim();
  if (!text) return null;
  // Explicit offsets and Z are preserved. Legacy timezone-less values are
  // known UTC database values, so append Z before constructing the Date.
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text);
  const date = new Date(hasTimezone ? text : `${text}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const date = parseTimestamp(value);
  if (!date) return value ? String(value) : "—";
  return date.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function formatTimestamp(value: string | Date | null | undefined): string { return formatDateTime(value); }

export function formatTime(value: string | Date | null | undefined): string {
  const date = parseTimestamp(value);
  if (!date) return value ? String(value) : "—";
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = parseTimestamp(value);
  if (!date) return value ? String(value) : "—";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

export function formatRelative(value: string | Date | null | undefined): string {
  const date = parseTimestamp(value);
  if (!date) return "never";
  const sec = Math.round((Date.now() - date.getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60); if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60); if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24); if (day < 30) return `${day}d ago`;
  return formatDate(date);
}
