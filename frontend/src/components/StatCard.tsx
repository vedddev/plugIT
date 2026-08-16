import type { ReactNode } from "react";
import { Activity, BarChart3, Coins, Gauge, Percent, Zap } from "lucide-react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  emphasis?: "default" | "muted";
}

export function StatCard({ label, value, detail, emphasis = "default" }: StatCardProps) {
  const Icon = label === "Requests" ? Activity : label === "Tokens" || label.includes("tokens") ? Zap : label.includes("cost") ? Coins : label.includes("latency") ? Gauge : label.includes("rate") ? Percent : BarChart3;
  return (
    <article className={`stat-card stat-card--${emphasis}`}>
      <header className="stat-card__label"><span className="stat-card__icon"><Icon size={14} /></span>{label}</header>
      <div className="stat-card__value">{value}</div>
      {detail && <div className="stat-card__detail">{detail}</div>}
    </article>
  );
}
