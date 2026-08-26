// First-Swing Engine harness — replays EVERY day through the SAME live-safe
// state machine used by the chart, then scores against hand-marked GT.
import { readFileSync } from "fs";
import { FirstSwingEngine } from "./src/lib/flowline";

const lines = readFileSync("C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_5min.csv", "utf8").split("\n").slice(1);
const cs = lines.map((l) => l.split(",")).filter((p) => p.length >= 7).map((p) => ({
  date: p[0], ts: 0, open: +p[2], high: +p[3], low: +p[4], close: +p[5], volume: 0, oi: 0,
}));
const marksRaw: Record<string, { start: { time: string; kind: string; px: number }, end: { time: string; kind: string; px: number } }> =
  JSON.parse(readFileSync("C:/Users/Pravin/Desktop/main/AT_Trading/data/first_swing_manual.json", "utf8"));

const tm = (t: string) => +t.slice(0, 2) * 60 + +t.slice(3, 5);

interface GT { day: string; dir: "up" | "down"; sTime: string; eTime: string; ePx: number }
const gtDays: GT[] = [];
for (const [day, m] of Object.entries(marksRaw)) {
  const a = m.start, b = m.end;
  const rev = tm(b.time) < tm(a.time);
  const f = rev ? b : a, sec = rev ? a : b;
  gtDays.push({ day, dir: sec.px >= f.px ? "up" : "down", sTime: f.time, eTime: sec.time, ePx: sec.px });
}

const daysMap = new Map<string, typeof cs>();
for (const c of cs) {
  const d = c.date.slice(0, 10);
  if (!daysMap.has(d)) daysMap.set(d, []);
  daysMap.get(d)!.push(c);
}

function runDay(bars: typeof cs, mP: number, tB: boolean) {
  const eng = new FirstSwingEngine(mP, tB);
  for (const c of bars) eng.processBar(c, 0);
  return eng;
}

console.log(`=== SWEEP (GT=${gtDays.length} days) ===`);
console.log(`config        | match | avg-lag | med-lag`);
let bestCfg = { mP: 20, tB: true, match: -1 };
for (const mP of [15, 20, 25, 30]) {
  for (const tB of [true, false]) {
    let match = 0; const lags: number[] = [];
    for (const g of gtDays) {
      const bars = daysMap.get(g.day); if (!bars) continue;
      const eng = runDay(bars, mP, tB);
      if (!eng.declared || eng.dir !== g.dir) continue;
      const dt = Math.abs(tm(eng.endTime) - tm(g.eTime));
      const dp = Math.abs(eng.endPx - g.ePx);
      if (dt <= 5 && dp <= 8) {
        match++;
        // lag = bars between declared time and GT end time
        const iGt = bars.findIndex((c) => c.date.slice(11, 16) === g.eTime);
        const iDc = bars.findIndex((c) => c.date.slice(11, 16) === eng.declaredAtTime);
        if (iGt >= 0 && iDc >= 0) lags.push(iDc - iGt);
      }
    }
    const sorted = lags.slice().sort((a, b) => a - b);
    const avg = lags.length ? (lags.reduce((a, b) => a + b, 0) / lags.length).toFixed(1) : "-";
    const med = lags.length ? String(sorted[Math.floor(sorted.length / 2)]) : "-";
    console.log(`M=${String(mP).padStart(2)} TB=${tB ? "Y" : "N"}     | ${String(match).padStart(2)}/${gtDays.length}  | ${avg.padStart(5)}   | ${med}`);
    if (match > bestCfg.match) bestCfg = { mP, tB, match };
  }
}
console.log(`\nBEST: M=${bestCfg.mP} twoClose=${bestCfg.tB} -> ${bestCfg.match}/${gtDays.length}`);

// ===== per-day detail on best config =====
console.log(`\n=== DETAIL (best cfg): day | dir ok? | algoEnd vs gtEnd | lag-bars ===`);
for (const g of gtDays) {
  const bars = daysMap.get(g.day); if (!bars) continue;
  const eng = runDay(bars, bestCfg.mP, bestCfg.tB);
  const ok = eng.declared && eng.dir === g.dir && Math.abs(tm(eng.endTime) - tm(g.eTime)) <= 5 && Math.abs(eng.endPx - g.ePx) <= 8;
  const iGt = bars.findIndex((c) => c.date.slice(11, 16) === g.eTime);
  const iDc = eng.declared ? bars.findIndex((c) => c.date.slice(11, 16) === eng.declaredAtTime) : -1;
  const lag = ok && iGt >= 0 && iDc >= 0 ? `+${iDc - iGt}` : "-";
  const res = !eng.declared ? "NOT-DECLARED"
    : `${eng.dir}@${eng.endTime}(${eng.endPx.toFixed(1)})${ok ? " ✓" : " ✗"}`;
  console.log(`${g.day} ${g.dir.padEnd(4)} gt-end=${g.eTime} | ${res.padEnd(34)} | ${lag}`);
}

// ===== full-history sanity =====
let total = 0, declaredCount = 0; const declTimes: number[] = [];
for (const [day, bars] of daysMap) {
  if (bars.length < 20) continue;
  total++;
  const eng = runDay(bars, bestCfg.mP, bestCfg.tB);
  if (eng.declared) {
    declaredCount++;
    declTimes.push(tm(eng.declaredAtTime));
  }
}
declTimes.sort((a, b) => a - b);
console.log(`\n=== FULL HISTORY (${total} days, best cfg) ===`);
console.log(`declared: ${declaredCount}/${total}`);
console.log(`declare-time med: ${Math.floor(declTimes[Math.floor(declTimes.length / 2)] / 60)}:${String(declTimes[Math.floor(declTimes.length / 2)] % 60).padStart(2, "0")} · p90: ${Math.floor(declTimes[Math.floor(declTimes.length * 0.9)] / 60)}:${String(declTimes[Math.floor(declTimes.length * 0.9)] % 60).padStart(2, "0")}`);
