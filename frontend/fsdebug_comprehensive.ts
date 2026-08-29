// Comprehensive audit across all days — check invariants
import { readFileSync } from "fs";
import { FirstSwingEngine, computeFsV2Results } from "./src/lib/firstswing";

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

// Group by day
const byDay = new Map<string, typeof allBars>();
for (const b of allBars) {
  const d = b.date.slice(0, 10);
  if (!byDay.has(d)) byDay.set(d, []);
  byDay.get(d)!.push(b);
}

const days = [...byDay.keys()].sort();
console.log(`Auditing ${days.length} days...\n`);

interface Issue {
  day: string;
  type: string;
  detail: string;
}
const issues: Issue[] = [];

for (const day of days) {
  const bars = byDay.get(day)!;
  const eng = new FirstSwingEngine({ timeCap: "09:29", sustainBars: 7 });
  for (let i = 0; i < bars.length; i++) {
    const c = bars[i];
    eng.processBar(c, i);
    if (eng.declared) {
      // INVARIANT 1: declared after 9:29
      if (eng.confirmedAtTime < "09:29") {
        issues.push({
          day,
          type: "PRE_CAP_DECL",
          detail: `FS declared at ${eng.confirmedAtTime} < 9:29`,
        });
      }
      // INVARIANT 2: B2 and FS on different bars
      const b2Marks = (eng.breakMarks || []).filter((m) => m.kind === "B2");
      for (const b2 of b2Marks) {
        if (b2.idx === eng.confirmedAtIdx) {
          issues.push({
            day,
            type: "B2_SAME_BAR_FS",
            detail: `B2 at ${b2.time} (idx ${b2.idx}) and FS at ${eng.confirmedAtTime} (idx ${eng.confirmedAtIdx}) same bar`,
          });
        }
      }
      // INVARIANT 3: B2 mark exists
      if (b2Marks.length === 0) {
        issues.push({
          day,
          type: "NO_B2",
          detail: `FS declared but no B2 mark`,
        });
      }
      break;
    }
  }

  if (!eng.declared) {
    issues.push({ day, type: "NO_DECL", detail: `No FS declared for the day` });
  }
}

if (issues.length === 0) {
  console.log("✓ All invariants pass on all", days.length, "days");
} else {
  console.log(`Found ${issues.length} potential issues:\n`);
  for (const iss of issues) {
    console.log(`  [${iss.type}] ${iss.day}: ${iss.detail}`);
  }
}
