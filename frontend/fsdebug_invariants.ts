// Deep audit: verify chop breaks are correct for ALL declared days
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

interface Issue {
  day: string;
  type: string;
  detail: string;
}
const issues: Issue[] = [];

for (const [day, bars] of byDay) {
  const eng = new FirstSwingEngine({ timeCap: "09:29", sustainBars: 7 });
  // Collect all state snapshots
  for (let i = 0; i < bars.length; i++) {
    eng.processBar(bars[i], i);
    if (eng.declared) {
      const confTime = eng.confirmedAtTime;
      const confIdx = eng.confirmedAtIdx;
      const src = eng.confirmSource;
      // For chop: verify the conf bar broke the lastConfirmHit level
      if (src === "chop" && eng.lastConfirmHit) {
        const target = eng.lastConfirmHit;
        const confBar = bars[confIdx];
        const broke =
          eng.dir === "down"
            ? confBar.high > target.px
            : confBar.low < target.px;
        if (!broke) {
          issues.push({
            day,
            type: "CHOP_NO_BREAK",
            detail: `FS=chop at ${confTime} but conf-bar ${eng.dir === "down" ? "high" : "low"} (${eng.dir === "down" ? confBar.high : confBar.low}) does not break target ${target.time}@${target.px}`,
          });
        }
      }
      // For sustain: verify sustain logic
      if (src === "sustain") {
        const locked = (eng as any).lockedLevel;
        const confBar = bars[confIdx];
        const confClose = confBar.close;
        const validClose =
          eng.dir === "down" ? confClose > locked : confClose < locked;
        if (!validClose) {
          issues.push({
            day,
            type: "SUSTAIN_INVALID",
            detail: `FS=sustain at ${confTime} but conf close ${confClose} does not satisfy ${eng.dir} direction vs locked ${locked}`,
          });
        }
      }
      // FS after 9:29
      if (confTime < "09:29") {
        issues.push({
          day,
          type: "PRE_CAP_DECL",
          detail: `FS at ${confTime} < 9:29`,
        });
      }
      break;
    }
  }
}

if (issues.length === 0) {
  console.log("✓ All chop breaks and sustains verified on all declared days");
} else {
  console.log(`Found ${issues.length} issues:\n`);
  for (const iss of issues) {
    console.log(`  [${iss.type}] ${iss.day}: ${iss.detail}`);
  }
}
