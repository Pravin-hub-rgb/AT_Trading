// FirstSwingEngine — SEPARATE engine for first-swing detection.
//
// Architectural fix for the FsV2 half-step ordering bug:
//   - The WalkerEngine (in flowline.ts) is the SINGLE SOURCE OF TRUTH for
//     sealed pivots. We consume its pivot stream for the "extreme pivot"
//     bookkeeping + chop-break targets (resolved, chronological, alternating).
//   - Break / direction detection is done per BAR (not per half-step) by
//     comparing the current bar's HIGH/LOW against the PREVIOUS bar's frozen
//     running extremes (eHiPrev / eLoPrev). A bar can therefore contribute at
//     most ONE break per side, and there is no "low-first vs high-first"
//     fragility — candle color can no longer change the verdict.
//   - Continuation takes precedence over reversal on the SAME bar, so a
//     volatile bar that both extends the locked direction AND pokes the
//     opposite extreme is treated as a continuation (count++), not a flip.
//
// Rules (course S6 + user spec + docs/first swing detection theory.md):
//   REAL — CONTINUATION: the session extreme EXTENDS twice (each break against
//                        a FRESH extreme, never re-breaking one fixed level) → dir confirmed
//   REAL — REVERSAL:     one extreme breaks, then the OTHER ORIGINAL extreme
//                        breaks — exactly ONE break needed → dir confirmed (flip)
//   REVERSAL CASE:       once locked (even dirConfirmed), an OPPOSITE extreme
//                        break wipes the swing memory → flip → ONE chop/sustain confirms
//   once dir confirmed:  CHOP-BREAK (previous MARKED PIVOT taken out) or
//                        N-BAR SUSTAIN → declared. Sustain is FAILURE-TO-EXTEND:
//                        selling swing = 7 closes back ABOVE the broken low;
//                        buying swing = 7 closes back BELOW the broken high;
//                        a fresh extreme print resets the streak.
//   Levels: LIVING session extremes (A/B, zero-lag) drive lock/extend/flip/
//   sustain-reference. Walker-sealed pivots are ONLY chop-back targets.
//   timeCap gates DECLARATION only — counting runs from bar one; a pre-cap
//   trigger is HELD (pending) and flushed on the first bar at/after the cap.
//   No fallback tier. Live-safe: closed bars only; declared end never repaints.

import { WalkerEngine } from "./flowline";
import type {
  AlgoPivot,
  FlowCandle,
  FlowSegment,
  FsV2Opts,
  FsV2Result,
} from "./flowline";

export interface FsBreakMark {
  idx: number;
  time: string;
  kind: "B1" | "B2" | "FLIP";
  dir: "up" | "down";
  px: number;
}

interface Lvl {
  px: number;
  idx: number;
  time: string;
}

type State = "watch" | "locked" | "confirmed";

export class FirstSwingEngine {
  private walker = new WalkerEngine();
  private barsSeen = 0;
  private t = "00:00";
  private gIdx = -1;
  private hi = NaN;
  private lo = NaN;
  private timeCap = "09:29";
  private sustainBars: number;
  private seedIdx = -1;

  // Running session extremes (updated at end of each bar).
  private eHi: Lvl = { px: -Infinity, idx: -1, time: "" };
  private eLo: Lvl = { px: Infinity, idx: -1, time: "" };
  // Frozen extremes as of the PREVIOUS bar close — the reference for break detection.
  private eHiPrev: Lvl = { px: -Infinity, idx: -1, time: "" };
  private eLoPrev: Lvl = { px: Infinity, idx: -1, time: "" };
  // Frozen WALKER extreme-pivot levels (sealed pivots) as of the previous bar.
  // Break detection uses these (matches "session extreme = pivot extreme"),
  // and because they are frozen per-bar they stay order-independent.
  private eHiPivotPrev: Lvl = { px: -Infinity, idx: -1, time: "" };
  private eLoPivotPrev: Lvl = { px: Infinity, idx: -1, time: "" };

