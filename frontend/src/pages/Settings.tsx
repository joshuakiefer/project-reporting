import { useEffect, useState } from "react";
import {
  getSettings,
  updateCaptureSettings,
  getAuthStatus,
  login,
  logout,
} from "../services/api";
import { Toast } from "../components/toast/ToastContainer";

interface SettingsProps {
  addToast: (toast: Omit<Toast, "id">) => string;
}

export default function Settings({ addToast }: SettingsProps) {
  const [interval, setInterval_] = useState(5);
  const [excludedApps, setExcludedApps] = useState("");
  const [blurSensitive, setBlurSensitive] = useState(true);

  // Auth
  const [auth, setAuth] = useState<{ authenticated: boolean; email: string | null; tier: string }>({
    authenticated: false,
    email: null,
    tier: "free",
  });
  const [email, setEmail] = useState("");
  const [licenseKey, setLicenseKey] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<"capture" | "account" | "privacy" | "billing">("capture");

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
    addToast({ type: "success", title: "Settings saved", duration: 2000 });
  };

  const handleLogin = async () => {
    setAuthError(null);
    try {
      await login(email, licenseKey);
      const status = await getAuthStatus();
      setAuth(status);
      setEmail("");
      setLicenseKey("");
      addToast({ type: "success", title: "License activated!", body: "Pro features are now unlocked.", duration: 4000 });
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "Login failed");
    }
  };

  const handleLogout = async () => {
    await logout();
    setAuth({ authenticated: false, email: null, tier: "free" });
    addToast({ type: "info", title: "Signed out", duration: 3000 });
  };

  const sections = [
    { id: "capture" as const, label: "Capture" },
    { id: "account" as const, label: "Account" },
    { id: "privacy" as const, label: "Privacy" },
    { id: "billing" as const, label: "Plans" },
  ];

  return (
    <div className="settings-page">
      {/* Settings nav */}
      <div className="settings-nav">
        {sections.map((s) => (
          <button
            key={s.id}
            className={`settings-nav-item ${activeSection === s.id ? "active" : ""}`}
            onClick={() => setActiveSection(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Capture Settings */}
      {activeSection === "capture" && (
        <section className="settings-section fade-in">
          <h3>Capture Settings</h3>
          <p className="settings-hint">Control how and when WorkOptimize captures your screen.</p>

          <div className="form-group">
            <label>Capture interval (seconds)</label>
            <div className="slider-group">
              <input
                type="range"
                min={1}
                max={30}
                value={interval}
                onChange={(e) => setInterval_(Number(e.target.value))}
              />
              <span className="slider-value">{interval}s</span>
            </div>
          </div>

          <div className="form-group">
            <label>Excluded apps</label>
            <input
              type="text"
              value={excludedApps}
              onChange={(e) => setExcludedApps(e.target.value)}
              placeholder="1Password, LastPass, Bitwarden"
            />
            <span className="form-hint">Comma-separated. These apps will never be captured.</span>
          </div>

          <div className="form-group form-group-inline">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={blurSensitive}
                onChange={(e) => setBlurSensitive(e.target.checked)}
              />
              <span className="toggle-slider" />
            </label>
            <div>
              <label>Auto-blur sensitive content</label>
              <span className="form-hint">Detects and blurs passwords, credit cards, SSNs</span>
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleSave}>
            Save Settings
          </button>
        </section>
      )}

      {/* Account */}
      {activeSection === "account" && (
        <section className="settings-section fade-in">
          <h3>Account</h3>

          {auth.authenticated ? (
            <div className="auth-info">
              <div className="auth-avatar">
                {auth.email?.charAt(0).toUpperCase() || "?"}
              </div>
              <div className="auth-details">
                <p className="auth-email">{auth.email}</p>
                <p className="auth-plan">
                  <span className={`plan-badge plan-${auth.tier}`}>{auth.tier}</span>
                </p>
              </div>
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
                  className="mono-input"
                />
              </div>
              <button className="btn btn-primary" onClick={handleLogin}>
                Activate License
              </button>
            </div>
          )}
        </section>
      )}

      {/* Privacy */}
      {activeSection === "privacy" && (
        <section className="settings-section fade-in">
          <h3>Privacy & Security</h3>
          <div className="privacy-grid">
            {[
              { icon: "\u{1F512}", title: "AES-256 Encryption", desc: "All screenshots encrypted before storage" },
              { icon: "\u{1F4BB}", title: "Local-Only Data", desc: "Nothing leaves your machine without opt-in" },
              { icon: "\u{1F6E1}", title: "Smart Filtering", desc: "Banking, passwords, and private browsing auto-blocked" },
              { icon: "\u{1F50D}", title: "Content Redaction", desc: "SSNs, credit cards, API keys stripped before API calls" },
              { icon: "\u{1F5D1}", title: "Auto-Cleanup", desc: "Data deleted after your retention period" },
              { icon: "\u{1F4CB}", title: "Audit Log", desc: "Full log of every capture and API call" },
            ].map((item, i) => (
              <div key={i} className="privacy-card">
                <span className="privacy-card-icon">{item.icon}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Plans */}
      {activeSection === "billing" && (
        <section className="settings-section fade-in">
          <h3>Plans</h3>
          <div className="plans-grid">
            {/* Free */}
            <div className={`plan-card ${auth.tier === "free" ? "current" : ""}`}>
              <div className="plan-name">Free</div>
              <div className="plan-price">$0</div>
              <ul className="plan-features">
                <li>Basic suggestions</li>
                <li>50 captures/day</li>
                <li>Ask about your screen</li>
              </ul>
              {auth.tier === "free" && <div className="plan-current-badge">Current Plan</div>}
            </div>

            {/* Pro */}
            <div className={`plan-card featured ${auth.tier === "pro" ? "current" : ""}`}>
              <div className="plan-popular">Most Popular</div>
              <div className="plan-name">Pro</div>
              <div className="plan-price">
                $19<span>/mo</span>
              </div>
              <ul className="plan-features">
                <li>Unlimited captures</li>
                <li>Pattern tracking</li>
                <li>Automation builder</li>
                <li>Focus analytics</li>
                <li>Cloud sync</li>
                <li>Priority support</li>
              </ul>
              {auth.tier === "pro" ? (
                <div className="plan-current-badge">Current Plan</div>
              ) : (
                <button className="btn btn-primary btn-block">Upgrade to Pro</button>
              )}
            </div>

            {/* Team */}
            <div className="plan-card">
              <div className="plan-name">Team</div>
              <div className="plan-price">
                $49<span>/user/mo</span>
              </div>
              <ul className="plan-features">
                <li>Everything in Pro</li>
                <li>Team dashboard</li>
                <li>Admin controls</li>
                <li>Aggregate reports</li>
                <li>SSO integration</li>
              </ul>
              <button className="btn btn-ghost btn-block">Contact Sales</button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
