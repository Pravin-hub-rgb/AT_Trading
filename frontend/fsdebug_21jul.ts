// FS trace: 21 July — why does FS confirm at 10:31 instead of 10:29?
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

// Patch checkChop to log evaluations
const origCheck = (eng as any).checkChop.bind(eng);
(eng as any).checkChop = function () {
  const t0 = this.t;
  if (t0 < "10:20" || t0 > "10:32") {
    return origCheck();
  }
  const dir = this.dir;
  const pool = dir === "down" ? this.normalHighs : this.normalLows;
  const len = pool.length;
  const prev = len >= 2 ? pool[len - 2] : len === 1 ? pool[0] : null;
  const latest = len >= 1 ? pool[len - 1] : null;
  const px = dir === "down" ? this.hi : this.lo;
  const tgtPx = prev ? prev.px : null;
  const broken =
    prev && ((dir === "down" && px > tgtPx) || (dir === "up" && px < tgtPx));
  console.log(
    `  [chop-eval] t=${t0} dir=${dir} hi=${this.hi} lo=${this.lo} ` +
      `prev=${prev ? prev.time + "@" + prev.px : "null"} ` +
      `latest=${latest ? latest.time + "@" + latest.px : "null"} ` +
      `${broken ? " <<BROKEN>>" : ""}`,
  );
  return origCheck();
};

for (let i = 0; i < bars.length; i++) {
  const c = bars[i];
  if (c.date.slice(11, 16) >= "10:20" && c.date.slice(11, 16) <= "10:35") {
    console.log(
      `-> bar ${c.date.slice(11, 16)} o=${c.open} h=${c.high} l=${c.low} c=${c.close}`,
    );
  }
  eng.processBar(c, i);
  if (c.date.slice(11, 16) >= "10:20" && c.date.slice(11, 16) <= "10:35") {
    console.log(
      `   state: dir=${(eng as any).dir} cand=${(eng as any).candTime} declared=${(eng as any).declared}`,
    );
  }
  if ((eng as any).declared) {
    console.log(
      `>> DECLARED end=${(eng as any).endTime}@${(eng as any).endPx} conf=${(eng as any).confirmedAtTime} src=${(eng as any).confirmSource}`,
    );
    break;
  }
}

console.log(
  "\nPIVOTS high (last 8):",
  (eng as any).normalHighs.slice(-8).map((l: any) => l.time + "@" + l.px),
);
console.log(
  "PIVOTS low  (last 8):",
  (eng as any).normalLows.slice(-8).map((l: any) => l.time + "@" + l.px),
);