  // Walker-sealed extreme pivots + the demoted "normal" pivots of each kind.
  private eHiPivot: Lvl | null = null;
  private eLoPivot: Lvl | null = null;
  private normalHighs: Lvl[] = [];
  private normalLows: Lvl[] = [];
  // Chop target: the latest marked pivot whose PIVOT CANDLE is at least 2 bars
  // old. A bar's own walker seal must never become its own chop reference
  // (same-bar self-block bug — 24 Aug:10:03), and a pivot must survive one
  // full bar after its pivot candle before it can be chopped back through
  // (12 Aug:10:03 — 1-bar-old micro-pivot broken by 0.25pt noise).
  private latestChoppableHigh(): Lvl | null {
    return this.latestPivotMinAge(this.normalHighs);
  }
  private latestChoppableLow(): Lvl | null {
    return this.latestPivotMinAge(this.normalLows);
  }
  private latestPivotMinAge(pool: Lvl[]): Lvl | null {
    for (let i = pool.length - 1; i >= 0; i--) {
      if (pool[i].idx <= this.gIdx - 2) return pool[i];
    }
    return null;
  }

  private state: State = "watch";
  dir: "up" | "down" | null = null;
  private baseDir: "up" | "down" | null = null;
  private sameSideBreaks = 0;
  // CORNER pivot: the first walker-sealed pivot AFTER B1 in the locked
  // direction. This forms the V/^ corner shape. B2 requires a LATER pivot
  // to BREAK this corner (not the corner itself).
  private cornerPivot: Lvl | null = null;
  // B2 trigger pivot: the pivot that BROKE the corner and triggered B2
  private b2Pivot: Lvl | null = null;
  // Block chop/sustain on the same bar as B2 (B2 must be followed by at least
  // one bar before confirmation can fire).
  private justFiredB2 = false;
  // B1 bar index: only pivots from AFTER this bar can trigger B2
  // (B2 should not fire on the same bar as B1)
  private b1BarIdx = -1;
  // Flag to allow corner recording. Starts FALSE after lock,
  // becomes TRUE on the next bar.
  private allowCornerRecord = false;
  private dirConfirmed = false;
  private lockedLevel = NaN;

  startIdx = -1;
  startTime = "";
  startPx = NaN;
  private candIdx = -1;
  candTime = "";
  candPx = NaN;

  declared = false;
  tier: "real" | null = null;
  endTime = "";
  endIdx = -1;
  endPx = NaN;
  confirmedAtTime = "";
  confirmedAtIdx = -1;
  confirmSource: "chop" | "sustain" | null = null;

  /** True once a first break has locked a tentative direction (watch -> locked). */
  get locked() {
    return this.state !== "watch";
  }

  private sustainStreak = 0;
  // Arming gate (theory doc + flowline behaviour): A/B don't exist until the
  // flowline makes its FIRST pivot — until the walker emits its first
  // flip-sealed pivot (the bar-1 seed doesn't count), no lock/flip may fire.
  // The living session extremes at arming moment ARE A/B; they cannot move
  // without immediately breaking out (which is the lock).
  private armed = false;
  lastConfirmHit: {
    pool: string;
    px: number;
    idx: number;
    time: string;
  } | null = null;
  // Direction-building break markers (chart: B1/B2/FLIP). Continuation day:
  // B1 (first A/B break → lock) + B2 (fresh-extreme extension → confirm).
  // Reversal day: B1 + FLIP (opposite extreme break → confirm). A flip day
  // like 2025-09-05 can carry several FLIPs — the last one wins.
  breakMarks: FsBreakMark[] = [];

  private minBars: number;
  constructor(opts: FsV2Opts = {}) {
    this.timeCap = opts.timeCap ?? "09:29";
    this.sustainBars = opts.sustainBars ?? 7;
    this.minBars = (opts as any).minBars ?? (opts as any).min_bars ?? 14;
  }

