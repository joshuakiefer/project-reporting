interface FocusScoreProps {
  score: number;
  label: string;
  deepWorkMinutes: number;
  contextSwitches: number;
  longestStreak: number;
}

export default function FocusScore({
  score,
  label,
  deepWorkMinutes,
  contextSwitches,
  longestStreak,
}: FocusScoreProps) {
  const getScoreColor = (s: number) => {
    if (s >= 80) return "var(--success)";
    if (s >= 60) return "var(--primary)";
    if (s >= 40) return "var(--warning)";
    return "var(--danger)";
  };

  const getScoreLabel = (s: number) => {
    if (s >= 80) return "Excellent";
    if (s >= 60) return "Good";
    if (s >= 40) return "Fair";
    if (s > 0) return "Needs Work";
    return "No Data";
  };

  const color = getScoreColor(score);
  const circumference = 2 * Math.PI * 54;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="focus-score-card">
      <div className="focus-ring-container">
        <svg viewBox="0 0 120 120" className="focus-ring-svg">
          {/* Background ring */}
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="var(--border)"
            strokeWidth="8"
          />
          {/* Score ring */}
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            transform="rotate(-90 60 60)"
            className="focus-ring-progress"
          />
        </svg>
        <div className="focus-ring-value">
          <span className="focus-score-number" style={{ color }}>
            {score}
          </span>
          <span className="focus-score-unit">/ 100</span>
        </div>
      </div>

      <div className="focus-score-label" style={{ color }}>
        {getScoreLabel(score)}
      </div>
      <div className="focus-score-period">{label}</div>

      <div className="focus-metrics">
        <div className="focus-metric">
          <span className="focus-metric-value">{deepWorkMinutes}m</span>
          <span className="focus-metric-label">Deep Work</span>
        </div>
        <div className="focus-metric-divider" />
        <div className="focus-metric">
          <span className="focus-metric-value">{contextSwitches}</span>
          <span className="focus-metric-label">Switches</span>
        </div>
        <div className="focus-metric-divider" />
        <div className="focus-metric">
          <span className="focus-metric-value">{longestStreak}m</span>
          <span className="focus-metric-label">Best Streak</span>
        </div>
      </div>
    </div>
  );
}
