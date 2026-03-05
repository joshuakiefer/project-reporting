import { useState } from "react";

interface OnboardingWizardProps {
  onComplete: () => void;
}

const STEPS = [
  {
    id: "welcome",
    title: "Welcome to WorkOptimize AI",
    subtitle: "Your personal work optimization assistant",
    description:
      "WorkOptimize watches your screen and provides intelligent suggestions to help you work faster, smarter, and more efficiently.",
    icon: "brain",
  },
  {
    id: "privacy",
    title: "Your Privacy Matters",
    subtitle: "Security-first architecture",
    description:
      "All screenshots are encrypted with AES-256 and stay on your machine. Sensitive content like passwords and banking sites are automatically blocked. You control what gets captured.",
    icon: "shield",
  },
  {
    id: "how-it-works",
    title: "How It Works",
    subtitle: "Three simple steps",
    bullets: [
      "WorkOptimize captures your active window every few seconds",
      "Claude AI analyzes the context and understands what you're doing",
      "You receive real-time tips, shortcuts, and optimization suggestions",
    ],
    icon: "zap",
  },
  {
    id: "patterns",
    title: "Pattern Detection",
    subtitle: "Smarter over time",
    description:
      "Over days and weeks, WorkOptimize detects repetitive workflows — like copying data between apps — and suggests automations that could save you hours every week.",
    icon: "trending-up",
  },
  {
    id: "setup",
    title: "Quick Setup",
    subtitle: "One click to start",
    description:
      "Click 'Start Watching' on the next screen to begin. You can pause anytime, adjust settings, or ask questions about what's on your screen.",
    icon: "play",
  },
];

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      onComplete();
    } else {
      setStep((s) => s + 1);
    }
  };

  const handleSkip = () => {
    onComplete();
  };

  const iconMap: Record<string, string> = {
    brain: "\u{1F9E0}",
    shield: "\u{1F6E1}",
    zap: "\u26A1",
    "trending-up": "\u{1F4C8}",
    play: "\u25B6",
  };

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-card">
        <div className="onboarding-progress">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`onboarding-dot ${i === step ? "active" : ""} ${
                i < step ? "completed" : ""
              }`}
            />
          ))}
        </div>

        <div className="onboarding-icon">{iconMap[current.icon] || ""}</div>

        <h1 className="onboarding-title">{current.title}</h1>
        <p className="onboarding-subtitle">{current.subtitle}</p>

        {current.description && (
          <p className="onboarding-desc">{current.description}</p>
        )}

        {current.bullets && (
          <ul className="onboarding-bullets">
            {current.bullets.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        )}

        <div className="onboarding-actions">
          {!isLast && (
            <button className="btn btn-ghost" onClick={handleSkip}>
              Skip
            </button>
          )}
          <button className="btn btn-primary btn-lg" onClick={handleNext}>
            {isLast ? "Get Started" : "Next"}
          </button>
        </div>

        <div className="onboarding-step-label">
          {step + 1} of {STEPS.length}
        </div>
      </div>
    </div>
  );
}