  processBar(c: FlowCandle, gIdx: number) {
    if (this.declared) return;
    this.barsSeen++;
    this.gIdx = gIdx;
    this.t = c.date.slice(11, 16);
    this.hi = c.high;
    this.lo = c.low;

    // 0) 9:29 rule: triggers before 9:29 are IGNORED. The first valid trigger
    //    at/after 9:29 is the one that declares.
    // Clear the B2-block flag at start of each bar.
    this.justFiredB2 = false;

    if (this.barsSeen === 1) {
      this.eHi = { px: c.high, idx: gIdx, time: this.t };
      this.eLo = { px: c.low, idx: gIdx, time: this.t };
      this.eHiPrev = { ...this.eHi };
      this.eLoPrev = { ...this.eLo };
      this.eHiPivot = { ...this.eHi };
      this.eLoPivot = { ...this.eLo };
      this.eHiPivotPrev = { ...this.eHiPivot };
      this.eLoPivotPrev = { ...this.eLoPivot };
      this.seedIdx = gIdx;
    }

    // 1) Consume walker seals — the single source of truth for pivots.
    //    The FIRST flip-sealed pivot (bar-1 seed excluded) is the arming
    //    event: A/B exist from that moment (see `armed`).
    for (const p of this.walker.processBar(c, gIdx)) {
      if (!p.sealed) continue;
      if (this.barsSeen >= 2) this.armed = true;
      if (p.kind === "H") {
        const cur = this.eHiPivot!;
        if (p.px > cur.px) {
          this.normalHighs.push(cur);
          this.eHiPivot = { px: p.px, idx: p.idx, time: p.time };
          // CORNER: track the first pivot after B1 as the corner (V/^ shape).
          // Use >= to include the B1 candle itself as the corner.
          if (
            this.dir === "up" &&
            p.px > this.lockedLevel &&
            p.idx >= this.b1BarIdx &&
            this.allowCornerRecord
          ) {
            if (!this.cornerPivot) {
              this.cornerPivot = { px: p.px, idx: p.idx, time: p.time };
            }
          }
        } else {
          this.pushUnique(this.normalHighs, {
            px: p.px,
            idx: p.idx,
            time: p.time,
          });
        }
      } else {
        const cur = this.eLoPivot!;
        if (p.px < cur.px) {
          this.normalLows.push(cur);
          this.eLoPivot = { px: p.px, idx: p.idx, time: p.time };
          // CORNER: track the first pivot after B1 as the corner (V/^ shape).
          // Use >= to include the B1 candle itself as the corner (17 Aug case).
          if (
            this.dir === "down" &&
            p.px < this.lockedLevel &&
            p.idx >= this.b1BarIdx &&
            this.allowCornerRecord
          ) {
            if (!this.cornerPivot) {
              this.cornerPivot = { px: p.px, idx: p.idx, time: p.time };
            }
          }
        } else {
          this.pushUnique(this.normalLows, {
            px: p.px,
            idx: p.idx,
            time: p.time,
          });
        }
      }
    }

    // 2) (removed) The old invalidation reset contradicted the theory doc: an
    //    opposite-original-extreme break IS the reversal flip (handled in
    //    step()), not swing-death. Living-extreme flips fire on the same bar
    //    the new extreme prints — strictly before the old next-bar reset.

    // 3) Direction / break step — per BAR, against the FROZEN LIVING SESSION
    //    EXTREMES (A/B — zero-lag, updated at end of each bar).
    //    COUNTING ALWAYS RUNS — the timeCap gates DECLARATION only.
    const upBreak = c.high > this.eHiPrev.px;
    const downBreak = c.low < this.eLoPrev.px;
    // ARMING GATE: before the first flowline pivot exists there is no A/B to
    // break — early pokes of the single opening candle are noise (24 Aug:
    // 9:16 +0.4pt poke must NOT lock a swing).
    if (this.armed) this.step(downBreak, upBreak);

    // 4) Keep the candidate end glued to the ACTUAL bar extreme in the swing dir
    //    (use c, not the running eLo/eHi which update only at end-of-bar).
    if (this.dir === "down" && c.low < this.eLo.px)
      this.setCand({ px: c.low, idx: gIdx, time: this.t });
    if (this.dir === "up" && c.high > this.eHi.px)
      this.setCand({ px: c.high, idx: gIdx, time: this.t });

    // 5) Sustain check (bar-level) once direction is confirmed.
    //    Also un-gated: checkSustain only feeds confirm(), which enforces the
    //    timeCap itself — pre-cap counting is kept, declaration stays capped.
    this.checkSustain(c);

    // 6) Advance frozen extremes to include THIS bar.
    if (c.high > this.eHi.px)
      this.eHi = { px: c.high, idx: gIdx, time: this.t };
    if (c.low < this.eLo.px) this.eLo = { px: c.low, idx: gIdx, time: this.t };
    this.eHiPrev = { ...this.eHi };
    this.eLoPrev = { ...this.eLo };
    // Walker extreme-pivot levels as of THIS bar become next bar's reference.
    this.eHiPivotPrev = { ...this.eHiPivot! };
    this.eLoPivotPrev = { ...this.eLoPivot! };
    // Enable corner recording for the NEXT bar onwards
    // (prevents same-bar walker emissions from recording the corner)
    if (this.state === "locked") {
      this.allowCornerRecord = true;
    }
  }

