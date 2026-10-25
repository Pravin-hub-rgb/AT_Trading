"use client";

import { API_BASE } from "@/lib/api";

export interface ForwardCandidate {
  config: string;
  flags: Record<string, unknown>;
  total_trades_replay: number;
  pre_cutoff: {
    gross: { n: number; sum_r: number; avg_r: number; wr_pct: number; pf: number };
    net: { n: number; sum_r: number; avg_r: number; max_dd: number };
  };
  forward: {
    gross: { n: number; sum_r: number; avg_r: number; wr_pct: number; pf: number };
    net: { n: number; sum_r: number; avg_r: number; max_dd: number;
           median: number; max_win: number; max_loss: number };
    monthly_net: Record<string, number>;
    positive_months: number;
    months: number;
  };
  verdict: string | {
    R2_edge_survival: boolean;
    R2_detail: Record<string, unknown>;
    R4_dd_containment: boolean;
    R4_detail: { net_max_dd_r: number; kill_line_pct_at_1R: number };
    R5_sample_size: string;
    n: number;
  };
  forward_trade_log: {
    entry_date: string;
    dir: string;
    entry_price: number;
    r: number;
    net: number;
    outcome: string;
    bars_held: number;
  }[];
}

export interface ForwardSummary {
  stage: string;
  instrument: string;
  cutoff_ist: string;
  cutoff_ts: number;
  contract: string;
  combined_15m_bars: number;
  combined_1h_bars: number;
  fine_1m_bars: number;
  candidates: Record<string, ForwardCandidate>;
  R3_no_degradation: { pass: boolean | null; detail: Record<string, unknown> };
  elapsed_sec: number;
  artifact_mtime: number;
}

export interface Oct20MarksResponse {
  target_date: string;
  timezone: string;
  mark_count: number;
  marks: {
    swing_index: number;
    confirmed_at_time: string;
    confirmed_at_idx: number;
    dir: string;
    kind: string;
    break_kind: string;
    start_time: string;
    start_px: number;
    end_time: string;
    end_px: number;
    fs_at_time: string;
    source: string;
  }[];
  artifact_mtime: number;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
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

export function getForwardSummary(refresh = false): Promise<ForwardSummary> {
  const qs = refresh ? "?refresh=true" : "";
  return get<ForwardSummary>(`/api/btc/forward${qs}`);
}

export function getForwardBook(bookKey: string, refresh = false): Promise<ForwardCandidate> {
  const qs = refresh ? "?refresh=true" : "";
  return get<ForwardCandidate>(`/api/btc/forward/${bookKey}${qs}`);
}

export function getOct20Marks(refresh = false): Promise<Oct20MarksResponse> {
  const qs = refresh ? "?refresh=true" : "";
  return get<Oct20MarksResponse>(`/api/btc/forward/marks/oct20${qs}`);
}
