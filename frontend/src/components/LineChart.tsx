import { useMemo } from "react";

interface LineChartProps {
  data: { label: string; value: number }[];
  height?: number;
  yFormat?: (value: number) => string;
}

// A small SVG line/area chart without external dependencies. Stays readable
// in a light theme, scales fluidly, and renders nothing when no data exists.
export function LineChart({ data, height = 180, yFormat }: LineChartProps) {
  const safeData = useMemo(() => data.filter((d) => Number.isFinite(d.value)), [data]);
  const { points, area, max, ticks, gridLines } = useMemo(() => {
    if (!safeData.length) {
      return { points: "", area: "", max: 0, ticks: [] as number[], gridLines: [] as { y: number; value: number }[] };
    }
    const width = 600;
    const innerHeight = height;
    const padding = { top: 12, right: 8, bottom: 22, left: 40 };
    const innerWidth = width - padding.left - padding.right;
    const maxValue = Math.max(...safeData.map((d) => d.value), 1);
    const niceMax = niceCeiling(maxValue);
    const stepX = safeData.length > 1 ? innerWidth / (safeData.length - 1) : 0;
    const scaleY = (value: number) =>
      padding.top + (innerHeight - padding.top - padding.bottom) *
      (1 - value / niceMax);
    const pointList = safeData.map((d, i) => {
      const x = padding.left + stepX * i;
      const y = scaleY(d.value);
      return { x, y };
    });
    const pointsStr = pointList
      .map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`)
      .join(" ");
    const areaStr =
      `${padding.left},${padding.top + (innerHeight - padding.top - padding.bottom)} ` +
      pointsStr +
      ` ${(padding.left + stepX * (pointList.length - 1)).toFixed(2)},${padding.top + (innerHeight - padding.top - padding.bottom)}`;
    const gridLineCount = 3;
    const grid = Array.from({ length: gridLineCount + 1 }, (_, i) => {
      const value = (niceMax / gridLineCount) * i;
      return { y: scaleY(value), value };
    });
    return { points: pointsStr, area: areaStr, max: niceMax, ticks: grid, gridLines: grid };
  }, [safeData, height]);

  if (!safeData.length) {
    return (
      <div className="chart-empty" style={{ height }}>
        No data points in this range.
      </div>
    );
  }

  const padding = { top: 12, right: 8, bottom: 22, left: 40 };
  const width = 600;
  const innerWidth = width - padding.left - padding.right;

  return (
    <svg
      className="line-chart"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Time series chart"
    >
      {gridLines.map((g) => (
        <g key={g.y}>
          <line
            x1={padding.left}
            x2={width - padding.right}
            y1={g.y}
            y2={g.y}
            stroke="var(--color-border)"
            strokeWidth={1}
          />
          <text
            x={padding.left - 6}
            y={g.y + 3}
            textAnchor="end"
            className="chart-axis-label"
          >
            {yFormat ? yFormat(g.value) : Math.round(g.value).toString()}
          </text>
        </g>
      ))}
      <polygon points={area} fill="var(--color-accent-soft)" />
      <polyline
        points={points}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {safeData.map((d, i) => {
        const stepX = safeData.length > 1 ? innerWidth / (safeData.length - 1) : 0;
        const x = padding.left + stepX * i;
        const value = d.value / max;
        const innerHeight = height - padding.top - padding.bottom;
        const y = padding.top + innerHeight * (1 - value);
        return (
          <circle
            key={`${d.label}-${i}`}
            cx={x}
            cy={y}
            r={2.5}
            fill="var(--color-accent)"
          />
        );
      })}
      <text
        x={padding.left}
        y={height - 6}
        className="chart-axis-label"
      >
        {safeData[0].label}
      </text>
      <text
        x={width - padding.right}
        y={height - 6}
        textAnchor="end"
        className="chart-axis-label"
      >
        {safeData[safeData.length - 1].label}
      </text>
    </svg>
  );
}

function niceCeiling(value: number): number {
  if (value <= 1) return 1;
  const exp = Math.floor(Math.log10(value));
  const fraction = value / Math.pow(10, exp);
  let nice: number;
  if (fraction <= 1) nice = 1;
  else if (fraction <= 2) nice = 2;
  else if (fraction <= 5) nice = 5;
  else nice = 10;
  return nice * Math.pow(10, exp);
}
