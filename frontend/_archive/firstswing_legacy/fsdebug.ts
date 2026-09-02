// FS v3 trace: 24 Aug bar-by-bar state transitions
import { readFileSync } from "fs";
import { FirstSwingEngine } from "./src/lib/firstswing";

const lines = readFileSync("C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv", "utf8").split("\n").slice(1);
const day = process.argv[2] ?? "2026-08-24";
const bars = lines.map((l) => l.split(",")).filter((p) => p.length >= 7 && p[0].startsWith(day)).map((p) => ({
  date: p[0], ts: 0, open: +p[2], high: +p[3], low: +p[4], close: +p[5], volume: 0, oi: 0,
}));

const eng = new FirstSwingEngine({ timeCap: "09:29", sustainBars: 7 });

let prev = "";
for (let i = 0; i < Math.min(bars.length, 240); i++) {
  const c = bars[i];
  eng.processBar(c, i);
  const st = `${eng.dir ?? "-"}${eng.locked ? "L" : ""}${eng.declared ? "D" : ""} dirConf=${(eng as any).dirConfirmed ?? "?"} cand=${eng.candTime} streak=${(eng as any).sustainStreak ?? "?"}`;
  if (st !== prev) {
    console.log(`${c.date.slice(11, 16)} ${String(c.close).padStart(9)} | ${st}`);
    prev = st;
  }
  if (eng.declared) {
    console.log(`>> DECLARED end=${eng.endTime}@${eng.endPx} conf=${eng.confirmedAtTime} src=${eng.confirmSource}`);
    break;
  }
}

console.log('POOLS', JSON.stringify((eng as any).debugPools?.()));
