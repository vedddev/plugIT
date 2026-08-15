import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { ToastStack, type ToastMessage, type ToastTone } from "../components/Toast";

interface ToastContextValue {
  show: (tone: ToastTone, title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const show = useCallback(
    (tone: ToastTone, title: string, description?: string) => {
      setToasts((prev) => [
        ...prev,
        { id: Date.now() + Math.random(), tone, title, description },
      ]);
    },
    [],
  );

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value = useMemo<ToastContextValue>(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider.");
  }
  return ctx;
}
