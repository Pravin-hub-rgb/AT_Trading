import { readFileSync } from "fs";
import { computeAlgoFlowLine, computeFlowLine } from "./src/lib/flowline";

const raw = readFileSync(
  "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_5min.csv",
  "utf8"
);
const cs = raw
  .split("\n")
  .slice(1)
  .map((l) => l.split(","))
  .filter((p) => p.length >= 7)
  .map((p) => ({
    date: p[0],
    open: +p[2],
    high: +p[3],
    low: +p[4],
    close: +p[5],
  }));

const day = cs.filter((c) => c.date.startsWith("2026-08-21"));
console.log("bars:", day.length);

try {
  const algo = computeAlgoFlowLine(day);
  console.log("ALGO segments:", algo.length);
  console.log("first 3:", JSON.stringify(algo.slice(0, 3)));
} catch (e) {
  console.error("ALGO CRASH:", e);
}

try {
  const manual = computeFlowLine(day);
  console.log("MANUAL segments:", manual.length);
} catch (e) {
  console.error("MANUAL CRASH:", e);
}
