// sessionStorage cache — survives full page reloads, tab switches,
// and Next.js dev-mode remounts. Wiped only when the browser tab closes.

import type {
  BtcBacktestResponse,
  BtcChartResponse,
  BtcStatusResponse,
  BtcSummaryResponse,
} from "@/lib/btcApi";

const CHART_KEY = "btc_cache_chart";
const STATUS_KEY = "btc_cache_status";
const BACKTEST_KEY = "btc_cache_backtest";
const SUMMARY_KEY = "btc_cache_summary";
const TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CacheEntry<T> {
  data: T;
  ts: number;
}

// ── helpers ──────────────────────────────────────────────────────────────────

function read<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const entry = JSON.parse(raw) as CacheEntry<T>;
    if (Date.now() - entry.ts > TTL_MS) {
      sessionStorage.removeItem(key);
      return null;
    }
    return entry.data;
  } catch {
    return null;
  }
}

function write<T>(key: string, data: T) {
  try {
    const entry: CacheEntry<T> = { data, ts: Date.now() };
    sessionStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // quota exceeded or storage disabled — fail silently
  }
}

// ── chart cache (keyed by tf|mode|limit|minBars) ───────────────────────────

export function getCachedChart(key: string): BtcChartResponse | null {
  const map = read<Record<string, BtcChartResponse>>(CHART_KEY);
  return map?.[key] ?? null;
}

export function setCachedChart(key: string, data: BtcChartResponse) {
  const map = read<Record<string, BtcChartResponse>>(CHART_KEY) ?? {};
  map[key] = data;
  write(CHART_KEY, map);
}

// ── status cache ────────────────────────────────────────────────────────────

export function getCachedStatus(): BtcStatusResponse | null {
  return read<BtcStatusResponse>(STATUS_KEY);
}

export function setCachedStatus(data: BtcStatusResponse) {
  write(STATUS_KEY, data);
}

// ── backtest cache (keyed by tf|mode|limit|btParams|version|htfLtf|htfLtfVer) ─

export function getCachedBacktest(key: string): BtcBacktestResponse | null {
  const map = read<Record<string, BtcBacktestResponse>>(BACKTEST_KEY);
  return map?.[key] ?? null;
}

export function setCachedBacktest(key: string, data: BtcBacktestResponse) {
  const map = read<Record<string, BtcBacktestResponse>>(BACKTEST_KEY) ?? {};
  map[key] = data;
  write(BACKTEST_KEY, map);
}

// ── summary cache (keyed by tf|mode|limit|feePct|slippagePts|version) ─────────

export function getCachedSummary(key: string): BtcSummaryResponse | null {
  const map = read<Record<string, BtcSummaryResponse>>(SUMMARY_KEY);
  return map?.[key] ?? null;
}

export function setCachedSummary(key: string, data: BtcSummaryResponse) {
  const map = read<Record<string, BtcSummaryResponse>>(SUMMARY_KEY) ?? {};
  map[key] = data;
  write(SUMMARY_KEY, map);
}

// ── clear all ───────────────────────────────────────────────────────────────

export function clearBtcCache() {
  try {
    sessionStorage.removeItem(CHART_KEY);
    sessionStorage.removeItem(STATUS_KEY);
    sessionStorage.removeItem(BACKTEST_KEY);
    sessionStorage.removeItem(SUMMARY_KEY);
  } catch {
    // ignore
  }
}
