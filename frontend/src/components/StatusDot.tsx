interface StatusDotProps {
  status: "ok" | "degraded" | "down" | "neutral";
  label?: string;
}

const COLOR: Record<StatusDotProps["status"], string> = {
  ok: "var(--color-success)",
  degraded: "var(--color-warning)",
  down: "var(--color-danger)",
  neutral: "var(--color-text-muted)",
};

export function StatusDot({ status, label }: StatusDotProps) {
  return (
    <span className="status-dot" aria-label={label ?? status}>
      <span
        className="status-dot__dot"
        style={{ background: COLOR[status] }}
      />
      {label && <span className="status-dot__label">{label}</span>}
    </span>
  );
}
