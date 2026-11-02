import { barGeometry } from "../stats";

export interface BarDatum {
  label: string;
  value: number;
}

export interface BarChartProps {
  data: BarDatum[];
  format: (value: number) => string;
  title: string;
  width?: number;
  height?: number;
  color?: string;
}

const PAD = { top: 22, right: 12, bottom: 34, left: 64 };

/** A vertical bar chart drawn directly as SVG. */
export function BarChart({
  data,
  format,
  title,
  width = 560,
  height = 220,
  color = "#6366f1",
}: BarChartProps) {
  const innerWidth = width - PAD.left - PAD.right;
  const innerHeight = height - PAD.top - PAD.bottom;
  const { bars, max } = barGeometry(data, innerWidth, innerHeight);
  const gridLines = [0, 0.25, 0.5, 0.75, 1];
  return (
    <svg
      class="chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={title}
      preserveAspectRatio="xMidYMid meet"
    >
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {gridLines.map((fraction) => {
          const y = innerHeight - fraction * innerHeight;
          return (
            <g key={fraction}>
              <line x1={0} x2={innerWidth} y1={y} y2={y} class="grid" />
              <text x={-8} y={y + 4} text-anchor="end" class="axis">
                {format(max * fraction)}
              </text>
            </g>
          );
        })}
        {bars.map((bar) => (
          <g key={bar.label}>
            <rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx={3} fill={color}>
              <title>{`${bar.label}: ${format(bar.value)}`}</title>
            </rect>
            <text x={bar.x + bar.width / 2} y={bar.y - 6} text-anchor="middle" class="value">
              {format(bar.value)}
            </text>
            <text
              x={bar.x + bar.width / 2}
              y={innerHeight + 18}
              text-anchor="middle"
              class="axis"
            >
              {bar.label}
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}
