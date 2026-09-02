// Inspect FLIP-based days — verify they're reversals (FLIP marks)
import { readFileSync } from "fs";
import { FirstSwingEngine } from "./src/lib/firstswing";

const lines = readFileSync(
  "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv",
  "utf8",
)
  .split("\n")
  .slice(1);
const allBars = lines
  .map((l) => l.split(","))
  .filter((p) => p.length >= 7)
  .map((p) => ({
    date: p[0],
    ts: 0,
    open: +p[2],
    high: +p[3],
    low: +p[4],
    close: +p[5],
    volume: 0,
    oi: 0,
  }));

const byDay = new Map<string, typeof allBars>();
for (const b of allBars) {
  const d = b.date.slice(0, 10);
  if (!byDay.has(d)) byDay.set(d, []);
  byDay.get(d)!.push(b);
}

const testDays = ["2025-08-06", "2025-09-05", "2026-04-15", "2025-10-21"];

for (const day of testDays) {
  const bars = byDay.get(day)!;
  const eng = new FirstSwingEngine({ timeCap: "09:29", sustainBars: 7 });
  for (let i = 0; i < bars.length; i++) eng.processBar(bars[i], i);
  const marks = eng.breakMarks;
  console.log(`\n${day}:`);
  console.log(
    `  declared=${eng.declared} confTime=${eng.confirmedAtTime} src=${eng.confirmSource}`,
  );
  console.log(
    `  marks:`,
    marks.map((m) => `${m.kind}@${m.time}(${m.dir})`),
  );
}
