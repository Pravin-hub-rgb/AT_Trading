export const API_BASE = "http://127.0.0.1:8003";

export type IntervalKey = "daily" | "5min";

export interface Candle {
  date: string;
  ts: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  oi: number;
}

export interface TokenStatus {
  configured: boolean;
  api_key_configured: boolean;
  api_secret_configured: boolean;
  token_length: number;
  masked_token: string | null;
  valid: boolean | null;
  last_price: number | null;
  last_validated_at: string | null;
  updated_at: string | null;
}

export interface TokenCheck {
  valid: boolean;
  message: string;
  last_price?: number | null;
  status_code?: number | null;
}

export interface IntervalStatus {
  interval: string;
  exists: boolean;
  row_count: number;
  first_ts: string | null;
  last_ts: string | null;
  last_date: string | null;
  expected_date: string | null;
  is_fresh: boolean;
  days_behind: number | null;
  coverage: number;
  total_months: number;
  present_months: number;
  missing_months: string[];
  badge: "fresh" | "stale" | "partial" | "no_data";
  message: string;
  requested_from: string | null;
  requested_to: string | null;
  last_update_at: string | null;
  last_update_status: string | null;
}

export interface DataStatus {
  daily: IntervalStatus;
  "5min": IntervalStatus;
}

export interface Settings {
  auto_update: boolean;
  update_time: string;
  years: number;
}

export interface OperationStatus {
  operation_id: string;
  status: string;
  progress: number;
  message: string;
  log: string[];
  intervals: string[];
  years: number;
  done_months: number;
  total_months: number;
  error: string | null;
  mode: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// --- token ---
export const getHealth = () => request<{ status: string; token_configured: boolean }>("/api/health");

export const getTokenStatus = () => request<TokenStatus>("/api/token/status");

export const saveToken = (creds: { token: string; api_key: string; api_secret: string }) =>
  request<{ ok: boolean; status: TokenStatus }>("/api/token", {
    method: "POST",
    body: JSON.stringify(creds),
  });

export const validateToken = (creds: { token: string; api_key: string; api_secret: string }) =>
  request<TokenCheck>("/api/token/validate", {
    method: "POST",
    body: JSON.stringify(creds),
  });

export const checkToken = () => request<TokenCheck>("/api/token/check");

// --- data status / settings ---
export const getDataStatus = () => request<DataStatus>("/api/data/status");

export const getSettings = () => request<Settings>("/api/settings");

export const putSettings = (patch: Partial<Settings>) =>
  request<Settings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(patch),
  });

// --- jobs ---
export const startDownload = (interval: string, years: number) =>
  request<{ status: string; operation_id: string; mode: string }>("/api/data/download", {
    method: "POST",
    body: JSON.stringify({ interval, years }),
  });

export const updateData = () =>
  request<{ status: string; operation_id: string; mode: string }>("/api/data/update", {
    method: "POST",
    body: JSON.stringify({}),
  });

export const getOperationStatus = (operationId: string) =>
  request<OperationStatus>(`/api/data/status/${operationId}`);

// --- chart ---
export const getChartData = (interval: string, limit?: number) =>
  request<{ interval: string; count: number; candles: Candle[] }>(
    `/api/chart/data?interval=${interval}${limit ? `&limit=${limit}` : ""}`,
  );

// --- swings (S/R) ---
export interface Swing {
  kind: "high" | "low";
  index: number;
  ts: number;
  date: string;
  date_only: string;
  price: number;
}

export interface SwingLevel {
  kind: "high" | "low";
  index: number;
  price: number;
  end_index: number;
}

export interface SwingsResponse {
  interval: string;
  pivot: number;
  levels: number;
  lookahead: number;
  swings: Swing[];
  sr_levels: SwingLevel[];
}

export const getSwings = (interval: string, pivot: number, levels = 5, lookahead = 50) =>
  request<SwingsResponse>(
    `/api/swings?interval=${interval}&pivot=${pivot}&levels=${levels}&lookahead=${lookahead}`,
  );