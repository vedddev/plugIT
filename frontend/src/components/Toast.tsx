import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

export type ToastTone = "success" | "error" | "info";

export interface ToastMessage {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}

export function ToastStack({ toasts, onDismiss }: ToastProps) {
  if (!toasts.length) return null;
  return createPortal(
    <div className="toast-stack" role="region" aria-label="Notifications">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body,
  );
}

function ToastItem({ toast, onDismiss }: { toast: ToastMessage; onDismiss: (id: number) => void }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const show = window.requestAnimationFrame(() => setVisible(true));
    const timer = window.setTimeout(() => {
      setVisible(false);
      window.setTimeout(() => onDismiss(toast.id), 200);
    }, 4500);
    return () => {
      window.cancelAnimationFrame(show);
      window.clearTimeout(timer);
    };
  }, [onDismiss, toast.id]);

  const Icon = toast.tone === "success" ? CheckCircle2 : toast.tone === "error" ? AlertCircle : Info;
  return (
    <div
      className={`toast toast--${toast.tone} ${visible ? "toast--visible" : ""}`}
      role="status"
    >
      <Icon size={18} className="toast__icon" />
      <div className="toast__body">
        <div className="toast__title">{toast.title}</div>
        {toast.description && <div className="toast__description">{toast.description}</div>}
      </div>
      <button
        className="toast__close"
        onClick={() => {
          setVisible(false);
          window.setTimeout(() => onDismiss(toast.id), 200);
        }}
        aria-label="Dismiss notification"
        type="button"
      >
        <X size={14} />
      </button>
    </div>
  );
}
