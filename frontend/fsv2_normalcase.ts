// Reproduce the "normal case" faithfully:
//   9:27 low breaks the low extreme once  (count 1 -> lock down)
//   9:35 breaks extreme low AGAIN         (count 2 -> direction CONFIRMED down)
//   9:35 ALSO pokes above the prev pivot high (wick > recent H pivot)
// Show HOW this normal case gets messed up. No edits to flowline.ts.
import { FirstSwingEngine } from "./src/lib/firstswing";

type C = { date: string; open: number; high: number; low: number; close: number };

// Flat-ish session: no new low until 9:27. Highs stay at 24305 (become
// "normalHigh" pivots, below the 24320 seed extreme). 9:27 = first low
// break. 9:35 = lower low (would be 2nd break) + high 24325 pokes the
// prev pivot high 24320 / recent 24305 normals.
const base: C[] = [
  { date: "2026-07-07 09:15", open: 24300, high: 24320, low: 24280, close: 24290 },
  { date: "2026-07-07 09:16", open: 24290, high: 24305, low: 24281, close: 24288 },
  { date: "2026-07-07 09:17", open: 24288, high: 24305, low: 24281, close: 24287 },
  { date: "2026-07-07 09:18", open: 24287, high: 24305, low: 24281, close: 24286 },
  { date: "2026-07-07 09:19", open: 24286, high: 24305, low: 24281, close: 24286 },
  { date: "2026-07-07 09:20", open: 24286, high: 24305, low: 24281, close: 24285 },
  { date: "2026-07-07 09:21", open: 24285, high: 24305, low: 24281, close: 24285 },
  { date: "2026-07-07 09:22", open: 24285, high: 24305, low: 24281, close: 24284 },
  { date: "2026-07-07 09:23", open: 24284, high: 24305, low: 24281, close: 24284 },
  { date: "2026-07-07 09:24", open: 24284, high: 24305, low: 24281, close: 24283 },
  { date: "2026-07-07 09:25", open: 24283, high: 24305, low: 24281, close: 24283 },
  { date: "2026-07-07 09:26", open: 24283, high: 24305, low: 24281, close: 24282 },
  { date: "2026-07-07 09:27", open: 24282, high: 24305, low: 24260, close: 24264 }, // FIRST break (count 1)
  { date: "2026-07-07 09:28", open: 24264, high: 24305, low: 24261, close: 24266 },
  { date: "2026-07-07 09:29", open: 24266, high: 24305, low: 24261, close: 24268 },
  { date: "2026-07-07 09:30", open: 24268, high: 24305, low: 24261, close: 24270 },
  { date: "2026-07-07 09:31", open: 24270, high: 24305, low: 24261, close: 24272 },
  { date: "2026-07-07 09:32", open: 24272, high: 24305, low: 24261, close: 24274 },
  { date: "2026-07-07 09:33", open: 24274, high: 24305, low: 24261, close: 24276 },
  { date: "2026-07-07 09:34", open: 24276, high: 24305, low: 24261, close: 24278 },
];

function run(label: string, nine35: C) {
  const candles = [...base, nine35];
  const eng = new FirstSwingEngine({ timeCap: "09:15", sustainBars: 7 });
  console.log(`\n========== ${label} ==========`);
  for (let i = 0; i < candles.length; i++) {
    const c = candles[i];
    eng.processBar(c, i);
    const a = eng as any;
    const note =
      i === 12 ? " <- 9:27 FIRST low break (count 1)"
      : i === candles.length - 1 ? " <- 9:35 lower-low (count 2) + high pokes prev pivot high"
      : "";
    console.log(
      `${c.date.slice(11, 16)} | dir=${eng.dir ?? "-"}${a.locked ? "L" : " "} ` +
      `dirConf=${a.dirConfirmed ? "Y" : "n"} ssb=${a.sameSideBreaks} osb=${a.oppositeSideBreaks} ` +
      `eHiP=${a.eHiPivot?.px} eLoP=${a.eLoPivot?.px} ` +
      `decl=${eng.declared ? "Y" : "n"} src=${eng.confirmSource ?? "-"} ` +
      `cand=${eng.candTime}@${eng.candPx}` + note,
    );
    if (eng.declared) {
      console.log(`   >> DECLARED dir=${eng.dir} start=${eng.startTime}@${eng.startPx} ` +
        `end=${eng.endTime}@${eng.endPx} confAt=${eng.confirmedAtTime} src=${eng.confirmSource}`);
    }
  }
  console.log("   POOLS", JSON.stringify(eng.debugPools()));
}

// CASE A: 9:35 RED bar -> HIGH prints first, then LOW.
run("CASE A: 9:35 RED (high then low) — should be DOWN but watch direction",
  { date: "2026-07-07 09:35", open: 24278, high: 24325, low: 24250, close: 24255 });

// CASE B: 9:35 GREEN bar -> LOW prints first, then HIGH.
run("CASE B: 9:35 GREEN (low then high) — should be DOWN, confirm via chop?",
  { date: "2026-07-07 09:35", open: 24278, high: 24325, low: 24250, close: 24285 });
