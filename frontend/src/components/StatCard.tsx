import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  emphasis?: "default" | "muted";
}

export function StatCard({ label, value, detail, emphasis = "default" }: StatCardProps) {
  return (
    <article className={`stat-card stat-card--${emphasis}`}>
      <header className="stat-card__label">{label}</header>
      <div className="stat-card__value">{value}</div>
      {detail && <div className="stat-card__detail">{detail}</div>}
    </article>
  );
}
