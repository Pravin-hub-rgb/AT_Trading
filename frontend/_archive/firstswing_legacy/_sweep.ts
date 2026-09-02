// Full-day sweep driver — runs the FIRST-SWING engine (working tree) over every day.
import { readFileSync } from "fs";
import { computeFsV2Results } from "./src/lib/firstswing";

const CSV = "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv";
const lines = readFileSync(CSV, "utf8").split("\n").slice(1);
const candles = lines
  .filter((l) => l.trim())
  .map((l) => {
    const p = l.split(",");
    return { date: p[0], open: +p[2], high: +p[3], low: +p[4], close: +p[5] };
  });

const res = computeFsV2Results(candles, { timeCap: "09:29" });
let n = 0;
for (const r of res) {
  if (!r.seg) continue;
  n++;
  const ct = r.confIdx >= 0 && candles[r.confIdx] ? candles[r.confIdx].date.slice(11, 16) : "-";
  const et = candles[r.seg.endIdx] ? candles[r.seg.endIdx].date.slice(11, 16) : "-";
  const startT = candles[r.seg.startIdx] ? candles[r.seg.startIdx].date.slice(11, 16) : "-";
  console.log(`${r.day}|${r.dir}|start=${startT}|end=${et}|fs=${ct}|${r.source}`);
}
console.error(`TOTAL ${n}`);