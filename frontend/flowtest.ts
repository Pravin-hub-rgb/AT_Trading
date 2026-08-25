import { readFileSync } from "fs";
import { computeFlowLine } from "./src/lib/flowline";

const raw = readFileSync(
  "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_5min.csv",
  "utf8",
);
const lines = raw.split("\n").slice(1);
const candles = lines
  .map((l) => l.split(","))
  .filter((p) => p.length >= 7)
  .map((p) => ({
    date: p[0],
    timestamp: p[0],
    open: parseFloat(p[2]),
    high: parseFloat(p[3]),
    low: parseFloat(p[4]),
    close: parseFloat(p[5]),
  }));

for (const d of ["2026-08-21"]) {
  const day = candles.filter((c) => c.date.slice(0, 10) === d);
  const segs = computeFlowLine(day);

  // point chain derive
  type P = { px: number; time: string; dir: string };
  const chain: P[] = [];
  segs.forEach((s, i) => {
    if (i === 0) {
      chain.push({
        px: s.startPx,
        time: day[Math.min(s.startIdx, day.length - 1)]?.timestamp.slice(11, 16) ?? "?",
        dir: "?",
      });
    }
    chain.push({
      px: s.endPx,
      time: day[Math.min(s.endIdx, day.length - 1)]?.timestamp.slice(11, 16) ?? "?",
      dir: s.dir === "B" ? "↑" : "↓",
    });
  });

  console.log(`\n=== ${d} : ${segs.length} segments, ${chain.length} points ===`);
  console.log(
    chain
      .slice(0, 30)
      .map((p) => `${p.dir}${p.px.toFixed(1)}@${p.time}`)
      .join(" -> "),
  );
}
