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
  "1min": IntervalStatus;
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

// --- initial bias (pre-open labels) ---
export type Bias = "bullish" | "bearish" | "unbiased";

export interface OverviewInfo {
  zone?: string;
  lean?: string | null;
  reason?: string;
  sh_price?: number;
  sh_date?: string;
  sl_price?: number;
  sl_date?: string;
  pos_pct?: number;
}

export interface BiasDetails {
  prev_date?: string;
  prev_close?: number;
  closing_signal?: string | null;
  closing_net_pts?: number | null;
  closing_frac?: number | null;
  closing_sustain?: string | null;
  closing_structure?: string | null;
}

export interface PrevSwingPoint {
  index?: number;
  ts: number;
  price: number;
  time?: string;
  kind: "high" | "low";
  tag: string | null;
}

export interface BreakInfo {
  kind: string; // "above" | "below"
  level: number;
  closed_beyond: boolean;
  at: string;
}

export interface PrevDayInfo {
  structure?: string; // bullish | bearish | mixed | unclear
  sustain?: string; // strong | weak
  summary?: string;
  close_pos_pct?: number | null;
  breaks?: BreakInfo[] | null;
  swings?: PrevSwingPoint[];
}

export interface BiasLabel {
  date: string;
  bias: Bias;
  reason: string;
  details?: BiasDetails;
  overview?: OverviewInfo | null;
  prev_day?: PrevDayInfo | null;
}

export interface BiasResponse {
  count: number;
  summary: Record<Bias, number>;
  bias: BiasLabel[];
}

export const getBias = (limit?: number) =>
  request<BiasResponse>(`/api/bias${limit ? `?limit=${limit}` : ""}`);

// --- intraday backtest engine ---
export type TradeOutcome = "target" | "sl" | "eod" | "cost-to-cost" | "ft_fail" | "no_momentum" | "trail";

export interface BacktestParams {
  sl_mode: string;    // avg | avg075 | avg05 | fixed8
  execution: string;  // 5min | 1min
  trailing: string;   // off | ladder
  gap_pct: string;    // gap threshold in %, e.g. "0.27"
}

export const DEFAULT_BT_PARAMS: BacktestParams = {
  sl_mode: "avg",
  execution: "5min",
  trailing: "off",
  gap_pct: "0.27",
};

export interface IntradayTrade {
  dir: "long" | "short";
  case?: string | null;
  entry_time: string;
  entry_ts: number;
  entry_price: number;
  sl: number;
  target: number;
  level: number;
  pace_break_type: string;
  domination_time: string;
  mfe_r: number;
  exit_time?: string;
  exit_ts?: number;
  exit_price?: number;
  outcome?: TradeOutcome;
  r_multiple?: number;
}

export interface IntradayDaySummary {
  date: string;
  bias: Bias;
  raw_bias?: Bias;
  case?: string | null;
  swing_direction: string | null;
  n_trades: number;
  outcomes: string[];
  trades: IntradayTrade[];
}

export interface IntradayStats {
  days_total: number;
  days_traded: number;
  trades: number;
  wins: number;
  win_rate: number;
  total_r: number;
  avg_r: number;
  outcomes: Record<string, number>;
  longs: number;
  shorts: number;
  cases?: Record<string, { trades: number; wins: number; total_r: number }>;
}

export interface IntradayBacktestResponse {
  stats: IntradayStats;
  days: IntradayDaySummary[];
  config?: BacktestParams & { trail_distance_r?: number };
}

export const getIntradayBacktest = (params: BacktestParams = DEFAULT_BT_PARAMS) => {
  const q = new URLSearchParams({
    sl_mode: params.sl_mode,
    execution: params.execution,
    trailing: params.trailing,
    gap_pct: params.gap_pct,
  });
  return request<IntradayBacktestResponse>(`/api/intraday/backtest?${q.toString()}`);
};

// --- first-swing manual ground truth (user-drawn) ---
export interface FsPoint {
  time: string; // "HH:MM"
  kind: "H" | "L";
  px: number;
}

export interface FsDayMark {
  start: FsPoint;
  end: FsPoint;
}

export interface FsManualResponse {
  count: number;
  days: Record<string, FsDayMark>;
}

export const getFirstSwingManual = () => request<FsManualResponse>("/api/firstswing/manual");

export const saveFirstSwingDay = (day: string, mark: FsDayMark) =>
  request<{ ok: boolean; day: string; count: number }>(
    `/api/firstswing/manual?day=${encodeURIComponent(day)}`,
    { method: "POST", body: JSON.stringify(mark) },
  );

export const deleteFirstSwingDay = (day: string) =>
  request<{ ok: boolean; deleted: string; count: number }>(
    `/api/firstswing/manual/${encodeURIComponent(day)}`,
    { method: "DELETE" },
  );