import { AppStatus } from "../services/api";

interface StatusBarProps {
  status: AppStatus | null;
}

export default function StatusBar({ status }: StatusBarProps) {
  if (!status) {
    return (
      <footer className="status-bar status-bar--offline">
        <span className="status-dot offline" />
        Connecting to backend...
      </footer>
    );
  }

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  return (
    <footer className={`status-bar ${status.running ? "status-bar--active" : "status-bar--idle"}`}>
      <span className={`status-dot ${status.running ? "active" : "idle"}`} />
      {status.running ? (
        <>
          Watching · {formatUptime(status.uptime_seconds)} ·{" "}
          {status.total_suggestions} suggestions
          {status.active_app && <> · {status.active_app}</>}
        </>
      ) : (
        "Paused"
      )}
      <span className="status-plan">{status.subscription}</span>
    </footer>
  );
}
