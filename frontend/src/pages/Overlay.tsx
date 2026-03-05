import { useCallback, useState } from "react";
import { useSuggestions } from "../hooks/useApi";
import { startCapture, stopCapture, pauseCapture, resumeCapture } from "../services/api";
import SuggestionCard from "../components/SuggestionCard";
import AskBar from "../components/AskBar";

export default function Overlay() {
  const { suggestions, dismiss } = useSuggestions();
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);

  const handleToggle = async () => {
    if (running) {
      await stopCapture();
      setRunning(false);
      setPaused(false);
    } else {
      await startCapture();
      setRunning(true);
    }
  };

  const handlePause = async () => {
    if (paused) {
      await resumeCapture();
      setPaused(false);
    } else {
      await pauseCapture();
      setPaused(true);
    }
  };

  return (
    <div className="overlay-page">
      <div className="overlay-controls">
        <button
          className={`btn ${running ? "btn-danger" : "btn-primary"}`}
          onClick={handleToggle}
        >
          {running ? "Stop Watching" : "Start Watching"}
        </button>
        {running && (
          <button className="btn btn-ghost" onClick={handlePause}>
            {paused ? "Resume" : "Pause"}
          </button>
        )}
      </div>

      <AskBar />

      <div className="suggestion-list">
        {suggestions.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state-title">No suggestions yet</p>
            <p className="empty-state-subtitle">
              {running
                ? "Analyzing your workflow — suggestions will appear here."
                : "Click \"Start Watching\" to begin."}
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
