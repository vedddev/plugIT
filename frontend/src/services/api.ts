// Centralized HTTP client. All dashboard requests go through here so
// loading, error, and authentication handling live in one place.

import type {
  ApiKey,
  ApiKeyCreated,
  FiltersResponse,
  ModelsResponse,
  Period,
  ProvidersResponse,
  RequestEvent,
  RequestPage,
  RequestStatus,
  Stats,
  UsageResponse,
  HealthResponse,
} from "../types/api";

export class ApiError extends Error {
  status: number;
  body: unknown;
  isAuth: boolean;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
    this.isAuth = status === 401 || status === 403;
  }
}

export interface ApiClient {
  health(): Promise<HealthResponse>;
  stats(period: Period): Promise<Stats>;
  usage(period: Period): Promise<UsageResponse>;
  requests(params: {
    period?: Period;
    provider?: string | null;
    model?: string | null;
    status?: RequestStatus | null;
    search?: string | null;
    limit?: number;
    offset?: number;
  }): Promise<RequestPage>;
  requestDetail(id: string): Promise<RequestEvent>;
  providers(period: Period): Promise<ProvidersResponse>;
  models(period: Period): Promise<ModelsResponse>;
  filters(): Promise<FiltersResponse>;
  listApiKeys(): Promise<{ data: ApiKey[] }>;
  createApiKey(payload: {
    name: string;
    expires_at?: string | null;
    metadata?: string | null;
  }): Promise<ApiKeyCreated>;
  revokeApiKey(id: string): Promise<ApiKey>;
  rotateApiKey(id: string): Promise<ApiKeyCreated>;
}

let getAdminKey: () => string = () => "";

export function configureApiClient(keyProvider: () => string): void {
  getAdminKey = keyProvider;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const adminKey = getAdminKey();
  if (adminKey) {
    headers.set("X-Admin-Key", adminKey);
  }
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : "Network request failed.",
      0,
      null,
    );
  }
  const text = await response.text();
  const body = text ? safeJson(text) : null;
  if (!response.ok) {
    const message =
      (body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : null) ||
      (body && typeof body === "object" && "error" in body
        ? String(((body as { error: { message?: unknown } }).error.message ?? "Request failed."))
        : `Request failed with status ${response.status}.`);
    throw new ApiError(message, response.status, body);
  }
  return body as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function buildQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const api: ApiClient = {
  health() {
    return request<HealthResponse>("/health");
  },
  stats(period) {
    return request<Stats>(`/dashboard/stats${buildQuery({ period })}`);
  },
  usage(period) {
    return request<UsageResponse>(`/dashboard/usage${buildQuery({ period })}`);
  },
  requests(params) {
    return request<RequestPage>(
      `/dashboard/requests${buildQuery({
        period: params.period ?? "all",
        provider: params.provider ?? undefined,
        model: params.model ?? undefined,
        status: params.status && params.status !== "all" ? params.status : undefined,
        search: params.search ?? undefined,
        limit: params.limit ?? 50,
        offset: params.offset ?? 0,
      })}`,
    );
  },
  requestDetail(id) {
    return request<RequestEvent>(
      `/dashboard/requests/${encodeURIComponent(id)}`,
    );
  },
  providers(period) {
    return request<ProvidersResponse>(
      `/dashboard/providers${buildQuery({ period })}`,
    );
  },
  models(period) {
    return request<ModelsResponse>(
      `/dashboard/models${buildQuery({ period })}`,
    );
  },
  filters() {
    return request<FiltersResponse>("/dashboard/filters");
  },
  listApiKeys() {
    return request<{ data: ApiKey[] }>("/admin/api-keys");
  },
  createApiKey(payload) {
    return request<ApiKeyCreated>("/admin/api-keys", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  revokeApiKey(id) {
    return request<ApiKey>(`/admin/api-keys/${encodeURIComponent(id)}/revoke`, {
      method: "POST",
    });
  },
  rotateApiKey(id) {
    return request<ApiKeyCreated>(
      `/admin/api-keys/${encodeURIComponent(id)}/rotate`,
      { method: "POST" },
    );
  },
};
