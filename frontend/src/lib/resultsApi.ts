"use client";

/**
 * Client for /api/btc/results*.
 *
 * Follows the btcApi.ts pattern deliberately: hand-rolled URLSearchParams and the
 * same res.ok block, rather than the shared request() in api.ts. btcApi.ts keeps
 * itself isolated from api.ts on purpose, and a third client that quietly reused
 * api.ts would be the first place those two conventions got mixed.
 *
 * There is no cache here on purpose. The artifact on the server is already the
 * one source of truth and it re-reads when its mtime changes; a sessionStorage
 * layer on top would only reintroduce the staleness the artifact was chosen to
 * avoid, which is why btcCache.ts is not used either.
 */
import { API_BASE } from "@/lib/api";

export type BookTag =
  | "zero-negative"
  | "low-DD"
  | "short-underwater"
  | "low-tail"
  | "cost-2x-safe"
  | "2x-cost-death"
  | "consistent-eras"
  | "never-negative-50";

/** One point of the equity series: [trade R, cumulative R, drawdown R]. */
export type EquityPoint = [number, number, number];

export interface ResultBook {
  name: string;
  desc: string;
  family: "multi" | "sig";
  swing: string;
  engine?: string;
  n: number;
  net: number;
  expectancy: number;
  pf: number | null;
  wr: number;
  avg_win: number;
  avg_loss: number;
  median_r: number;
  max_win: number;
  max_loss: number;
  sd: number;
  tstat: number;
  max_dd: number;
  net_to_dd: number | null;
  dd_pct_of_net: number | null;
  longest_underwater: number;
  n_dd_periods: number;
  ulcer: number;
  sortino: number;
  calmar: number;
  uw_pct: number;
  recovery: number;
  max_streak: number;
  worst_roll20: number;
  worst_roll50: number;
  worst_roll100: number;
  top1_contrib: number | null;
  top5_contrib: number | null;
  top10_contrib: number | null;
  cap10_net: number;
  cost_1x: number;
  cost_2x: number;
  cost_3x: number;
  is_net: number;
  is_n: number;
  is_exp: number;
  oos_net: number;
  oos_n: number;
  oos_exp: number;
  retention: number | null;
  is_sign: boolean;
  oos_sign: boolean;
  halfs: Record<string, number>;
  neg_cells: string[];
  years_positive: number | null;
  params: number;
  tuned: number;
  series: EquityPoint[];
  position_mode: "multi" | "single" | "inherit";
  position_explicit: boolean;
  tags: BookTag[];

  /** Paired-permutation p-values against the shipping book. A p below 0.05 means
   *  this arm's CHOICE OF TRADES beats its parent's by more than reshuffling the
   *  same trades would. null is "not measured", which is NOT the same as 0.5. */
  null_p_is: number | null;
  null_p_oos: number | null;
  null_dnet_is: number;
  null_dnet_oos: number;
  null_sig_is: boolean;
  null_sig_oos: boolean;
  null_sig: boolean;
}

export interface ResultsPayload {
  generated_from: string;
  dd_budget: number;
  books: ResultBook[];
  count: number;
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

export function getResults(family?: "multi" | "sig", refresh = false) {
  const q = new URLSearchParams();
  if (family) q.set("family", family);
  if (refresh) q.set("refresh", "true");
  const qs = q.toString();
  return get<ResultsPayload>(`/api/btc/results${qs ? `?${qs}` : ""}`);
}

export function getResultBook(name: string) {
  return get<ResultBook>(`/api/btc/results/${name}`);
}