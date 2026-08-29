// FsV2Engine driver — reads nifty_1min.csv, runs frontend engine on one day,
// dumps per-bar state to JSON for Python diff.
//
// Usage: bun debug/_fsv2_drive.ts YYYY-MM-DD > out.json
//
// Output: { day, candles: [{i, t, o, h, l, c, state}], summary }

import { FsV2Engine, type FlowCandle } from "../frontend/src/lib/flowline";
import * as fs from "fs";
import * as path from "path";

const csvPath = path.join(__dirname, "..", "data", "nifty_1min.csv");
const targetDay = process.argv[2];
if (!targetDay) {
  console.error("Usage: bun _fsv2_drive.ts YYYY-MM-DD");
  process.exit(1);
}

const text = fs.readFileSync(csvPath, "utf8");
const lines = text.split("\n");
const header = lines[0].split(",");
const dayIdx = header.indexOf("timestamp");

const dayCandles: { i: number; candle: FlowCandle }[] = [];
let dayStart = -1;
for (let li = 1; li < lines.length; li++) {
  const line = lines[li].trim();
  if (!line) continue;
  const cols = line.split(",");
  const ts = cols[dayIdx];
  if (!ts || !ts.startsWith(targetDay)) continue;
  if (dayStart < 0) dayStart = dayCandles.length;
  const candle: FlowCandle = {
    date: ts.replace(" ", "T"),
    open: parseFloat(cols[header.indexOf("open")]),
    high: parseFloat(cols[header.indexOf("high")]),
    low: parseFloat(cols[header.indexOf("low")]),
    close: parseFloat(cols[header.indexOf("close")]),
  };
  dayCandles.push({ i: dayCandles.length, candle });
}

if (dayCandles.length === 0) {
  console.error(`No candles for ${targetDay}`);
  process.exit(2);
}

const eng = new FsV2Engine();
const states: any[] = [];
for (const { i, candle } of dayCandles) {
  eng.processBar(candle, i);
  states.push({
    i,
    t: candle.date.slice(11, 16),
    o: candle.open,
    h: candle.high,
    l: candle.low,
    c: candle.close,
    g: candle.close >= candle.open,
    barsSeen: eng.barsSeen,
    eHi: { px: eng.eHi.px, idx: eng.eHi.idx, t: eng.eHi.time },
    eLo: { px: eng.eLo.px, idx: eng.eLo.idx, t: eng.eLo.time },
    eHiPivot: eng.eHiPivot
      ? { px: eng.eHiPivot.px, idx: eng.eHiPivot.idx, t: eng.eHiPivot.time }
      : null,
    eLoPivot: eng.eLoPivot
      ? { px: eng.eLoPivot.px, idx: eng.eLoPivot.idx, t: eng.eLoPivot.time }
      : null,
    normalHighs: eng.normalHighs.map((l: any) => ({
      px: l.px,
      idx: l.idx,
      t: l.time,
    })),
    normalLows: eng.normalLows.map((l: any) => ({
      px: l.px,
      idx: l.idx,
      t: l.time,
    })),
    microHighs: eng.microHighs.map((l: any) => ({
      px: l.px,
      idx: l.idx,
      t: l.time,
    })),
    microLows: eng.microLows.map((l: any) => ({
      px: l.px,
      idx: l.idx,
      t: l.time,
    })),
    dir: eng.dir,
    baseDir: (eng as any).baseDir,
    sameSideBreaks: (eng as any).sameSideBreaks,
    oppositeSideBreaks: (eng as any).oppositeSideBreaks,
    dirConfirmed: eng.dirConfirmed,
    dirConfirmedIdx: eng.dirConfirmedIdx,
    locked: eng.locked,
    lockedLevelPx: eng.lockedLevelPx,
    startIdx: eng.startIdx,
    startPx: eng.startPx,
    candIdx: eng.candIdx,
    candPx: eng.candPx,
    sustainStreak: eng.sustainStreak,
    declared: eng.declared,
    tier: eng.tier,
    endIdx: eng.endIdx,
    endPx: eng.endPx,
    confirmedAtIdx: eng.confirmedAtIdx,
    confirmSource: eng.confirmSource,
    lastConfirmHit: eng.lastConfirmHit,
  });
}

const out = {
  day: targetDay,
  totalBars: dayCandles.length,
  final: {
    declared: eng.declared,
    dir: eng.dir,
    tier: eng.tier,
    startIdx: eng.startIdx,
    startPx: eng.startPx,
    endIdx: eng.endIdx,
    endPx: eng.endPx,
    confirmedAtIdx: eng.confirmedAtIdx,
    confirmSource: eng.confirmSource,
    lastConfirmHit: eng.lastConfirmHit,
  },
  states,
};
process.stdout.write(JSON.stringify(out));
