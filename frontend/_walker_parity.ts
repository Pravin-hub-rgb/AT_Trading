// Walker parity test: run the TS WalkerEngine over nifty_1min.csv per day,
// emit every sealed pivot from processBar (exactly what FirstSwingEngine consumes).
// Output lines: date|gIdx|kind|px|time  — compared 1:1 against walker.py output.
import { readFileSync } from "fs";
import { WalkerEngine, FlowCandle } from "./src/lib/flowline";

const lines = readFileSync("../data/nifty_1min.csv", "utf8").trim().split(/\r?\n/).slice(1);
const byDay = new Map<string, FlowCandle[]>();
for (const line of lines) {
  const parts = line.split(",");
  if (parts.length < 6) continue;
  const ts = parts[0];
  const d = ts.slice(0, 10);
  if (!byDay.has(d)) byDay.set(d, []);
  byDay.get(d)!.push({
    date: ts.replace(" ", "T"),
    open: parseFloat(parts[2]),
    high: parseFloat(parts[3]),
    low: parseFloat(parts[4]),
    close: parseFloat(parts[5]),
  });
}
const out: string[] = [];
for (const [d, bars] of byDay) {
  const eng = new WalkerEngine();
  bars.forEach((c, gIdx) => {
    for (const p of eng.processBar(c, gIdx)) {
      if (!p.sealed) continue;
      out.push(`${d}|${gIdx}|${p.kind}|${p.px.toFixed(2)}|${p.time}`);
    }
  });
}
console.log(out.join("\n"));