  private step(downBreak: boolean, upBreak: boolean) {
    if (this.state === "watch") {
      if (downBreak) this.lock("down");
      else if (upBreak) this.lock("up");
      return;
    }
    if (this.dirConfirmed) {
      // REVERSAL CASE: an opposite extreme break after confirmation wipes the
      // thesis entirely — flip immediately (flip() resets memory: baseDir,
      // breaks, start = counter-extreme) and let ONE fresh chop/sustain
      // confirm the new direction. Same-bar continuation still takes
      // precedence (identical invariant to the locked phase below): a bar
      // that extends the swing AND pokes the opposite extreme is treated as
      // continuation, not a flip.
      if (this.dir === "down" && upBreak && !downBreak) {
        this.flip("up");
        this.checkChop();
        return;
      }
      if (this.dir === "up" && downBreak && !upBreak) {
        this.flip("down");
        this.checkChop();
        return;
      }
      this.checkChop();
      return;
    }
    // LOCKED, direction not yet confirmed.
    // B2 confirmation:
    //   - If a corner pivot exists: B2 fires when PRICE breaks the corner.
    //   - If no corner yet: B2 fires on the first break of the B1 extreme.
    // B2 fires when candle's low breaks BELOW the LATEST walker-sealed low pivot
    // (eLoPivot). The corner is just the latest eLoPivot after B1. We only fire
    // B2 when the corner is from a PREVIOUS bar (so the walker has had a chance
    // to update eLoPivot with the corner value).
    if (this.dir === "down") {
      if (downBreak) {
        // Check against the latest walker-sealed eLoPivot
        // Must be from a different bar than B1 (so it's a fresh pivot)
        if (
          this.eLoPivot &&
          this.eLoPivot.idx >= this.b1BarIdx &&
          this.lo < this.eLoPivot.px
        ) {
          this.b2Pivot = { px: this.lo, idx: this.gIdx, time: this.t };
          this.confirmDirection();
          this.checkChop();
        }
      } else if (upBreak) {
        this.flip("up");
        this.checkChop();
      }
    } else if (this.dir === "up") {
      if (upBreak) {
        if (
          this.eHiPivot &&
          this.eHiPivot.idx >= this.b1BarIdx &&
          this.hi > this.eHiPivot.px
        ) {
          this.b2Pivot = { px: this.hi, idx: this.gIdx, time: this.t };
          this.confirmDirection();
          this.checkChop();
        }
      } else if (downBreak) {
        this.flip("down");
        this.checkChop();
      }
    }
  }

