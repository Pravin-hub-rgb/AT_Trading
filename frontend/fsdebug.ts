// FS v3 trace: 24 Aug bar-by-bar state transitions
import { readFileSync } from "fs";
import { FsV2Engine } from "./src/lib/flowline";

const lines = readFileSync("C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv", "utf8").split("\n").slice(1);
const day = process.argv[2] ?? "2026-08-24";
const bars = lines.map((l) => l.split(",")).filter((p) => p.length >= 7 && p[0].startsWith(day)).map((p) => ({
  date: p[0], ts: 0, open: +p[2], high: +p[3], low: +p[4], close: +p[5], volume: 0, oi: 0,
}));

const eng = new FsV2Engine({ zonePct: 25, armRangePts: 80, armBars: 10 });
let prev = "";
for (let i = 0; i < Math.min(bars.length, 240); i++) {
  const c = bars[i];
  eng.processBar(c, i);
  const st = `${eng.dir ?? "-"}/s${eng.stage}${eng.locked ? "L" : ""}${eng.invalidated ? "X" : ""}${eng.declared ? "D" : ""} cand=${eng.candTime}`;
  if (st !== prev) {
    console.log(`${c.date.slice(11, 16)} ${String(c.close).padStart(9)} | ${st}`);
    prev = st;
  }
  if (eng.declared || eng.invalidated) {
    console.log(`>> ${eng.declared ? `DECLARED end=${eng.endTime}@${eng.endPx} conf=${eng.confirmedAtTime}` : "INVALIDATED"}`);
    break;
  }
}
