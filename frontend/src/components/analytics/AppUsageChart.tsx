interface AppUsage {
  app: string;
  minutes: number;
  percentage: number;
}

interface AppUsageChartProps {
  data: AppUsage[];
}

const APP_COLORS = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
];

export default function AppUsageChart({ data }: AppUsageChartProps) {
  if (data.length === 0) {
    return (
      <div className="app-usage-empty">
        <p>No app usage data yet. Start watching to track your workflow.</p>
      </div>
    );
  }

  const maxMinutes = Math.max(...data.map((d) => d.minutes));

  return (
    <div className="app-usage-chart">
      {data.slice(0, 8).map((item, i) => (
        <div key={item.app} className="app-usage-row">
          <div className="app-usage-label">
            <span
              className="app-usage-dot"
              style={{ background: APP_COLORS[i % APP_COLORS.length] }}
            />
            <span className="app-usage-name">{item.app}</span>
          </div>
          <div className="app-usage-bar-container">
            <div
              className="app-usage-bar"
              style={{
                width: `${(item.minutes / maxMinutes) * 100}%`,
                background: APP_COLORS[i % APP_COLORS.length],
              }}
            />
          </div>
          <div className="app-usage-stats">
            <span className="app-usage-time">{item.minutes}m</span>
            <span className="app-usage-pct">{item.percentage}%</span>
          </div>
        </div>
      ))}
    </div>
  );
}
