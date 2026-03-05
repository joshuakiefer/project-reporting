import { useState } from "react";
import { useSuggestions } from "../hooks/useApi";
import { startCapture, stopCapture, pauseCapture, resumeCapture } from "../services/api";
import SuggestionCard from "../components/SuggestionCard";
import AskBar from "../components/AskBar";
import { Toast } from "../components/toast/ToastContainer";

interface OverlayProps {
  addToast: (toast: Omit<Toast, "id">) => string;
}

export default function Overlay({ addToast }: OverlayProps) {
  const { suggestions, dismiss } = useSuggestions();
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);

  const handleToggle = async () => {
    try {
      if (running) {
        await stopCapture();
        setRunning(false);
        setPaused(false);
        addToast({ type: "info", title: "Stopped watching", duration: 3000 });
      } else {
        await startCapture();
        setRunning(true);
        addToast({
          type: "success",
          title: "Watching your screen",
          body: "Suggestions will appear as you work.",
          duration: 4000,
        });
      }
    } catch {
      addToast({ type: "error", title: "Failed to connect to backend", duration: 5000 });
    }
  };

  const handlePause = async () => {
    try {
      if (paused) {
        await resumeCapture();
        setPaused(false);
      } else {
        await pauseCapture();
        setPaused(true);
      }
    } catch {
      // ignore
    }
  };

  return (
    <div className="overlay-page">
      {/* Hero control area */}
      <div className="overlay-hero">
        <button
          className={`btn btn-xl ${running ? "btn-danger" : "btn-primary"}`}
          onClick={handleToggle}
        >
          <span className={`pulse-dot ${running ? "active" : ""}`} />
          {running ? "Stop Watching" : "Start Watching"}
        </button>
        {running && (
          <button className="btn btn-ghost" onClick={handlePause}>
            {paused ? "Resume" : "Pause"}
          </button>
        )}
      </div>

      {/* Ask bar */}
      <AskBar />

      {/* Suggestions stream */}
      <div className="suggestion-list">
        {suggestions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">{running ? "\u{1F50D}" : "\u{1F4A1}"}</div>
            <p className="empty-state-title">
              {running ? "Analyzing your workflow..." : "Ready to optimize"}
            </p>
            <p className="empty-state-subtitle">
              {running
                ? "AI is watching — suggestions will appear here as you work."
                : "Click \"Start Watching\" to begin. The AI will observe your screen and provide helpful suggestions."}
            </p>
          </div>
        ) : (
          suggestions.map((s) => (
            <SuggestionCard key={s.id} suggestion={s} onDismiss={dismiss} />
          ))
        )}
      </div>
    </div>
  );
}
