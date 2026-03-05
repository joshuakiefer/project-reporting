interface TrendPoint {
  date: string;
  score: number;
  deep_work_minutes: number;
  context_switches: number;
}

interface TrendChartProps {
  data: TrendPoint[];
}

export default function TrendChart({ data }: TrendChartProps) {
  if (data.length < 2) {
    return (
      <div className="trend-empty">
        <p>Need at least 2 days of data to show trends.</p>
      </div>
    );
  }

  const maxScore = 100;
  const width = 320;
  const height = 120;
  const padding = { top: 10, right: 10, bottom: 24, left: 10 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const points = data.map((d, i) => ({
    x: padding.left + (i / (data.length - 1)) * chartW,
    y: padding.top + chartH - (d.score / maxScore) * chartH,
    ...d,
  }));

  // Build SVG path
  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  // Area fill path
  const areaD =
    pathD +
    ` L ${points[points.length - 1].x} ${padding.top + chartH}` +
    ` L ${points[0].x} ${padding.top + chartH} Z`;

  const avg = Math.round(data.reduce((s, d) => s + d.score, 0) / data.length);
  const trend = data[data.length - 1].score - data[0].score;

  return (
    <div className="trend-chart">
      <div className="trend-header">
        <span className="trend-avg">Avg: {avg}</span>
        <span className={`trend-direction ${trend >= 0 ? "up" : "down"}`}>
          {trend >= 0 ? "\u2191" : "\u2193"} {Math.abs(trend)} pts
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="trend-svg">
        {/* Grid lines */}
        {[25, 50, 75].map((v) => (
          <line
            key={v}
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + chartH - (v / maxScore) * chartH}
            y2={padding.top + chartH - (v / maxScore) * chartH}
            stroke="var(--border)"
            strokeWidth="0.5"
            strokeDasharray="4 4"
          />
        ))}

        {/* Area fill */}
        <path d={areaD} fill="url(#trendGradient)" opacity="0.3" />

        {/* Line */}
        <path d={pathD} fill="none" stroke="var(--primary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Dots */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="4"
            fill="var(--bg)"
            stroke="var(--primary)"
            strokeWidth="2"
          />
        ))}

        {/* Date labels */}
        {points.map((p, i) => (
          <text
            key={i}
            x={p.x}
            y={height - 4}
            textAnchor="middle"
            fill="var(--text-muted)"
            fontSize="9"
          >
            {p.date.slice(5)}
          </text>
        ))}

        <defs>
          <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}
