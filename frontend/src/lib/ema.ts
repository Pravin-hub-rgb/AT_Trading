import type { Candle } from "./api";

export interface EmaPoint {
  idx: number;
  value: number;
}

export function computeEMA(candles: Candle[], period: number): EmaPoint[] {
  if (candles.length === 0 || period <= 1) return [];
  const k = 2 / (period + 1);
  const out: EmaPoint[] = [];
  let ema = candles[0].close;
  out.push({ idx: 0, value: ema });
  for (let i = 1; i < candles.length; i++) {
    ema = candles[i].close * k + ema * (1 - k);
    out.push({ idx: i, value: ema });
  }
  return out;
}

export function computeEMALines(
  candles: Candle[],
  periods: number[]
): Record<number, EmaPoint[]> {
  const map: Record<number, EmaPoint[]> = {};
  for (const p of periods) {
    map[p] = computeEMA(candles, p);
  }
  return map;
}
