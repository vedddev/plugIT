import { api } from "./api";

export interface PlaygroundModel { id: string; owned_by: string; }

const storageKey = (userId: string) => `rim-playground-key:${userId}`;

export async function getPlaygroundKey(userId: string): Promise<string> {
  const stored = sessionStorage.getItem(storageKey(userId));
  if (stored) return stored;
  const created = await api.createApiKey({ name: "RIM Playground" });
  sessionStorage.setItem(storageKey(userId), created.key);
  return created.key;
}

async function gatewayRequest(path: string, apiKey: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(path, {
    ...init,
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json", ...(init.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || body?.error?.message || "The gateway could not complete the request.");
  }
  return response;
}

export async function listPlaygroundModels(apiKey: string): Promise<PlaygroundModel[]> {
  const response = await gatewayRequest("/v1/models", apiKey);
  const body = await response.json() as { data?: PlaygroundModel[] };
  return body.data ?? [];
}

export interface PlaygroundOptions { temperature?: number; maxTokens?: number; }

export async function streamCompletion(apiKey: string, messages: { role: "user" | "assistant"; content: string }[], model: string, options: PlaygroundOptions, signal: AbortSignal, onText: (text: string) => void): Promise<void> {
  const response = await gatewayRequest("/v1/chat/completions/stream", apiKey, { method: "POST", signal, body: JSON.stringify({
    model, messages, stream: true,
    ...(options.temperature !== undefined ? { temperature: options.temperature } : {}),
    ...(options.maxTokens !== undefined ? { max_tokens: options.maxTokens } : {}),
  }) });
  if (!response.body) throw new Error("Streaming is not supported by this browser.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  while (true) {
    const { value, done } = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), { stream: !done });
    const events = pending.split("\n\n");
    pending = events.pop() ?? "";
    for (const event of events) {
      const data = event.split("\n").find((line) => line.startsWith("data: "))?.slice(6);
      if (!data || data === "[DONE]") continue;
      const payload = JSON.parse(data);
      if (payload.error) throw new Error(payload.error.message || "The provider stopped streaming.");
      const content = payload.choices?.[0]?.delta?.content;
      if (content) onText(content);
    }
    if (done) break;
  }
}
