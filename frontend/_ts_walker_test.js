// Test frontend walker on 29 May 2026 data - run with bun or node
import { WalkerEngine } from "./src/lib/flowline";
import fs from "fs";

const csv = fs.readFileSync("../data/nifty_5min.csv", "utf-8");
const lines = csv.split("\n").slice(1);
const rows = lines.map(line => {
  const [ts, open, high, low, close] = line.split(",");
  const d = new Date(ts);
  return {date: ts, open: +open, high: +high, low: +low, close: +close};
});

const may29 = rows.filter(r => r.date.startsWith("2026-05-29"));

console.log(`Loaded ${may29.length} candles for 2026-05-29`);

const eng = new WalkerEngine();
const normal_lows = [];
const normal_highs = [];

for (let i = 0; i < may29.length; i++) {
  const c = may29[i];
  const newPivots = eng.processBar(c, i);
  for (const p of newPivots) {
    if (p.kind === "L") normal_lows.push(p);
    else normal_highs.push(p);
  }
}

console.log("\n=== FRONTEND LOW pivots on 2026-05-29 ===");
normal_lows.forEach(p => {
  const t = may29[p.idx]?.date.substring(11,16) || "?";
  console.log(`  pivot.idx=${p.idx} sealTime=${p.time} srcTime=${t} L=${p.px} sealed=${p.sealed}`);
});
console.log(`\nTotal: ${normal_lows.length} L pivots, ${normal_highs.length} H pivots`);

// What's normal_lows[-1] at the time of bar 6 (09:45)?
console.log("\n=== State at each bar (after processBar) ===");
const eng2 = new WalkerEngine();
const state = [];
for (let i = 0; i < 11; i++) {
  eng2.processBar(may29[i], i);
  // can't access internal state, just log
  const t = may29[i].date.substring(11,16);
  console.log(`  bar=${i} ${t}`);
}
