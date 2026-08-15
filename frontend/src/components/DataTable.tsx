import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  width?: string;
  align?: "left" | "right";
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyState?: ReactNode;
  isLoading?: boolean;
}

export function DataTable<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  emptyState,
  isLoading,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="data-table__loading" role="status">
        Loading…
      </div>
    );
  }
  if (!data.length) {
    return <div className="data-table__empty">{emptyState ?? "No records."}</div>;
  }
  return (
    <div className="data-table__scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  width: col.width,
                  textAlign: col.align ?? "left",
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => {
            const interactive = Boolean(onRowClick);
            return (
              <tr
                key={rowKey(row)}
                className={interactive ? "data-table__row--clickable" : undefined}
                onClick={interactive ? () => onRowClick?.(row) : undefined}
                tabIndex={interactive ? 0 : undefined}
                onKeyDown={
                  interactive
                    ? (e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onRowClick?.(row);
                        }
                      }
                    : undefined
                }
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    style={{ textAlign: col.align ?? "left" }}
                  >
                    {col.cell(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