  private lock(dir: "up" | "down") {
    this.dir = dir;
    this.baseDir = dir;
    this.sameSideBreaks = 1;
    // Reset corner tracking for new lock
    this.cornerPivot = null;
    this.b2Pivot = null; // Reset B2 trigger
    // Track the B1 bar index so B2 can only fire from a LATER bar
    this.b1BarIdx = this.gIdx;
    this.state = "locked";
    // Don't record corner on the same bar as lock
    this.allowCornerRecord = false;
    const s = dir === "up" ? this.eLo : this.eHi;
    this.startIdx = s.idx;
    this.startTime = s.time;
    this.startPx = s.px;
    this.lockedLevel = dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
    this.breakMarks.push({
      idx: this.gIdx,
      time: this.t,
      kind: "B1",
      dir,
      px: this.lockedLevel,
    });
  }

  private confirmDirection() {
    this.dirConfirmed = true;
    // B2 mark goes on the PIVOT candle that extended beyond B1, not on
    // the current bar. This is the bar where the walker sealed the new
    // extreme pivot that confirmed the break.
    const b2 = this.b2Pivot;
    this.lockedLevel = this.dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
    this.breakMarks.push({
      idx: b2 ? b2.idx : this.gIdx,
      time: b2 ? b2.time : this.t,
      kind: "B2",
      dir: this.dir!,
      px: b2 ? b2.px : this.lockedLevel,
    });
    this.b2Pivot = null;
    this.justFiredB2 = true; // block chop/sustain on this bar
  }

  private flip(dir: "up" | "down") {
    this.dir = dir;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.cornerPivot = null; // Reset corner pivot on flip
    this.b2Pivot = null; // Reset B2 trigger
    this.b1BarIdx = -1; // Reset B1 bar index on flip
    this.allowCornerRecord = false; // Block same-bar corner recording after flip
    this.dirConfirmed = true;
    const s = dir === "up" ? this.eLo : this.eHi;
    this.startIdx = s.idx;
    this.startTime = s.time;
    this.startPx = s.px;
    this.lockedLevel = dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
    this.breakMarks.push({
      idx: this.gIdx,
      time: this.t,
      kind: "FLIP",
      dir,
      px: this.lockedLevel,
    });
  }

  private checkChop() {
    // Block chop on the same bar as B2 (B2 must be followed by at least one bar).
    if (this.justFiredB2) return;
    // Chop = price reclaims the most recently marked pivot:
    // - Selling swing (down): breaks above the most recent high pivot
    // - Buying swing (up): breaks below the most recent low pivot
    // The target is the latest pivot whose PIVOT CANDLE is at least 2 bars old:
    // a pivot must survive one full bar after its pivot candle before it becomes
    // a valid chop reference. This both fixes the same-bar self-block
    // (24 Aug: 10:03 — own seal has age 0) and avoids noise-firing on
    // 1-bar-old micro-pivots (12 Aug: 10:03 breaking 10:02@24375.75 by 0.25pt).
    if (this.dir === "down") {
      const tgt =
        this.latestChoppableHigh() ?? this.latestPivot(this.normalHighs);
      if (tgt && this.hi > tgt.px) {
        this.lastConfirmHit = {
          pool: "normal",
          px: tgt.px,
          idx: tgt.idx,
          time: tgt.time,
        };
        this.confirm("chop");
      }
    } else if (this.dir === "up") {
      const tgt =
        this.latestChoppableLow() ?? this.latestPivot(this.normalLows);
      if (tgt && this.lo < tgt.px) {
        this.lastConfirmHit = {
          pool: "normal",
          px: tgt.px,
          idx: tgt.idx,
          time: tgt.time,
        };
        this.confirm("chop");
      }
    }
  }

