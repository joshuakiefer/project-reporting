import { useState } from "react";
import { askQuestion } from "../services/api";

export default function AskBar() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setAnswer(null);
    try {
      const res = await askQuestion(question);
      setAnswer(res.answer);
    } catch (e) {
      setAnswer("Failed to get answer. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <div className="ask-bar">
      <div className="ask-input-row">
        <input
          type="text"
          className="ask-input"
          placeholder="Ask about what's on your screen..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button className="btn btn-primary" onClick={handleAsk} disabled={loading}>
          {loading ? "..." : "Ask"}
        </button>
      </div>
      {answer && (
        <div className="ask-answer">
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}
