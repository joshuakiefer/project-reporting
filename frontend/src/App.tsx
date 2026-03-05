import { useEffect, useState } from "react";
import { useStatus } from "./hooks/useApi";
import Overlay from "./pages/Overlay";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import StatusBar from "./components/StatusBar";
import Nav from "./components/Nav";
import OnboardingWizard from "./components/onboarding/OnboardingWizard";
import ToastContainer, { useToasts } from "./components/toast/ToastContainer";

type Page = "overlay" | "dashboard" | "settings";

export default function App() {
  const [page, setPage] = useState<Page>("overlay");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const { status, error } = useStatus();
  const { toasts, addToast, dismissToast } = useToasts();

  // Check onboarding status
  useEffect(() => {
    fetch("http://127.0.0.1:8321/api/onboarding/status")
      .then((r) => r.json())
      .then((data) => {
        if (!data.completed) setShowOnboarding(true);
      })
      .catch(() => setShowOnboarding(true));
  }, []);

  const handleOnboardingComplete = async () => {
    setShowOnboarding(false);
    try {
      await fetch("http://127.0.0.1:8321/api/onboarding/complete", {
        method: "POST",
      });
    } catch {
      // Ignore — the user completed it locally
    }
    addToast({
      type: "success",
      title: "Welcome to WorkOptimize AI!",
      body: "Click 'Start Watching' to begin optimizing your workflow.",
      duration: 5000,
    });
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Ctrl+Shift+1/2/3 for tab switching
      if (e.ctrlKey && e.shiftKey) {
        if (e.key === "1") { e.preventDefault(); setPage("overlay"); }
        if (e.key === "2") { e.preventDefault(); setPage("dashboard"); }
        if (e.key === "3") { e.preventDefault(); setPage("settings"); }
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  if (showOnboarding) {
    return <OnboardingWizard onComplete={handleOnboardingComplete} />;
  }

  return (
    <div className="app">
      <Nav current={page} onNavigate={setPage} />

      <main className="app-content">
        {error && (
          <div className="error-banner">
            <span className="error-icon">!</span>
            {error} — Make sure the backend is running: <code>workoptimize serve</code>
          </div>
        )}

        {page === "overlay" && <Overlay addToast={addToast} />}
        {page === "dashboard" && <Dashboard />}
        {page === "settings" && <Settings addToast={addToast} />}
      </main>

      <StatusBar status={status} />
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
