// FS v2 harness — replay 1-min days through FsV2Engine, score vs hand GT.
import { readFileSync } from "fs";
import { FsV2Engine } from "./src/lib/flowline";

const lines = readFileSync("C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv", "utf8").split("\n").slice(1);
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

function runDay(bars: typeof cs, zonePct = 25, armRange = 80, armBarsN = 10, gap = 15, closeC = true) {
  const eng = new FsV2Engine({ zonePct, armRangePts: armRange, armBars: armBarsN, confirmGapPts: gap, closeConfirm: closeC });
  for (const c of bars) eng.processBar(c, 0);
  return eng;
}

console.log(`=== FS v2 SWEEP (GT=${gtDays.length} days, 1-min replay) ===`);
console.log(`zone% | match | med-lag | declare-med-time`);
let bestZ = 25, bestAR = 60, bestAB = 10, bestG = 0, bestCC = false, bestMatch = -1;
for (const [z, ar, ab, gp, cc] of [[25,80,10,0,false],[25,80,10,8,false],[25,80,10,8,true],[25,80,10,15,false],[25,80,10,15,true],[30,80,10,8,false],[30,80,10,8,true],[30,80,10,15,true],[35,100,10,8,false],[35,100,10,8,true]] as const) {
  let match = 0; const lags: number[] = []; const dtimes: number[] = [];
  for (const g of gtDays) {
    const bars = daysMap.get(g.day); if (!bars || bars.length < 50) continue;
    const eng = runDay(bars, z, ar, ab, gp, cc);
    if (eng.invalidated) continue;
    if (!eng.declared || eng.dir !== g.dir) continue;
    if (Math.abs(tm(eng.endTime) - tm(g.eTime)) <= 5 && Math.abs(eng.endPx - g.ePx) <= 8) {
      match++;
      const iGt = bars.findIndex((c) => c.date.slice(11, 16) === g.eTime);
      const iCf = bars.findIndex((c) => c.date.slice(11, 16) === eng.confirmedAtTime);
      if (iGt >= 0 && iCf >= 0) lags.push(iGt - iCf); // negative = confirm AFTER gt-end (normal)
      dtimes.push(tm(eng.confirmedAtTime));
    }
  }
  const sorted = lags.slice().sort((a, b) => a - b);
  const dts = dtimes.slice().sort((a, b) => a - b);
  const medLag = sorted.length ? String(sorted[Math.floor(sorted.length / 2)]) : "-";
  const medT = dts.length ? `${String(Math.floor(dts[Math.floor(dts.length / 2)] / 60)).padStart(2, "0")}:${String(dts[Math.floor(dts.length / 2)] % 60).padStart(2, "0")}` : "-";
  console.log(`${String(z).padStart(4)} | ${String(match).padStart(2)}/${gtDays.length} | ${medLag.padStart(4)} | ${medT}`);
  if (match > bestMatch) { bestMatch = match; bestZ = z; bestAR = ar; bestAB = ab; bestG = gp; bestCC = cc; }
}
console.log(`\nBEST ZONE=${bestZ}% -> ${bestMatch}/${gtDays.length}`);

// detail on best
console.log(`\n=== DETAIL (z=${bestZ}) ===`);
let dirWrong = 0, noDecl = 0, lateMiss = 0;
for (const g of gtDays) {
  const bars = daysMap.get(g.day); if (!bars || bars.length < 50) continue;
  const eng = runDay(bars, bestZ, bestAR, bestAB, bestG, bestCC);
  if (!eng.declared) { noDecl++; console.log(`${g.day} ${g.dir} gt=${g.eTime} | NOT-DECLARED`); continue; }
  const okDir = eng.dir === g.dir;
  if (!okDir) dirWrong++;
  const dt = Math.abs(tm(eng.endTime) - tm(g.eTime));
  const dp = Math.abs(eng.endPx - g.ePx);
  const ok = okDir && dt <= 5 && dp <= 8;
  if (okDir && !ok) lateMiss++;
  console.log(`${g.day} ${g.dir.padEnd(4)} gt=${g.eTime}(${g.ePx.toFixed(1)}) | ${eng.dir}@end=${eng.endTime}(${eng.endPx.toFixed(1)}) conf=${eng.confirmedAtTime}${eng.convertedByZone ? " [ZONE]" : ""} ${ok ? "✓" : "✗"}`);
}
console.log(`\nsummary: dirWrong=${dirWrong} notDeclared=${noDecl} dirOkButEndMissed=${lateMiss}`);

// full-history sanity at best Z
let total = 0, decl = 0; const times: number[] = [];
for (const [, bars] of daysMap) {
  if (bars.length < 100) continue;
  total++;
  const eng = runDay(bars, bestZ, bestAR, bestAB, bestG, bestCC);
  if (eng.declared) { decl++; times.push(tm(eng.confirmedAtTime)); }
}
times.sort((a, b) => a - b);
if (times.length) {
  const fmt = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  console.log(`\nFULL HISTORY: declared ${decl}/${total} · confirm-time med=${fmt(times[Math.floor(times.length / 2)])} p90=${fmt(times[Math.floor(times.length * 0.9)])}`);
}
