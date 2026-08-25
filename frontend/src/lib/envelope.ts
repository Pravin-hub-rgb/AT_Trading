// Envelope Law validator — frontend port of the harness logic in
// algotest.ts. For every day, walk the algo pivot chain and flag candles
// that breach the marked extreme before the opposite kind prints:
//   after an L marker until the next H, no candle low < L.px
//   after an H marker until the next L, no candle high > H.px
// Same-candle pairs are exempt (volatile bars may print both sides).
// Atomic-candle principle: the marker bar itself is ONE swing unit — its
// counter-wick belongs to the prior leg — so checks start at a.idx + 1.

import { computeAlgoPivots, type AlgoPivot } from "./flowline";
import type { Candle } from "./api";

export interface EnvelopeViolation {
  idx: number; // global index of the violating candle
  side: "high" | "low"; // which side breached
  px: number; // breaching price (candle high/low)
  markerIdx: number; // global index of the violated marker's bar
  markerTime: string; // HH:MM (or date for daily) of the marker
  markerKind: "H" | "L";
  markerPx: number; // the marked extreme that was undercut/breached
  day: string; // YYYY-MM-DD
}

const EPS = 1e-6;

export function computeEnvelopeViolations(candles: Candle[]): EnvelopeViolation[] {
  if (candles.length === 0) return [];

  // per-day grouping — identical to how computeAlgoPivots walks days
  const byDay = new Map<string, { c: Candle; gIdx: number }[]>();
  candles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const out: EnvelopeViolation[] = [];
  byDay.forEach((items, dayKey) => {
    const pivots: AlgoPivot[] = computeAlgoPivots(items.map((it) => it.c));
    // computeAlgoPivots returns pivots with idx relative to... global indices
    // of the array it received — but we passed a per-day slice, so remap.
    // walkDay assigns items[i].gIdx from ITS input order, so pivot.idx is an
    // index into our sliced array. Map slice-index -> global via position:
    // items[k].gIdx is the global index of slice element k.

    for (let i = 0; i + 1 < pivots.length; i++) {
      const a = pivots[i];
      const b = pivots[i + 1];
      if (a.idx === b.idx || a.kind === b.kind) continue;

      for (let j = a.idx + 1; j <= Math.max(a.idx, b.idx); j++) {
        if (j >= items.length) break;
        const cd = items[j].c;
        if (b.kind === "H" && cd.high > b.px + EPS) {
          out.push({
            idx: items[j].gIdx,
            side: "high",
            px: cd.high,
            markerIdx: items[b.idx].gIdx,
            markerTime: b.time,
            markerKind: "H",
            markerPx: b.px,
            day: dayKey,
          });
          break;
        }
        if (b.kind === "L" && cd.low < b.px - EPS) {
          out.push({
            idx: items[j].gIdx,
            side: "low",
            px: cd.low,
            markerIdx: items[b.idx].gIdx,
            markerTime: b.time,
            markerKind: "L",
            markerPx: b.px,
            day: dayKey,
          });
          break;
        }
      }
    }
  });

  return out;
}
