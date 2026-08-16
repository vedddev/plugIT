export interface User {
  id: string;
  email: string;
  name?: string | null;
  full_name?: string | null;
  username?: string | null;
  role: string;
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json", ...(init.headers || {}) },
  });
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail || "Authentication request failed.");
  return body as T;
}

export const auth = {
  login: (email: string, password: string) => call<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (name: string, email: string, password: string) => call<User>("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) }),
  getCurrentUser: () => call<User>("/auth/me"),
  logout: () => call<void>("/auth/logout", { method: "POST" }),
};
