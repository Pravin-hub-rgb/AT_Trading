import { readFileSync } from "fs";
import { WalkerEngine } from "./frontend/src/lib/flowline";

const lines = readFileSync("data/nifty_1min.csv", "utf8").split("\n").slice(1);
const candles = lines
  .map((l) => l.split(","))
  .filter((p) => p.length >= 7 && p[0].startsWith("2026-08-28"))
  .map((p) => ({
    date: p[0],
    open: +p[2],
    high: +p[3],
    low: +p[4],
    close: +p[5],
  }));

// Detailed walker trace for bars 0-15
const walker = new WalkerEngine();
for (let i = 0; i < 16; i++) {
  const c = candles[i];
  const t = c.date.slice(11, 16);
  const green = c.close >= c.open;
  
  // Access internal state by calling processBar and inspecting before/after
  // We need to use type assertions or a hack
  const sealed = walker.processBar(c, i);
  
  console.log(
    `${t} idx=${i} O=${c.open.toFixed(2)} H=${c.high.toFixed(2)} L=${c.low.toFixed(2)} C=${c.close.toFixed(2)} ` +
    `${green ? "GREEN" : "RED"} sealed=[${sealed.map(p => p.kind+p.px.toFixed(2)+"@"+p.time).join(", ")}]`
  );
}
