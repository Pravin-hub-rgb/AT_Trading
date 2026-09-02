// FS trace: 21 July — using eHiPivotPrev / eLoPivotPrev for chop targets
import { readFileSync } from "fs";
import { FirstSwingEngine } from "./src/lib/firstswing";

const lines = readFileSync(
  "C:/Users/Pravin/Desktop/main/AT_Trading/data/nifty_1min.csv",
  "utf8",
)
  .split("\n")
  .slice(1);
const day = "2026-07-21";
const bars = lines
  .filter((l) => l.startsWith(day))
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

const eng = new FirstSwingEngine({ timeCap: "09:29", sustainBars: 7 });

// Log eHiPivotPrev / eLoPivotPrev at each bar
for (let i = 0; i < bars.length; i++) {
  const c = bars[i];
  eng.processBar(c, i);
  const t = c.date.slice(11, 16);
  if (t >= "10:20" && t <= "10:35") {
    const eHiPivotPrev = (eng as any).eHiPivotPrev;
    const eLoPivotPrev = (eng as any).eLoPivotPrev;
    const dir = (eng as any).dir;
    // What chop would target:
    // down: break above eHiPivotPrev
    // up: break below eLoPivotPrev
    const chopTarget =
      dir === "down"
        ? eHiPivotPrev
          ? eHiPivotPrev.px
          : null
        : eLoPivotPrev
          ? eLoPivotPrev.px
          : null;
    const wouldBreakDown =
      dir === "down" && chopTarget !== null && c.high > chopTarget;
    const wouldBreakUp =
      dir === "up" && chopTarget !== null && c.low < chopTarget;
    console.log(
      `${t} hi=${c.high} lo=${c.low} dir=${dir} ` +
        `eHiPrev=${eHiPivotPrev?.time}@${eHiPivotPrev?.px} ` +
        `eLoPrev=${eLoPivotPrev?.time}@${eLoPivotPrev?.px} ` +
        `chopTarget=${chopTarget} ` +
        `${wouldBreakDown ? "<<BROKEN-DOWN>>" : wouldBreakUp ? "<<BROKEN-UP>>" : ""}` +
        `${(eng as any).declared ? " DECLARED at " + (eng as any).confirmedAtTime : ""}`,
    );
  }
  if ((eng as any).declared) break;
}

console.log("\nPivot pools:");
console.log(
  "highs:",
  (eng as any).normalHighs.slice(-10).map((l: any) => l.time + "@" + l.px),
);
console.log(
  "lows:",
  (eng as any).normalLows.slice(-10).map((l: any) => l.time + "@" + l.px),
);
