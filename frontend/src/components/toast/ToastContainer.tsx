import { useEffect, useState, useCallback } from "react";

export interface Toast {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  body?: string;
  duration?: number; // ms, 0 = persistent
}

interface ToastContainerProps {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}

export default function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [exiting, setExiting] = useState(false);

  const dismiss = useCallback(() => {
    setExiting(true);
    setTimeout(() => onDismiss(toast.id), 300);
  }, [toast.id, onDismiss]);

  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(dismiss, toast.duration);
      return () => clearTimeout(timer);
    }
  }, [toast.duration, dismiss]);

  const typeColors: Record<string, string> = {
    info: "var(--primary)",
    success: "var(--success)",
    warning: "var(--warning)",
    error: "var(--danger)",
  };

  return (
    <div
      className={`toast-item ${exiting ? "toast-exit" : "toast-enter"}`}
      style={{ borderLeftColor: typeColors[toast.type] }}
    >
      <div className="toast-content">
        <strong className="toast-title">{toast.title}</strong>
        {toast.body && <p className="toast-body">{toast.body}</p>}
      </div>
      <button className="toast-close" onClick={dismiss}>
        &times;
      </button>
    </div>
  );
}

/** Hook for managing toasts from anywhere in the app. */
export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, "id">) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts((prev) => [...prev, { ...toast, id }]);
    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, addToast, dismissToast };
}
