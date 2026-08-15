interface HorizontalBarsProps {
  data: { label: string; value: number; secondary?: string }[];
  valueFormat?: (value: number) => string;
}

export function HorizontalBars({ data, valueFormat }: HorizontalBarsProps) {
  if (!data.length) {
    return <div className="chart-empty">No data to display.</div>;
  }
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <ul className="bar-list">
      {data.map((item) => (
        <li key={item.label} className="bar-list__row">
          <div className="bar-list__label" title={item.label}>
            {item.label}
          </div>
          <div className="bar-list__bar">
            <div
              className="bar-list__bar-fill"
              style={{ width: `${(item.value / max) * 100}%` }}
            />
          </div>
          <div className="bar-list__value">
            {valueFormat ? valueFormat(item.value) : item.value}
          </div>
          {item.secondary && (
            <div className="bar-list__secondary">{item.secondary}</div>
          )}
        </li>
      ))}
    </ul>
  );
}
