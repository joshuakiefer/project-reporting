/**
 * API client for communicating with the local Python backend.
 */

const BASE_URL = "http://127.0.0.1:8321";
const WS_URL = "ws://127.0.0.1:8321/ws";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

// ── Status & Control ────────────────────────────────────────────

export interface AppStatus {
  running: boolean;
  uptime_seconds: number;
  total_captures: number;
  total_suggestions: number;
  active_app: string;
  subscription: string;
}

export const getStatus = () => request<AppStatus>("/api/status");
export const startCapture = () => request("/api/start", { method: "POST" });
export const stopCapture = () => request("/api/stop", { method: "POST" });
export const pauseCapture = () => request("/api/pause", { method: "POST" });
export const resumeCapture = () => request("/api/resume", { method: "POST" });

// ── Suggestions ─────────────────────────────────────────────────

export interface Suggestion {
  id: string;
  category: string;
  title: string;
  body: string;
  priority: number;
  timestamp: number;
  helpful: boolean | null;
}

export const getSuggestions = (limit = 10) =>
  request<{ suggestions: Suggestion[] }>(`/api/suggestions?limit=${limit}`);

export const dismissSuggestion = (id: string) =>
  request(`/api/suggestions/${id}/dismiss`, { method: "POST" });

export const markHelpful = (id: string) =>
  request(`/api/suggestions/${id}/helpful`, { method: "POST" });

// ── Ask ─────────────────────────────────────────────────────────

export const askQuestion = (question: string) =>
  request<{ answer: string }>("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });

// ── Patterns & Reports ──────────────────────────────────────────

export interface Pattern {
  pattern_type: string;
  description: string;
  apps_involved: string[];
  automation_potential: string;
  occurrence_count: number;
}

export const getPatterns = () =>
  request<{ patterns: Pattern[] }>("/api/patterns");

export const getReport = () => request<Record<string, unknown>>("/api/report");

export const generateAutomation = (patternType?: string) =>
  request<{ script: Record<string, string> }>("/api/automate", {
    method: "POST",
    body: JSON.stringify({ pattern_type: patternType }),
  });

// ── Settings ────────────────────────────────────────────────────

export const getSettings = () =>
  request<Record<string, unknown>>("/api/settings");

export const updateCaptureSettings = (settings: Record<string, unknown>) =>
  request("/api/settings/capture", {
    method: "PUT",
    body: JSON.stringify(settings),
  });

// ── Auth ────────────────────────────────────────────────────────

export const login = (email: string, licenseKey: string) =>
  request<{ success: boolean; plan: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, license_key: licenseKey }),
  });

export const logout = () =>
  request("/api/auth/logout", { method: "POST" });

export const getAuthStatus = () =>
  request<{ authenticated: boolean; tier: string; email: string | null }>(
    "/api/auth/status"
  );

// ── WebSocket ───────────────────────────────────────────────────

export function connectWebSocket(
  onMessage: (event: string, data: unknown) => void,
  onError?: (err: Event) => void
): WebSocket {
  const ws = new WebSocket(WS_URL);

  ws.onmessage = (e) => {
    try {
      const { event, data } = JSON.parse(e.data);
      onMessage(event, data);
    } catch {
      // ignore malformed messages
    }
  };

  ws.onerror = (e) => onError?.(e);

  // Auto-reconnect
  ws.onclose = () => {
    setTimeout(() => connectWebSocket(onMessage, onError), 3000);
  };

  return ws;
}
