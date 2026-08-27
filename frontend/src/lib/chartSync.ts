import type { Candle } from "@/lib/api";

// Normalize a candle to UTC epoch seconds.
// Intraday candles carry a numeric `ts`; daily candles use "YYYY-MM-DD HH:MM" strings
// where the date part anchors the business day (UTC midnight, matching timeToSec
// in StockChart).
export function candleSec(c: Candle, intraday: boolean): number {
  if (intraday) return c.ts;
  return Date.parse(`${c.date.slice(0, 10)}T00:00:00Z`) / 1000;
}

// Sorted-ascending array of epoch seconds — input candles are already ordered.
export function buildTimes(candles: Candle[], intraday: boolean): number[] {
  const out: number[] = new Array(candles.length);
  for (let i = 0; i < candles.length; i++) out[i] = candleSec(candles[i], intraday);
  return out;
}

// Binary search: closest epoch sec in a sorted array (ties pick the earlier bar).
export function nearestSec(times: number[], sec: number): number | null {
  if (times.length === 0) return null;
  if (sec <= times[0]) return times[0];
  if (sec >= times[times.length - 1]) return times[times.length - 1];
  let lo = 0;
  let hi = times.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const v = times[mid];
    if (v === sec) return v;
    if (v < sec) lo = mid + 1;
    else hi = mid - 1;
  }
  const before = times[hi];
  const after = times[lo];
  return Math.abs(before - sec) <= Math.abs(after - sec) ? before : after;
}
