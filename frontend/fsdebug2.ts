// FS trace harness — bar-by-bar engine state for one day (default 09:29 cap).
// Usage: bun fsdebug2.ts [YYYY-MM-DD] [--nocap]
import { readFileSync } from "fs";
import { FirstSwingEngine } from "./src/lib/firstswing";

const noCap = process.argv.includes("--nocap");
const day = process.argv[2] ?? "2026-08-28";
const lines = readFileSync("C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv", "utf8").split("\n").slice(1);
const bars = lines.map((l) => l.split(",")).filter((p) => p.length >= 7 && p[0].startsWith(day)).map((p) => ({
  date: p[0], ts: 0, open: +p[2], high: +p[3], low: +p[4], close: +p[5], volume: 0, oi: 0,
}));

const eng = new FirstSwingEngine({ timeCap: noCap ? "00:00" : "09:29", sustainBars: 7 });
const e = eng as any;

let prevSig = "";
for (let i = 0; i < Math.min(bars.length, 240); i++) {
  const c = bars[i];
  const t = c.date.slice(11, 16);
  const eHiPv = e.eHiPrev ? e.eHiPrev.px : NaN;
  const eLoPv = e.eLoPrev ? e.eLoPrev.px : NaN;
  const upBreak = c.high > eHiPv;
  const downBreak = c.low < eLoPv;
  eng.processBar(c, i);
  const sig = `${eng.dir}|${e.state}|${e.sameSideBreaks}|${e.dirConfirmed}|${eng.candTime}`;
  if (sig !== prevSig || upBreak || downBreak || eng.declared) {
    console.log(
      t,
      String(c.close).padStart(9),
      e.armed ? "armed" : "ARMING",
      upBreak ? "UP-BRK" : "      ",
      downBreak ? "DN-BRK" : "",
      `| dir=${eng.dir} ${e.state} ssb=${e.sameSideBreaks} dirConf=${e.dirConfirmed}`,
      `pend=${e.pendingConfirm ? e.pendingConfirm.src + "@" + e.pendingConfirm.time : "-"}`,
      `start=${eng.startTime}@${eng.startPx} cand=${eng.candTime}@${eng.candPx}`,
    );
  }
  prevSig = sig;
  if (eng.declared) {
    console.log(`>> DECLARED end=${eng.endTime}@${eng.endPx} confirmedAt=${eng.confirmedAtTime} src=${eng.confirmSource}`);
    console.log("MARKS", JSON.stringify((e as any).breakMarks ?? []));
    break;
  }
}
console.log("POOLS", JSON.stringify(e.debugPools?.()));
