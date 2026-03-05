import { useEffect, useState } from "react";
import {
  getSettings,
  updateCaptureSettings,
  getAuthStatus,
  login,
  logout,
} from "../services/api";

export default function Settings() {
  const [interval, setInterval_] = useState(5);
  const [excludedApps, setExcludedApps] = useState("");
  const [blurSensitive, setBlurSensitive] = useState(true);
  const [saved, setSaved] = useState(false);

  // Auth
  const [auth, setAuth] = useState<{ authenticated: boolean; email: string | null; tier: string }>({
    authenticated: false,
    email: null,
    tier: "free",
  });
  const [email, setEmail] = useState("");
  const [licenseKey, setLicenseKey] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((s: Record<string, unknown>) => {
        const capture = s.capture as Record<string, unknown> | undefined;
        if (capture) {
          setInterval_(capture.interval_seconds as number ?? 5);
          setBlurSensitive(capture.blur_sensitive as boolean ?? true);
          const apps = capture.excluded_apps as string[] | undefined;
          if (apps) setExcludedApps(apps.join(", "));
        }
      })
      .catch(() => {});

    getAuthStatus().then(setAuth).catch(() => {});
  }, []);

  const handleSave = async () => {
    await updateCaptureSettings({
      interval_seconds: interval,
      excluded_apps: excludedApps.split(",").map((s) => s.trim()).filter(Boolean),
      blur_sensitive: blurSensitive,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleLogin = async () => {
    setAuthError(null);
    try {
      await login(email, licenseKey);
      const status = await getAuthStatus();
      setAuth(status);
      setEmail("");
      setLicenseKey("");
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Login failed");
    }
  };

  const handleLogout = async () => {
    await logout();
    setAuth({ authenticated: false, email: null, tier: "free" });
  };

  return (
    <div className="settings-page">
      <h2>Settings</h2>

      <section className="settings-section">
        <h3>Capture</h3>

        <div className="form-group">
          <label>Capture interval (seconds)</label>
          <input
            type="number"
            min={1}
            max={60}
            value={interval}
            onChange={(e) => setInterval_(Number(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label>Excluded apps (comma-separated)</label>
          <input
            type="text"
            value={excludedApps}
            onChange={(e) => setExcludedApps(e.target.value)}
            placeholder="1Password, LastPass, Bitwarden"
          />
        </div>

        <div className="form-group form-group-inline">
          <input
            type="checkbox"
            id="blur-sensitive"
            checked={blurSensitive}
            onChange={(e) => setBlurSensitive(e.target.checked)}
          />
          <label htmlFor="blur-sensitive">
            Auto-blur sensitive content (passwords, credit cards)
          </label>
        </div>

        <button className="btn btn-primary" onClick={handleSave}>
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </section>

      <section className="settings-section">
        <h3>Account</h3>

        {auth.authenticated ? (
          <div className="auth-info">
            <p>
              Signed in as <strong>{auth.email}</strong>
            </p>
            <p>
              Plan: <span className="tag">{auth.tier}</span>
            </p>
            <button className="btn btn-ghost" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
        ) : (
          <div className="auth-form">
            <p className="settings-hint">
              Enter your license key to unlock Pro features.
            </p>
            {authError && <div className="error-text">{authError}</div>}
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
            <div className="form-group">
              <label>License Key</label>
              <input
                type="text"
                value={licenseKey}
                onChange={(e) => setLicenseKey(e.target.value)}
                placeholder="WO-XXXX-XXXX-XXXX"
              />
            </div>
            <button className="btn btn-primary" onClick={handleLogin}>
              Activate License
            </button>
          </div>
        )}
      </section>

      <section className="settings-section">
        <h3>Privacy & Security</h3>
        <ul className="privacy-list">
          <li>All screenshots are encrypted with AES-256 before storage</li>
          <li>Data stays on your machine — nothing is sent to the cloud without your opt-in</li>
          <li>Only the current screen context is sent to Claude API for analysis</li>
          <li>Sensitive content (passwords, financial data) is automatically redacted before API calls</li>
          <li>Data is automatically deleted after your configured retention period</li>
        </ul>
      </section>
    </div>
  );
}