  private checkSustain(c: FlowCandle) {
    // Block sustain on the same bar as B2 (B2 must be followed by at least one bar).
    if (this.justFiredB2) return;
    if (!this.dirConfirmed) {
      this.sustainStreak = 0;
      return;
    }
    // FRESH-EXTREME reset (theory doc): a bar extending the swing belongs to
    // the move, not the hold — also withdraws any held sustain trigger.
    const fresh =
      this.dir === "down" ? c.low < this.eLo.px : c.high > this.eHi.px;
    if (fresh) {
      this.sustainStreak = 0;
      return;
    }
    // FAILURE-TO-EXTEND (theory doc): a selling swing sustains when price
    // stops making new lows and rests back ABOVE the broken low; a buying
    // swing when it rests back BELOW the broken high. NOT "holding the
    // breakout" — that was the old inverted behaviour.
    const ref = this.lockedLevel;
    const hold = this.dir === "down" ? c.close > ref : c.close < ref;
    this.sustainStreak = hold ? this.sustainStreak + 1 : 0;
    if (this.sustainStreak >= this.sustainBars) this.confirm("sustain");
  }

  private confirm(
    src: "chop" | "sustain",
    trig?: { idx: number; time: string },
  ) {
    // 9:29 rule: nothing DECLARES before the cap. If trigger fires pre-9:29,
    // IGNORE it — continue looking for a new chop/sustain. The first valid
    // trigger AT or AFTER 9:29 is the one that declares.
    if (this.t < this.timeCap) {
      return; // ignore pre-cap triggers
    }
    if (this.barsSeen < this.minBars) {
      return;
    }
    this.declared = true;
    this.tier = "real";
    this.endIdx = this.candIdx;
    this.endTime = this.candTime;
    this.endPx = this.candPx;
    // FS marker sits on the TRIGGER candle.
    this.confirmedAtTime = trig ? trig.time : this.t;
    this.confirmedAtIdx = trig ? trig.idx : this.gIdx;
    this.confirmSource = src;
  }

  private setCand(l: Lvl) {
    this.candIdx = l.idx;
    this.candTime = l.time;
    this.candPx = l.px;
  }

  private pushUnique(pool: Lvl[], l: Lvl) {
    if (!pool.some((x) => x.idx === l.idx && x.px === l.px)) pool.push(l);
  }

  // Returns the LATEST (most recent) marked pivot in the pool.
  // Chop fires when price reclaims this level.
  private latestPivot(pool: Lvl[]): Lvl | null {
    if (pool.length === 0) return null;
    return pool[pool.length - 1]; // most recent
  }

  debugPools() {
    return {
      armed: this.armed,
      startIdx: this.startIdx,
      startPx: this.startPx,
      lockedLevelPx: this.lockedLevel,
      lastConfirmHit: this.lastConfirmHit,
      normalHighs: this.normalHighs.map((l) => l.time + "@" + l.px.toFixed(2)),
      normalLows: this.normalLows.map((l) => l.time + "@" + l.px.toFixed(2)),
    };
  }

  /** Re-initialize the engine to detect a new swing starting from a pre-defined
   *  price level (e.g., the first swing's extreme). After reset, the next
   *  processBar increments barsSeen to 2, skipping the barsSeen==1 initialization
   *  (seed bar is already set). This makes the seed behave exactly like the
   *  09:15 candle for the new swing.
   *  NOTE: seedPx seeds BOTH hi/lo to the same extreme (flat). For a true
   *  mirror of first-swing init (which uses 09:15 high/low), use resetWithCandle. */
  reset(seedPx: number, seedIdx: number, seedTime: string) {
    this.walker = new WalkerEngine();
    this.barsSeen = 1;
    this.t = seedTime;
    this.gIdx = seedIdx;
    this.hi = NaN;
    this.lo = NaN;
    this.seedIdx = seedIdx;

    const seed: Lvl = { px: seedPx, idx: seedIdx, time: seedTime };
    this.eHi = { ...seed };
    this.eLo = { ...seed };
    this.eHiPrev = { ...seed };
    this.eLoPrev = { ...seed };
    this.eHiPivot = { ...seed };
    this.eLoPivot = { ...seed };
    this.eHiPivotPrev = { ...seed };
    this.eLoPivotPrev = { ...seed };

    this.normalHighs.length = 0;
    this.normalLows.length = 0;

    this.state = "watch";
    this.dir = null;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.cornerPivot = null;
    this.b2Pivot = null;
    this.justFiredB2 = false;
    this.b1BarIdx = -1;
    this.allowCornerRecord = false;
    this.dirConfirmed = false;
    this.lockedLevel = NaN;

    this.startIdx = -1;
    this.startTime = "";
    this.startPx = NaN;
    this.candIdx = -1;
    this.candTime = "";
    this.candPx = NaN;

    this.declared = false;
    this.tier = null;
    this.endTime = "";
    this.endIdx = -1;
    this.endPx = NaN;
    this.confirmedAtTime = "";
    this.confirmedAtIdx = -1;
    this.confirmSource = null;
    this.lastConfirmHit = null;
    this.sustainStreak = 0;
    this.armed = false;
    this.breakMarks.length = 0;
  }

