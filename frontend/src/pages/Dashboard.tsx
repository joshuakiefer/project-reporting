import { useEffect, useState } from "react";
import { getReport, getPatterns, Pattern } from "../services/api";
import FocusScoreCard from "../components/analytics/FocusScore";
import AppUsageChart from "../components/analytics/AppUsageChart";
import TrendChart from "../components/analytics/TrendChart";

export default function Dashboard() {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [focusScore, setFocusScore] = useState<Record<string, unknown> | null>(null);
  const [appUsage, setAppUsage] = useState<Array<{ app: string; minutes: number; percentage: number }>>([]);
  const [trends, setTrends] = useState<Array<{ date: string; score: number; deep_work_minutes: number; context_switches: number }>>([]);
  const [activeTab, setActiveTab] = useState<"overview" | "patterns" | "analytics">("overview");

  useEffect(() => {
    getReport().then(setReport).catch(() => {});
    getPatterns().then((res) => setPatterns(res.patterns)).catch(() => {});

    // Analytics data
    fetch("http://127.0.0.1:8321/api/analytics/focus?period=today")
      .then((r) => r.json()).then(setFocusScore).catch(() => {});
    fetch("http://127.0.0.1:8321/api/analytics/apps?period=today")
      .then((r) => r.json()).then((d) => setAppUsage(d.apps || [])).catch(() => {});
    fetch("http://127.0.0.1:8321/api/analytics/trends?days=7")
      .then((r) => r.json()).then((d) => setTrends(d.trends || [])).catch(() => {});
  }, []);

  const potentialColors: Record<string, string> = {
    high: "var(--success)",
    medium: "var(--warning)",
    low: "var(--text-muted)",
  };

  return (
    <div className="dashboard-page">
      {/* Tab bar */}
      <div className="dashboard-tabs">
        {(["overview", "patterns", "analytics"] as const).map((tab) => (
          <button
            key={tab}
            className={`dashboard-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview tab */}
      {activeTab === "overview" && (
        <div className="dashboard-overview fade-in">
          {report && (
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-value">{String(report.total_observations ?? 0)}</div>
                <div className="stat-label">Observations</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{String(report.patterns_detected ?? 0)}</div>
                <div className="stat-label">Patterns</div>
              </div>
              <div className="stat-card accent">
                <div className="stat-value">{String(report.high_value_automations ?? 0)}</div>
                <div className="stat-label">Automations</div>
              </div>
            </div>
          )}

          {focusScore && (
            <div className="section">
              <h3 className="section-title">Focus Score</h3>
              <FocusScoreCard
                score={(focusScore.score as number) ?? 0}
                label={(focusScore.period_label as string) ?? "Today"}
                deepWorkMinutes={(focusScore.deep_work_minutes as number) ?? 0}
                contextSwitches={(focusScore.context_switches as number) ?? 0}
                longestStreak={(focusScore.longest_focus_streak_minutes as number) ?? 0}
              />
            </div>
          )}

          {report?.top_recommendations &&
            (report.top_recommendations as Array<Record<string, string>>).length > 0 && (
              <div className="section">
                <h3 className="section-title">Top Recommendations</h3>
                {(report.top_recommendations as Array<Record<string, string>>).map((rec, i) => (
                  <div key={i} className="recommendation-card">
                    <p>{rec.suggestion}</p>
                    <span className="tag">{rec.potential} impact</span>
                  </div>
                ))}
              </div>
            )}
        </div>
      )}

      {/* Patterns tab */}
      {activeTab === "patterns" && (
        <div className="dashboard-patterns fade-in">
          {patterns.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">{"\u{1F50D}"}</div>
              <p className="empty-state-title">No patterns yet</p>
              <p className="empty-state-subtitle">
                Keep working and the AI will identify repetitive workflows
                and automation opportunities over time.
              </p>
            </div>
          ) : (
            <div className="pattern-list">
              {patterns.map((p, i) => (
                <div key={i} className="pattern-card">
                  <div className="pattern-header">
                    <span
                      className="pattern-potential"
                      style={{ color: potentialColors[p.automation_potential] || "var(--text-muted)" }}
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
                  {p.automation_potential !== "none" && (
                    <button className="btn btn-sm btn-ghost pattern-automate-btn">
                      Generate Automation
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Analytics tab */}
      {activeTab === "analytics" && (
        <div className="dashboard-analytics fade-in">
          <div className="section">
            <h3 className="section-title">7-Day Focus Trend</h3>
            <TrendChart data={trends} />
          </div>

          <div className="section">
            <h3 className="section-title">App Usage Today</h3>
            <AppUsageChart data={appUsage} />
          </div>
        </div>
      )}
    </div>
  );
}
