// Does the WalkerEngine ever seal a pivot whose CANDLE is the current bar?
// If yes, intraday.py's detect_pivot_break (cur.high > normal_highs[-1].px)
// can self-block exactly like the FirstSwingEngine chop bug did.
import { readFileSync } from "node:fs";
import { WalkerEngine, type FlowCandle } from "./src/lib/flowline";

const csv = readFileSync("../data/nifty_1min.csv", "utf-8").trim().split(/\r?\n/);
type Bar = { date: string; o: number; h: number; l: number; c: number };
const bars: Bar[] = [];
for (let i = 1; i < csv.length; i++) {
  const f = csv[i].split(",");
  if (f.length < 5) continue;
  bars.push({ date: f[0], o: +f[1], h: +f[2], l: +f[3], c: +f[4] });
}
const byDay = new Map<string, Bar[]>();
for (const b of bars) {
  const d = b.date.slice(0, 10);
  if (!byDay.has(d)) byDay.set(d, []);
  byDay.get(d)!.push(b);
}

let sameCandleSeals = 0;
const examples: string[] = [];
// self-block shape: pivot appended THIS bar whose px == cur.high while the
// PREVIOUS pool top was strictly below cur.high (a real break got masked)
let maskedBreaks = 0;
const maskedEx: string[] = [];

for (const [day, dbars] of byDay) {
  const w = new WalkerEngine();
  let prevHighTop: number | null = null;
  dbars.forEach((b, i) => {
    const fc: FlowCandle = { date: b.date, open: b.o, high: b.h, low: b.l, close: b.c };
    const emitted = w.processBar(fc, i);
    for (const p of emitted) {
      if (p.idx === i) {
        sameCandleSeals++;
        if (examples.length < 10) examples.push(`${day} ${b.date.slice(11,16)} sealed pivot idx==bar (${p.kind} ${p.px})`);
      }
    }
    // detect_pivot_break shape (long side): after appending this bar's seals
    const highs = emitted.filter((p) => p.kind === "H");
    if (highs.length && prevHighTop !== null) {
      const top = highs[highs.length - 1].px;
      if (b.h > prevHighTop && b.h <= top && top === b.h) {
        maskedBreaks++;
        if (maskedEx.length < 10) maskedEx.push(`${day} ${b.date.slice(11,16)} cur.high ${b.h} broke prev top ${prevHighTop} but new top == cur.high -> no break`);
      }
    }
    // update prevHighTop to the pool top AFTER this bar (approximate: track last emitted H or previous)
    if (highs.length) prevHighTop = highs[highs.length - 1].px;
  });
}

console.log(`days=${byDay.size}`);
console.log(`same-candle-sealed pivots (p.idx == current bar): ${sameCandleSeals}`);
examples.forEach((e) => console.log("  " + e));
console.log(`detect_pivot_break self-block occurrences: ${maskedBreaks}`);
maskedEx.forEach((e) => console.log("  " + e));
