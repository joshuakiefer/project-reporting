import { useCallback, useEffect, useRef, useState } from "react";
import { AppStatus, Suggestion, getStatus, getSuggestions, connectWebSocket } from "../services/api";

/** Poll the backend for status every N ms. */
export function useStatus(intervalMs = 3000) {
  const [status, setStatus] = useState<AppStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const s = await getStatus();
        if (active) {
          setStatus(s);
          setError(null);
        }
      } catch (e) {
        if (active) setError("Backend not reachable");
      }
    };

    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { status, error };
}

/** Manage suggestions with real-time WebSocket updates. */
export function useSuggestions() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Initial fetch
  useEffect(() => {
    getSuggestions(20)
      .then((res) => setSuggestions(res.suggestions))
      .catch(() => {});
  }, []);

  // Real-time updates via WebSocket
  useEffect(() => {
    wsRef.current = connectWebSocket((event, data) => {
      if (event === "new_suggestion") {
        setSuggestions((prev) => [...prev, data as Suggestion].slice(-50));
      }
    });

    return () => wsRef.current?.close();
  }, []);

  const dismiss = useCallback((id: string) => {
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { suggestions, dismiss };
}
