// Centralized TypeScript types for the SmartLLM dashboard API.
// These mirror the response shapes from the FastAPI backend so every
// component sees the same data model.

export type Period = "today" | "7d" | "30d" | "all";
export type RequestStatus = "success" | "failed" | "cached" | "all";

export interface Stats {
  period: Period;
  total_requests: number;
  requests_today: number;
  successful_requests: number;
  failed_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost: number;
  average_latency: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
}

export interface UsageBucket {
  name: string;
  requests: number;
  total_tokens: number;
  total_cost: number;
}

export interface TimeSeriesPoint {
  date: string;
  requests: number;
  total_tokens: number;
  total_cost: number;
}

export interface UsageResponse {
  period: Period;
  provider_usage: UsageBucket[];
  model_usage: UsageBucket[];
  time_series: TimeSeriesPoint[];
}

export interface RequestEvent {
  id: string;
  api_key_id: string;
  provider: string | null;
  model: string | null;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  success: boolean;
  latency_ms: number;
  cached: boolean;
  created_at: string;
}

export interface RequestPage {
  total: number;
  limit: number;
  offset: number;
  data: RequestEvent[];
}

export interface ProviderMetric {
  name: string;
  requests: number;
  successful_requests: number;
  failed_requests: number;
  total_tokens: number;
  total_cost: number;
  average_latency: number;
  error_rate: number;
}

export interface ProvidersResponse {
  period: Period;
  registered: string[];
  models: Record<string, string[]>;
  catalog: Record<string, string[]>;
  health: Record<string, boolean>;
  metrics: ProviderMetric[];
  known_providers: string[];
}

export interface ModelMetric {
  model: string;
  provider: string | null;
  in_catalog: boolean;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost: number;
  average_latency: number;
  error_rate: number;
}

export interface ModelsResponse {
  period: Period;
  data: ModelMetric[];
  observed_providers: string[];
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
  metadata: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export interface FiltersResponse {
  providers: string[];
  models: { model: string; provider: string | null }[];
}

export interface HealthResponse {
  status: string;
}
