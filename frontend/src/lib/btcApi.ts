// BTC chart API — isolated client for the /api/btc/* routes.
// Same base URL + error convention as lib/api.ts (which stays untouched).
import { API_BASE } from "./api";

export type BtcTf = "1m" | "5m" | "15m" | "1h" | "4h";
export type BtcMode = "continuous" | "daily";
export type BtcVersion = "v1" | "v2" | "v3" | "v4" | "v5" | "v6" | "v7" | "v8" | "v9" | "v10" | "v11" | "v12" | "v13" | "v15" | "v16" | "v17" | "v18";

export interface BtcCandle {
  date: string;
  ts: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  oi: number;
}

export interface BtcSwing {
  day: string;
  swing_index: number;
  seg: {
    dir: "B" | "S";
    start_idx: number;
    start_px: number;
    end_idx: number;
    end_px: number;
  };
  source: "chop" | "sustain" | null;
  dir: "up" | "down";
  /** "FS" or "SUS" — label at the swing's structural completion. */
  kind: string;
  /** "B1", "B2", "FLIP" or null — the decisive break kind. */
  break_kind: "B1" | "B2" | "FLIP" | null;
  /** Ordered break marks for this swing (idx = global bar index in window). */
  breaks: {
    idx: number;
    time: string;
    kind: "B1" | "B2" | "FLIP";
    dir: "up" | "down";
    px: number;
  }[];
  confirmed_at_idx: number;
  confirmed_at_time: string;
  /** Bar where the swing's OWN opposing pivot broke (FS marker point). */
  fs_at_idx?: number;
  fs_at_time?: string;
}

export interface BtcFlowSegment {
  dir: "B" | "S";
  startIdx: number;
  startPx: number;
  endIdx: number;
  endPx: number;
}

export interface BtcChartResponse {
  tf: BtcTf;
  mode: BtcMode;
  count: number;
  first_ts: string | null;
  last_ts: string | null;
  candles: BtcCandle[];
  swings: BtcSwing[];
  flow: BtcFlowSegment[];
}

export const BTC_TFS: BtcTf[] = ["1m", "5m", "15m", "1h", "4h"];

