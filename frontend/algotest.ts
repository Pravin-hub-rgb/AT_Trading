import { readFileSync } from "fs";
import { computeAlgoPivots, AlgoPivot } from "./src/lib/flowline";

const lines = readFileSync(
  "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_5min.csv",
  "utf8"
).split("\n").slice(1);

const cs = lines
  .map((l) => l.split(","))
  .filter((p) => p.length >= 7)
  .map((p) => ({
    date: p[0],
    open: +p[2],
    high: +p[3],
    low: +p[4],
    close: +p[5],
  }));

// Ground truth per day (manual orange line): time, kind, price
// Optional from/to window: only that slice of the day is compared.
type DayGt = {
  gt: [string, "H" | "L", number][];
  from?: string;
  to?: string;
};

const GT_BY_DAY: Record<string, DayGt> = {
  // sweep-reversal volatile: insider -> volatile(double-break) -> insider
  "2026-08-19": {
    from: "09:50",
    to: "10:20",
    gt: [
      ["09:50", "H", 24108.45],
      ["10:00", "L", 24093.1],
      ["10:00", "H", 24107.8],
      ["10:20", "L", 24063.2],
    ],
  },
  "2026-08-20": {
    gt: [
      ["09:15", "H", 24225.45],
      ["09:20", "L", 24184.55],
      ["09:25", "H", 24201.6],
      ["09:30", "L", 24185.1],
      ["09:45", "H", 24215.05],
      ["09:50", "L", 24195.95],
      ["09:55", "H", 24214.25],
      ["10:00", "L", 24199.7],
      ["10:15", "H", 24226.85],
      ["10:25", "L", 24207.25],
      ["10:30", "H", 24215.35],
      ["10:35", "L", 24201.25],
      ["10:45", "H", 24218.1],
      ["10:55", "L", 24203.9],
      ["11:00", "H", 24223.55],
      ["11:20", "L", 24194.2],
      ["11:30", "H", 24217.4],
      ["11:40", "L", 24209.0],
      ["11:45", "H", 24218.85],
      ["11:55", "L", 24209.95],
      ["11:55", "H", 24220.5],
      ["12:05", "L", 24210.15],
      ["12:15", "H", 24223.0],
      ["12:25", "L", 24208.15],
      ["12:30", "H", 24215.25],
      ["12:35", "L", 24207.4],
      ["12:50", "H", 24265.15],
      ["12:55", "L", 24235.55],
      ["13:00", "H", 24250.6],
      ["13:05", "L", 24243.8],
      ["13:10", "H", 24251.7],
      ["13:15", "L", 24237.15],
    ],
  },
  "2026-08-21": {
    gt: [
      ["09:15", "H", 24284.05],
      ["09:20", "L", 24210.8],
      ["09:25", "H", 24236.2],
      ["09:30", "L", 24206.8],
      ["09:50", "H", 24256.4],
      ["09:55", "L", 24240.0],
      ["10:00", "H", 24253.65],
      ["10:10", "L", 24224.6],
      ["10:15", "H", 24237.9],
      ["10:20", "L", 24229.35],
      ["10:30", "H", 24258.85],
      ["10:35", "L", 24245.4],
      ["10:55", "H", 24267.65],
      ["10:55", "L", 24251.05],
      ["11:05", "H", 24267.3],
      ["11:10", "L", 24257.85],
      ["11:15", "H", 24265.85],
      ["11:20", "L", 24248.15],
      ["11:30", "H", 24261.75],
      ["11:45", "L", 24247.75],
      ["11:50", "H", 24259.7],
      ["12:15", "L", 24227.5],
      ["12:20", "H", 24243.35],
      ["12:25", "L", 24234.9],
      ["12:35", "H", 24246.7],
      ["12:40", "L", 24227.45],
      ["12:45", "H", 24239.4],
      ["12:55", "L", 24229.55],
      ["13:05", "H", 24253.1],
      ["13:20", "L", 24234.9],
      ["13:30", "H", 24250.35],
    ],
  },
  // stacked-insider (onion) window — full day not yet hand-marked
  "2026-08-24": {
    from: "09:30",
    to: "10:20",
    gt: [
      ["09:30", "L", 24272.55],
      ["09:35", "H", 24288.6],
      ["09:40", "L", 24274.25],
      ["09:45", "H", 24285.15],
      ["09:55", "L", 24267.3],
      ["10:00", "H", 24276.55],
      ["10:05", "L", 24267.7],
      ["10:20", "H", 24284.25],
    ],
  },
};

