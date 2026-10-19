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

/**
 * Per-book result of the selection work that happened after the original
 * export. Added by exp_enrich_results.py; absent on books that were never part
 * of the thirteen-book multi selection, which is most of them.
 *
 * The point of carrying it per book is that a reader looking at one row cannot
 * see a confident-looking net and miss the fact that the selection procedure
 * failed its own overfitting check. It rides on the book rather than in a
 * banner that can be scrolled past.
 */
export interface BookAnalysis {
  /** short handle used in conversation and docs - 107, 110, sigm, ... */
  code: string;
  /** e.g. "15/16" - how many pre-declared gate criteria passed */
  gate_passed: string;
  gate_fails: string[];
  gates: { G1: string; G2: string; G3: string; G4: string };
  survives_all_gates: boolean;
  /** Deflated Sharpe probability per era; absent if pbo_dsr.json is missing */
  dsr?: { oos?: { sr: number; dsr: number; p: number; n: number };
          is?: { sr: number; dsr: number; p: number; n: number } };
  /** true only if DSR cleared p<0.05 in both eras */
  dsr_pass?: boolean;
  verdict: string;
}

export interface VerdictBlock {
  headline: string;
  reason: string;
  pbo: { oos: number | null; is: number | null } | null;
  pbo_bar: number;
  book_count_tried: number;
  closest: string[];
  closest_note: string;
  next_step: string;
  see: string;
}

export interface ResultBook {
  analysis?: BookAnalysis;
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
  // Drawdown as a percentage. A bare R figure is not comparable across books of
  // different size - 29.62R on a book that ended at +295R and 29.62R on one that
  // ended at +1,230R are different things. dd_pct_1/2 assume 1R risks 1% (or 2%)
  // of the account; dd_pct_of_peak is the standard (equity - peak) / peak, and
  // dd_recover_pct is what it costs to get back, which is asymmetric.
  dd_pct_1: number;
  dd_pct_2: number;
  dd_pct_of_peak: number | null;
  dd_recover_pct: number | null;
  // Calendar-time drawdown shape. The trade-count measures above say how many
  // trades the fall took; these say how long a person would have been sitting
  // in it. recover_days is null when the deepest drawdown never got back to its
  // own peak, which is a real answer and not a missing value.
  dd_days: number;
  recover_days: number | null;
  worst_3m: number | null;
  worst_6m: number | null;
  worst_12m: number | null;
  // Share of k-trade rolling windows that ended profitable.
  roll10_prof_pct: number;
  roll20_prof_pct: number;
  roll50_prof_pct: number;
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
  // null, deliberately. There is no fixed drawdown ceiling: a limit that rejects
  // a 29R dip on a 1230R book also passes a 29R dip on a 66R one, so it cannot
  // tell a big book from a small one. dd_budget_r_legacy is kept beside it so
  // an old export can still be read. See dd_pct_of_peak, net_to_dd, dd_days and
  // recover_days for the measures that do discriminate.
  dd_budget: number | null;
  dd_budget_note?: string;
  dd_budget_r_legacy?: number;
  /** stamped by exp_enrich_results.py - the answer, at the top of the payload */
  verdict?: VerdictBlock;
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