export async function getBtcChart(
  tf: BtcTf,
  mode: BtcMode,
  limit: number | null,
  minBars?: number,
): Promise<BtcChartResponse> {
  const params = new URLSearchParams({ tf, mode });
  if (limit && limit > 0) params.set("limit", String(limit));
  if (minBars && minBars >= 2) params.set("min_bars", String(minBars));
  const res = await fetch(`${API_BASE}/api/btc/chart?${params.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<BtcChartResponse>;
}

// --- position engine (backtest) ---

export type EntryBreak = "decisive" | "b2" | "flip";
export type SlMode = "swing" | "pct";
export type TrailingMode = "off" | "r" | "swing";
export type BiasMode = "off" | "15m";
export type RegimeMode = "off" | "streak_311";

export interface BtcTrade {
  trade_no: number;
  dir: "long" | "short";
  swing_no: number;
  break_kind: string;
  entry_idx: number;
  entry_ts: number;
  entry_date: string;
  entry_price: number;
  sl: number;
  target: number;
  exit_idx: number;
  exit_ts: number;
  exit_date: string;
  exit_price: number;
  outcome: "target" | "sl" | "be" | "trail" | "open";
  r_multiple: number;
  /** round-trip fee+slippage cost of this trade, in R (0 when fee_pct=0). */
  cost_r?: number;
  bars_held: number;
}

export interface BtcTradeStats {
  trades: number;
  closed: number;
  open: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_r: number;
  avg_r: number;
  avg_win_r: number;
  avg_loss_r: number;
  profit_factor?: number;
  payoff?: number;
  expectancy?: number;
  max_drawdown_r: number;
  max_drawdown_duration_trades?: number;
  max_drawdown_start?: number;
  max_drawdown_end?: number;
  max_consecutive_losses?: number;
  max_consecutive_wins?: number;
  avg_bars_held?: number;
  max_bars_held?: number;
  longs: number;
  shorts: number;
  /** outcome histogram, count-sorted (target/sl/be/trail/open) */
  outcomes: Record<string, number>;
  equity: { trade_no: number; cum_r: number }[];
  /** cost-adjusted aggregates — total_r minus fee+slippage (in R). */
  net_total_r?: number;
  net_avg_r?: number;
  total_costs_r?: number;
  median_r?: number;
  top1_contribution_r?: number;
  top5_contribution_r?: number;
  top10_contribution_r?: number;
  top1_contribution_pct?: number;
  top5_contribution_pct?: number;
  top10_contribution_pct?: number;
  monthly_r?: Record<string, number>;
  yearly_r?: Record<string, number>;
  monthly_equity?: { month: string; net_r: number; cum_r: number }[];
  rolling_20?: { trade_no: number; net_r: number }[];
  rolling_50?: { trade_no: number; net_r: number }[];
  rolling_20_min?: number;
  rolling_20_max?: number;
  rolling_20_last?: number;
  rolling_50_min?: number;
  rolling_50_max?: number;
  rolling_50_last?: number;
}

export interface BtcBacktestParams {
  entryBreak: EntryBreak;
  slMode: SlMode;
  slPct: number;
  rrTarget: number;
  trailing: TrailingMode;
  trailDistanceR: number;
  breakevenR: number;
  bias: BiasMode;
  /** SwingEngine minBars (sweep winner: 20 > 14 > 7 on BTC). */
  minBars: number;
  /** daily-color streak regime gate (3-1-1). */
  regime: RegimeMode;
  /** fee % per side (e.g. 0.05 = Binance taker) — 0 shows the raw backtest. */
  feePct: number;
  /** adverse exit slippage in price points. */
  slippagePts: number;
}

export interface BtcBacktestResponseParams {
  tf: BtcTf;
  mode: BtcMode;
  limit: number | null;
  fee_pct: number;
  slippage_pts: number;
  /** "1m" = exits resolved on 1-minute candles (precise fills). */
  fill_tf: string;
  entry_break: EntryBreak;
  sl_mode: SlMode;
  sl_pct: number;
  rr_target: number;
  trailing: TrailingMode;
  trail_distance_r: number;
  breakeven_r: number;
  skip_first: boolean;
  bias: BiasMode;
  bias_applied: boolean;
  min_bars: number;
  regime: RegimeMode;
  version: BtcVersion;
  /** present when htf_ltf != off */
  htf_ltf?: string;
  htf_ltf_ver?: string;
  /** present when htf_ltf_ver = v3/v5/v6 (extension stop level, in R) */
  ext_stop_r?: number;
  /** present when htf_ltf_ver = v5 (SL = pivot + N x ATR14 buffer) */
  sl_buf_atr?: number;
  /** present when htf_ltf_ver = v6 (SL = highest-high/lowest-low of N bars) */
  sl_hhll_n?: number;
  /** merged-equity drawdown of the combined book (1h legs + 15m legs) */
  combined_maxdd?: number;
}

export interface BtcBacktestResponse {
  params: BtcBacktestResponseParams;
  count: number;
  swings_used: number;
  trades: BtcTrade[];
  stats: BtcTradeStats;
  /** present when htf_ltf != off: the 1h book + its stats + merged numbers */
  htf_trades?: BtcTrade[];
  htf_stats?: BtcTradeStats;
  /** 1h book net + 15m book net (both after costs) */
  combined_net?: number;
}

export type HtfLtfMode = "off" | "5m" | "15m";
/** HTF-LTF engine version — v3 = Extension Stop, v5 = + ATR-buffered SL, v6 = + N-bar structure SL, v11 = Conditional HTF (all-positive 539 +172.5), v12+cd20 = FROZEN BASELINE (414 trades, +265.3R gross, all 4 years positive), v13 = cooldown 30, v15 = recover 1R, v16 = entry distance (rejected), v17 = ATR filter (rejected), v18 = streak halt at 5L (+331.1R net, NEW BEST), v19 = 1.5R window (rejected, see fix/research_v19.md). */
export type HtfLtfVer = "v1" | "v3" | "v5" | "v6" | "v11" | "v12" | "v13" | "v15" | "v16" | "v17" | "v18" | "v19";

export async function getBtcBacktest(
  tf: BtcTf,
  mode: BtcMode,
  limit: number | null,
  p: BtcBacktestParams,
  version: BtcVersion = "v1",
  htfLtf: HtfLtfMode = "off",
  htfLtfVer: HtfLtfVer = "v1",
): Promise<BtcBacktestResponse> {
  const q = new URLSearchParams({
    tf,
    mode,
    fee_pct: String(p.feePct),
    slippage_pts: String(p.slippagePts),
    entry_break: p.entryBreak,
    sl_mode: p.slMode,
    sl_pct: String(p.slPct),
    rr_target: String(p.rrTarget),
    trailing: p.trailing,
    trail_distance_r: String(p.trailDistanceR),
    breakeven_r: String(p.breakevenR),
    bias: p.bias,
    min_bars: String(p.minBars),
    regime: p.regime,
    version,
    htf_ltf: htfLtf,
    htf_ltf_ver: htfLtfVer,
  });
  if (limit && limit > 0) q.set("limit", String(limit));
  const res = await fetch(`${API_BASE}/api/btc/backtest?${q.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<BtcBacktestResponse>;
}

// --- data coverage (status) ---

export interface BtcStatusTf {
  exists: boolean;
  rows: number;
  first_ts: string | null;
  last_ts: string | null;
}

export interface BtcStatusResponse {
  tfs: Record<string, BtcStatusTf>;
}

export async function getBtcStatus(): Promise<BtcStatusResponse> {
  const res = await fetch(`${API_BASE}/api/btc/status`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<BtcStatusResponse>;
}

export async function getBtcVersions(): Promise<{ versions: BtcVersion[]; labels: Record<string, string>; default: BtcVersion }> {
  const res = await fetch(`${API_BASE}/api/btc/versions`, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// --- strategy summary ("konsi best hai" table) ---

export interface BtcSummaryRow {
  rank: number;
  key: string;
  label: string;
  /** preset's OWN reference timeframe the row was measured on (bestTf) */
  tf: BtcTf;
  entry_break: EntryBreak;
  min_bars: number;
  trailing: TrailingMode;
  breakeven_r: number;
  bias: BiasMode;
  regime: RegimeMode;
  trades: number;
  win_rate: number;
  /** zero-cost R (what the raw sim made) */
  base_r: number;
  /** fee+slippage cost in R */
  costs_r: number;
  /** net_r = base_r - costs_r — the honest number */
  net_r: number;
}

export interface BtcSummaryResponse {
  tf: BtcTf;
  mode: BtcMode;
  limit: number | null;
  count: number;
  fee_pct: number;
  slippage_pts: number;
  version: BtcVersion;
  rows: BtcSummaryRow[];
  best: string | null;
}

// --- data fetch (fill data button) ---

export interface BtcFetchResult {
  tf: string;
  ok: boolean;
  seeded?: boolean;
  note?: string;
  fetched: number;
  appended: number;
  last_ts: string | null;
  error?: string;
}

export interface BtcFetchResponse {
  results: BtcFetchResult[];
}

export async function fetchBtcData(tfs?: string[]): Promise<BtcFetchResponse> {
  const res = await fetch(`${API_BASE}/api/btc/fetch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tfs: tfs ?? null }),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<BtcFetchResponse>;
}

export async function getBtcSummary(
  tf: BtcTf,
  mode: BtcMode,
  limit: number | null,
  feePct: number,
  slippagePts: number,
  version: BtcVersion = "v1",
): Promise<BtcSummaryResponse> {
  const q = new URLSearchParams({
    tf,
    mode,
    fee_pct: String(feePct),
    slippage_pts: String(slippagePts),
    version,
  });
  if (limit && limit > 0) q.set("limit", String(limit));
  const res = await fetch(`${API_BASE}/api/btc/summary?${q.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<BtcSummaryResponse>;
}
