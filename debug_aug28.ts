import { readFileSync } from "fs";
import { WalkerEngine } from "./frontend/src/lib/flowline";
import { FirstSwingEngine } from "./frontend/src/lib/firstswing";

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

console.log("=== AUG 28 1-MIN DATA (first 20 bars) ===");
candles.slice(0, 20).forEach((c, i) => {
  const green = c.close >= c.open;
  console.log(
    `${i.toString().padStart(2)} ${c.date.slice(11, 16)} O=${c.open.toFixed(2)} H=${c.high.toFixed(2)} L=${c.low.toFixed(2)} C=${c.close.toFixed(2)} ${green ? "GREEN" : "RED"}`
  );
});

console.log("\n=== WALKER ENGINE TRACE (pivots) ===");
const walker = new WalkerEngine();
const walkerPivots: any[] = [];
for (let i = 0; i < candles.length; i++) {
  const sealed = walker.processBar(candles[i], i);
  for (const p of sealed) {
    walkerPivots.push(p);
    console.log(`  bar ${i.toString().padStart(2)} (${candles[i].date.slice(11, 16)}) -> SEALED ${p.kind} ${p.px.toFixed(2)} @ ${p.time}`);
  }
}
const finalPivot = walker.finalize();
if (finalPivot) {
  walkerPivots.push(finalPivot);
  console.log(`  FINALIZE -> ${finalPivot.kind} ${finalPivot.px.toFixed(2)} @ ${finalPivot.time}`);
}

console.log("\n=== FIRST SWING ENGINE TRACE ===");
const engine = new FirstSwingEngine();
for (let i = 0; i < candles.length; i++) {
  engine.processBar(candles[i], i);
}
console.log("declared:", engine.declared);
if (engine.declared) {
  console.log("  dir:", engine.dir);
  console.log("  tier:", engine.tier);
  console.log("  start:", engine.startTime, engine.startPx);
  console.log("  end:", engine.endTime, engine.endPx);
  console.log("  source:", engine.confirmSource);
  console.log("  confirmedAt:", engine.confirmedAtTime);
}
console.log("debug:", engine.debugPools());
