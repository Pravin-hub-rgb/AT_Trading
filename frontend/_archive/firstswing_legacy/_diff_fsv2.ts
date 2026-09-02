// Compare per-day GT match between pre-fix (base) and post-fix (work) engines.
import { readFileSync } from "fs";

const baseMod = require("./_basecheck/firstswing");
const workMod = require("./src/lib/firstswing");

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
for (const c of cs) { const d = c.date.slice(0, 10); if (!daysMap.has(d)) daysMap.set(d, []); daysMap.get(d)!.push(c); }

function run(mod: any, bars: typeof cs) {
  const eng = new mod.FirstSwingEngine({ timeCap: "09:29", sustainBars: 7 });
  bars.forEach((c, i) => eng.processBar(c, i));
  return eng;
}
function ok(eng: any, g: GT) {
  if (!eng.declared || eng.dir !== g.dir) return false;
  return Math.abs(tm(eng.endTime) - tm(g.eTime)) <= 5 && Math.abs(eng.endPx - g.ePx) <= 8;
}
let moved = 0;
for (const g of gtDays) {
  const bars = daysMap.get(g.day); if (!bars || bars.length < 50) continue;
  const be = run(baseMod, bars), we = run(workMod, bars);
  const bOk = ok(be, g), wOk = ok(we, g);
  if (bOk !== wOk) {
    moved++;
    console.log(`${g.day} ${g.dir} gt=${g.eTime}(${g.ePx}) | BASE ${bOk ? "OK" : "miss"} end=${be.endTime}(${be.endPx.toFixed(1)}) conf=${be.confirmedAtTime} ${be.confirmSource} | WORK ${wOk ? "OK" : "miss"} end=${we.endTime}(${we.endPx.toFixed(1)}) conf=${we.confirmedAtTime} ${we.confirmSource}`);
  }
}
console.log(`days whose GT-match flipped: ${moved}`);