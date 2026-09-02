// Deep per-bar trace of the first-swing engine for specific days.
// Usage: bun _bar_trace.ts <YYYY-MM-DD> [_basecheck]
//   - second arg "_basecheck" -> committed HEAD engine (pre-fix); default = working tree (post-fix)
import { readFileSync } from "fs";

const CSV = "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv";
const day = process.argv[2] ?? "2026-08-24";
const useBase = process.argv[3] === "_basecheck";
const engineMod = useBase ? require("./_basecheck/firstswing") : require("./src/lib/firstswing");
const Eng = engineMod.FirstSwingEngine;

const lines = readFileSync(CSV, "utf8").split("\n").slice(1);
const bars = lines
  .filter((l) => l.trim() && l.startsWith(day))
  .map((l) => {
    const p = l.split(",");
    return { date: p[0], open: +p[2], high: +p[3], low: +p[4], close: +p[5] };
  });

const eng = new Eng({ timeCap: "09:29" });
console.log(`=== ${useBase ? "PRE-FIX(base)" : "POST-FIX(worktree)"} ${day} ===`);
for (let i = 0; i < bars.length; i++) {
  eng.processBar(bars[i], i);
  if (eng.declared) {
    console.log(`DECLARED end=${eng.endTime}@${eng.endPx} conf=${eng.confirmedAtTime} src=${eng.confirmSource} hit=${JSON.stringify(eng.lastConfirmHit)}`);
    break;
  }
  if (!eng.locked) continue;
  const poold = (eng as any).debugPools?.();
  const hh = poold?.normalHighs ?? [];
  const lo = poold?.normalLows ?? [];
  console.log(
    `${bars[i].date.slice(11,16)} H${bars[i].high} L${bars[i].low} dir=${eng.dir} conf=${(eng as any).dirConfirmed} ` +
    `cand=${eng.candTime}@${eng.candPx} lastH=${hh.length?hh[hh.length-1]:''} lastL=${lo.length?lo[lo.length-1]:''} ` +
    `snap=${(eng as any).latestHighAtBarStart?JSON.stringify((eng as any).latestHighAtBarStart):'-'}/${(eng as any).latestLowAtBarStart?JSON.stringify((eng as any).latestLowAtBarStart):'-'}`
  );
}