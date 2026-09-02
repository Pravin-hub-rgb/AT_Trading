// Trace pool additions for 21 July to see when 10:26 gets added
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

for (let i = 0; i < bars.length; i++) {
  const c = bars[i];
  const prevHighs = [...(eng as any).normalHighs];
  eng.processBar(c, i);
  const t = c.date.slice(11, 16);
  if (t >= "10:20" && t <= "10:35") {
    const currHighs = (eng as any).normalHighs;
    const added = currHighs.filter(
      (l: any) =>
        !prevHighs.some((p: any) => p.time === l.time && p.px === l.px),
    );
    const prevPivot =
      currHighs.length >= 2
        ? currHighs[currHighs.length - 2]
        : currHighs.length === 1
          ? currHighs[0]
          : null;
    const latestPivot =
      currHighs.length >= 1 ? currHighs[currHighs.length - 1] : null;
    console.log(
      `${t} h=${c.high} pool=${currHighs.map((l: any) => l.time.slice(-5)).join(",")} ` +
        `prev=${prevPivot ? prevPivot.time.slice(-5) + "@" + prevPivot.px : "null"} ` +
        `latest=${latestPivot ? latestPivot.time.slice(-5) + "@" + latestPivot.px : "null"} ` +
        `break-prev=${prevPivot ? c.high > prevPivot.px : false} ` +
        `${added.length ? " <<< NEW: " + added.map((l: any) => l.time.slice(-5) + "@" + l.px).join(",") : ""}` +
        `${(eng as any).declared ? " DECLARED at " + (eng as any).confirmedAtTime : ""}`,
    );
  }
  if ((eng as any).declared) break;
}