let totalOk = 0;
let totalGt = 0;
let dayFail = false;

for (const [day, { gt, from, to }] of Object.entries(GT_BY_DAY)) {
  const candles = cs.filter((c) => c.date.startsWith(day));
  const algo: AlgoPivot[] = computeAlgoPivots(candles);
  let sealed = algo.filter((p) => p.sealed);
  if (from) sealed = sealed.filter((p) => p.time >= from);
  if (to) sealed = sealed.filter((p) => p.time <= to);

  console.log(`\n=== ${day}${from ? ` [${from}..${to}]` : ""}: bars ${candles.length}, GT ${gt.length}, algo ${sealed.length} ===`);

  let ok = 0;
  for (let i = 0; i < Math.max(gt.length, sealed.length); i++) {
    const g = gt[i];
    const a = sealed[i];
    const match =
      g && a && g[0] === a.time && g[1] === a.kind && Math.abs(g[2] - a.px) < 1e-6;
    if (!match && i >= gt.length) break; // trailing extras past GT end: info only
    if (match) ok++;
    else dayFail = true;
    const gs = g ? `${g[0]} ${g[1]} ${g[2].toFixed(2)}` : "-- missing --";
    const as = a ? `${a.time} ${a.kind} ${a.px.toFixed(2)}` : "-- extra --";
    console.log(`${String(i + 1).padStart(2)}  ${match ? "OK " : "XX "}  GT ${gs.padEnd(22)} | ALGO ${as}`);
  }
  console.log(`--- ${day}: MATCH ${ok}/${gt.length} ---`);
  totalOk += ok;
  totalGt += gt.length;
}

console.log(`\n=== TOTAL: ${totalOk}/${totalGt} ===`);

// ===== ENVELOPE LAW (hard, all days) =====
// Between consecutive markers, no candle may exceed the marked extreme:
// after an L until the next H, every candle high <= H.px; symmetric for lows.
// Same-candle pairs (idx equal) are exempt — volatile bars may print both.
const allDays = Array.from(new Set(cs.map((c) => c.date.slice(0, 10))));
let envMarked = 0;
let envOther = 0;
for (const day of allDays) {
  const candles = cs.filter((c) => c.date.startsWith(day));
  const pivots = computeAlgoPivots(candles);
  for (let i = 0; i + 1 < pivots.length; i++) {
    const a = pivots[i];
    const b = pivots[i + 1];
    if (a.idx === b.idx || a.kind === b.kind) continue;
    // Atomic-candle principle: the marker bar is ONE swing unit — its
    // counter-wick belongs to the prior leg. Only candles STRICTLY AFTER
    // the marker bar must respect the new extreme.
    for (let j = a.idx + 1; j <= Math.max(a.idx, b.idx); j++) {
      const cd = candles[j];
      if (b.kind === "H" && cd.high > b.px + 1e-6) {
        console.log(`ENVELOPE ${day}: ${cd.date.slice(11, 16)} high ${cd.high.toFixed(2)} > H ${b.px.toFixed(2)}@${b.time}`);
        if (GT_BY_DAY[day]) envMarked++;
        else envOther++;
        break;
      }
      if (b.kind === "L" && cd.low < b.px - 1e-6) {
        console.log(`ENVELOPE ${day}: ${cd.date.slice(11, 16)} low ${cd.low.toFixed(2)} < L ${b.px.toFixed(2)}@${b.time}`);
        if (GT_BY_DAY[day]) envMarked++;
        else envOther++;
        break;
      }
    }
  }
}
console.log(`=== ENVELOPE: ${envMarked} violations on marked days, ${envOther} on unlabeled days ===`);

// hard-fail: GT mismatches always; envelope breaches only on hand-marked days
if (dayFail || totalOk !== totalGt || envMarked > 0) process.exit(1);
