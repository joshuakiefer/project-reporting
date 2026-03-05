import { useState } from "react";
import { useStatus } from "./hooks/useApi";
import Overlay from "./pages/Overlay";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import StatusBar from "./components/StatusBar";
import Nav from "./components/Nav";

type Page = "overlay" | "dashboard" | "settings";

export default function App() {
  const [page, setPage] = useState<Page>("overlay");
  const { status, error } = useStatus();

  return (
    <div className="app">
      <Nav current={page} onNavigate={setPage} />

      <main className="app-content">
        {error && (
          <div className="error-banner">
            {error} — Make sure the backend is running.
          </div>
        )}

        {page === "overlay" && <Overlay />}
        {page === "dashboard" && <Dashboard />}
        {page === "settings" && <Settings />}
      </main>

      <StatusBar status={status} />
    </div>
  );
}
