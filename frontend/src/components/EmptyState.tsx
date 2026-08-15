import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state" role="status">
      <div className="empty-state__title">{title}</div>
      {description && (
        <div className="empty-state__description">{description}</div>
      )}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
