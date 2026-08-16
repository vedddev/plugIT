import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { auth, type User } from "./auth";

interface AuthContextValue { user: User | null; ready: boolean; signIn: (email: string, password: string) => Promise<User>; register: (name: string, email: string, password: string) => Promise<User>; signOut: () => Promise<void>; }
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => { auth.getCurrentUser().then(setUser).catch(() => setUser(null)).finally(() => setReady(true)); const clear = () => setUser(null); window.addEventListener("rim:unauthorized", clear); return () => window.removeEventListener("rim:unauthorized", clear); }, []);
  const signIn = useCallback(async (email: string, password: string) => { const next = await auth.login(email, password); setUser(next); return next; }, []);
  const register = useCallback(async (name: string, email: string, password: string) => { const next = await auth.register(name, email, password); setUser(next); return next; }, []);
  const signOut = useCallback(async () => { await auth.logout(); setUser(null); }, []);
  const value = useMemo(() => ({ user, ready, signIn, register, signOut }), [user, ready, signIn, register, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("useAuth must be used within AuthProvider"); return value; }
