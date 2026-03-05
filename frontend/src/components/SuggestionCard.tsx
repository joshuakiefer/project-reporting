import { Suggestion, dismissSuggestion, markHelpful } from "../services/api";

interface SuggestionCardProps {
  suggestion: Suggestion;
  onDismiss: (id: string) => void;
}

const categoryColors: Record<string, string> = {
  tip: "#3b82f6",
  optimization: "#10b981",
  automation: "#f59e0b",
  question: "#8b5cf6",
  warning: "#ef4444",
};

export default function SuggestionCard({ suggestion, onDismiss }: SuggestionCardProps) {
  const color = categoryColors[suggestion.category] || "#6b7280";

  const handleDismiss = async () => {
    await dismissSuggestion(suggestion.id).catch(() => {});
    onDismiss(suggestion.id);
  };

  const handleHelpful = async () => {
    await markHelpful(suggestion.id).catch(() => {});
  };

  return (
    <div className="suggestion-card" style={{ borderLeftColor: color }}>
      <div className="suggestion-header">
        <span className="suggestion-category" style={{ color }}>
          {suggestion.category}
        </span>
        <button className="suggestion-dismiss" onClick={handleDismiss} title="Dismiss">
          &times;
        </button>
      </div>
      <h3 className="suggestion-title">{suggestion.title}</h3>
      <p className="suggestion-body">{suggestion.body}</p>
      <div className="suggestion-actions">
        <button className="btn btn-sm btn-ghost" onClick={handleHelpful}>
          Helpful
        </button>
      </div>
    </div>
  );
}