  /** True mirror of first-swing init: seed with the actual OHLC of the 09:27
   *  cyan candle (high/low), not a flat level. This is what the user asked:
   *  “take ohlc value from 9:27 and run it though first swing engine”.
   *  After this, 09:28 is the second bar (barsSeen=2) and must break the
   *  09:27 low/high to lock. */
  resetWithCandle(c: FlowCandle, gIdx: number) {
    this.walker = new WalkerEngine();
    this.barsSeen = 1;
    this.t = c.date.slice(11, 16);
    this.gIdx = gIdx;
    this.hi = NaN;
    this.lo = NaN;
    this.seedIdx = gIdx;

    this.eHi = { px: c.high, idx: gIdx, time: this.t };
    this.eLo = { px: c.low, idx: gIdx, time: this.t };
    this.eHiPrev = { ...this.eHi };
    this.eLoPrev = { ...this.eLo };
    this.eHiPivot = { ...this.eHi };
    this.eLoPivot = { ...this.eLo };
    this.eHiPivotPrev = { ...this.eHiPivot };
    this.eLoPivotPrev = { ...this.eLoPivot };

    this.normalHighs.length = 0;
    this.normalLows.length = 0;

    this.state = "watch";
    this.dir = null;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.cornerPivot = null;
    this.b2Pivot = null;
    this.justFiredB2 = false;
    this.b1BarIdx = -1;
    this.allowCornerRecord = false;
    this.dirConfirmed = false;
    this.lockedLevel = NaN;

    this.startIdx = -1;
    this.startTime = "";
    this.startPx = NaN;
    this.candIdx = -1;
    this.candTime = "";
    this.candPx = NaN;

    this.declared = false;
    this.tier = null;
    this.endTime = "";
    this.endIdx = -1;
    this.endPx = NaN;
    this.confirmedAtTime = "";
    this.confirmedAtIdx = -1;
    this.confirmSource = null;
    this.lastConfirmHit = null;
    this.sustainStreak = 0;
    this.armed = false;
    this.breakMarks.length = 0;
  }
}

// ===== Batch helpers (same surface as the legacy flowline.ts API) =====

export function computeFsV2Results(
  candles: FlowCandle[],
  opts: FsV2Opts = {},
): FsV2Result[] {
  const byDay = new Map<string, { c: FlowCandle; gIdx: number }[]>();
  candles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const out: FsV2Result[] = [];
  byDay.forEach((items, day) => {
    const eng = new FirstSwingEngine(opts);
    for (const it of items) eng.processBar(it.c, it.gIdx);

    if (!eng.declared || eng.startIdx < 0) return;
    out.push({
      day,
      outcome: "real",
      confIdx: eng.confirmedAtIdx,
      seg: {
        dir: eng.dir === "up" ? "B" : "S",
        startIdx: eng.startIdx,
        startPx: eng.startPx,
        endIdx: eng.endIdx,
        endPx: eng.endPx,
      },
      source: eng.confirmSource,
      dir: eng.dir,
      breaks: eng.breakMarks,
    });
  });
  return out;
}

export function computeFsV2Declared(
  candles: FlowCandle[],
  opts: FsV2Opts = {},
): FlowSegment[] {
  return computeFsV2Results(candles, opts)
    .filter((r): r is FsV2Result & { seg: FlowSegment } => r.seg !== null)
    .map((r) => r.seg);
}
