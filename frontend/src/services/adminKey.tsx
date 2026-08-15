import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { configureApiClient } from "./api";

interface AdminKeyContextValue {
  adminKey: string;
  setAdminKey: (key: string) => void;
  clearAdminKey: () => void;
  ready: boolean;
}

const AdminKeyContext = createContext<AdminKeyContextValue | null>(null);
const STORAGE_KEY = "smartllm.adminKey";

export function AdminKeyProvider({ children }: { children: ReactNode }) {
  const [adminKey, setAdminKeyState] = useState<string>("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY) ?? "";
    setAdminKeyState(stored);
    setReady(true);
  }, []);

  const setAdminKey = useCallback((key: string) => {
    const trimmed = key.trim();
    if (trimmed) {
      sessionStorage.setItem(STORAGE_KEY, trimmed);
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    setAdminKeyState(trimmed);
  }, []);

  const clearAdminKey = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setAdminKeyState("");
  }, []);

  useEffect(() => {
    configureApiClient(() => adminKey);
  }, [adminKey]);

  const value = useMemo<AdminKeyContextValue>(
    () => ({ adminKey, setAdminKey, clearAdminKey, ready }),
    [adminKey, setAdminKey, clearAdminKey, ready],
  );

  return (
    <AdminKeyContext.Provider value={value}>
      {children}
    </AdminKeyContext.Provider>
  );
}

export function useAdminKey(): AdminKeyContextValue {
  const ctx = useContext(AdminKeyContext);
  if (!ctx) {
    throw new Error("useAdminKey must be used within an AdminKeyProvider.");
  }
  return ctx;
}
