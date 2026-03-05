import { useEffect, useState } from "react";
import { getReport, getPatterns, Pattern } from "../services/api";

export default function Dashboard() {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);

  useEffect(() => {
    getReport().then(setReport).catch(() => {});
    getPatterns().then((res) => setPatterns(res.patterns)).catch(() => {});
  }, []);

  const potentialColors: Record<string, string> = {
    high: "#10b981",
    medium: "#f59e0b",
    low: "#6b7280",
    none: "#374151",
  };

  return (
    <div className="dashboard-page">
      <h2>Optimization Insights</h2>

      {report && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{String(report.total_observations ?? 0)}</div>
            <div className="stat-label">Total Observations</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{String(report.patterns_detected ?? 0)}</div>
            <div className="stat-label">Patterns Found</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{String(report.high_value_automations ?? 0)}</div>
            <div className="stat-label">Automation Opportunities</div>
          </div>
        </div>
      )}

      <h3>Detected Patterns</h3>
      {patterns.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-subtitle">
            No patterns detected yet. Keep working and the AI will identify
            optimization opportunities over time.
          </p>
        </div>
      ) : (
        <div className="pattern-list">
          {patterns.map((p, i) => (
            <div key={i} className="pattern-card">
              <div className="pattern-header">
                <span
                  className="pattern-potential"
                  style={{ color: potentialColors[p.automation_potential] }}
                >
                  {p.automation_potential} potential
                </span>
                <span className="pattern-count">{p.occurrence_count}x</span>
              </div>
              <p className="pattern-desc">{p.description}</p>
              <div className="pattern-apps">
                {p.apps_involved.map((app) => (
                  <span key={app} className="tag">{app}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {report?.top_recommendations &&
        (report.top_recommendations as Array<Record<string, unknown>>).length > 0 && (
          <>
            <h3>Top Recommendations</h3>
            <div className="recommendations">
              {(report.top_recommendations as Array<Record<string, string>>).map(
                (rec, i) => (
                  <div key={i} className="recommendation-card">
                    <p>{rec.suggestion}</p>
                    <span className="tag">{rec.potential} impact</span>
                  </div>
                )
              )}
            </div>
          </>
        )}
    </div>
  );
}
