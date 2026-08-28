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
// Rules (course S6 + user spec):
//   REAL — CONTINUATION: session extreme extends twice (A→break, B→break) → dir confirmed
//   REAL — REVERSAL:     one extreme breaks, later the OTHER breaks → dir confirmed
//   REVERSAL CASE:       once locked (even dirConfirmed), an OPPOSITE extreme
//                        break wipes the swing memory → flip → ONE chop/sustain confirms
//   once dir confirmed:  CHOP-BREAK (prior opposite pivot taken out) or
//                        N-BAR SUSTAIN past the broken level → declared.
//   timeCap gates DECLARATION only — counting (locks/flips/chops) runs from bar one.
//   No fallback tier. Live-safe: closed bars only; declared end never repaints.

import { WalkerEngine } from "./flowline";
import type {
  AlgoPivot,
  FlowCandle,
  FlowSegment,
  FsV2Opts,
  FsV2Result,
} from "./flowline";

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

  private state: State = "watch";
  dir: "up" | "down" | null = null;
  private baseDir: "up" | "down" | null = null;
  private sameSideBreaks = 0;
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
  lastConfirmHit: { pool: string; px: number; idx: number; time: string } | null = null;

  constructor(opts: FsV2Opts = {}) {
    this.timeCap = opts.timeCap ?? "09:29";
    this.sustainBars = opts.sustainBars ?? 7;
  }

  processBar(c: FlowCandle, gIdx: number) {
    if (this.declared) return;
    this.barsSeen++;
    this.gIdx = gIdx;
    this.t = c.date.slice(11, 16);
    this.hi = c.high;
    this.lo = c.low;

    if (this.barsSeen === 1) {
      this.eHi = { px: c.high, idx: gIdx, time: this.t };
      this.eLo = { px: c.low, idx: gIdx, time: this.t };
      this.eHiPrev = { ...this.eHi };
      this.eLoPrev = { ...this.eLo };
      this.eHiPivot = { ...this.eHi };
      this.eLoPivot = { ...this.eLo };
      this.eHiPivotPrev = { ...this.eHiPivot };
      this.eLoPivotPrev = { ...this.eLoPivot };
    }

    // 1) Consume walker seals — the single source of truth for pivots.
    for (const p of this.walker.processBar(c, gIdx)) {
      if (!p.sealed) continue;
      if (p.kind === "H") {
        const cur = this.eHiPivot!;
        if (p.px > cur.px) {
          this.normalHighs.push(cur);
          this.eHiPivot = { px: p.px, idx: p.idx, time: p.time };
        } else {
          this.pushUnique(this.normalHighs, { px: p.px, idx: p.idx, time: p.time });
        }
      } else {
        const cur = this.eLoPivot!;
        if (p.px < cur.px) {
          this.normalLows.push(cur);
          this.eLoPivot = { px: p.px, idx: p.idx, time: p.time };
        } else {
          this.pushUnique(this.normalLows, { px: p.px, idx: p.idx, time: p.time });
        }
      }
    }

    // 2) Invalidation: a confirmed swing is void if price takes out the
    //    OPPOSITE extreme beyond the swing's start (the thesis failed).
    if (this.dirConfirmed && this.dir && this.startIdx >= 0) {
      if (this.dir === "down" && this.eHi.px > this.startPx) this.resetSwing();
      else if (this.dir === "up" && this.eLo.px < this.startPx) this.resetSwing();
    }

    // 3) Direction / break step — per BAR, against the FROZEN previous-bar
    //    walker extreme-pivot levels (order-independent, walker-sourced).
    //    COUNTING ALWAYS RUNS — the timeCap gates DECLARATION only (inside
    //    confirm()). Locks / flips / chop observations before 09:29 are
    //    remembered so a pre-cap reversal case (e.g. 28 Aug: 09:20 E-low
    //    break → 09:26 E-high break) is not thrown away.
    const upBreak = c.high > this.eHiPivotPrev.px;
    const downBreak = c.low < this.eLoPivotPrev.px;
    this.step(downBreak, upBreak);

    // 4) Keep the candidate end glued to the ACTUAL bar extreme in the swing dir
    //    (use c, not the running eLo/eHi which update only at end-of-bar).
    if (this.dir === "down" && c.low <= this.eLo.px)
      this.setCand({ px: c.low, idx: gIdx, time: this.t });
    if (this.dir === "up" && c.high >= this.eHi.px)
      this.setCand({ px: c.high, idx: gIdx, time: this.t });

    // 5) Sustain check (bar-level) once direction is confirmed.
    //    Also un-gated: checkSustain only feeds confirm(), which enforces the
    //    timeCap itself — pre-cap counting is kept, declaration stays capped.
    this.checkSustain(c);

    // 6) Advance frozen extremes to include THIS bar.
    if (c.high > this.eHi.px) this.eHi = { px: c.high, idx: gIdx, time: this.t };
    if (c.low < this.eLo.px) this.eLo = { px: c.low, idx: gIdx, time: this.t };
    this.eHiPrev = { ...this.eHi };
    this.eLoPrev = { ...this.eLo };
    // Walker extreme-pivot levels as of THIS bar become next bar's reference.
    this.eHiPivotPrev = { ...this.eHiPivot! };
    this.eLoPivotPrev = { ...this.eLoPivot! };
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
    if (this.dir === "down") {
      if (downBreak) {
        // continuation takes precedence over a same-bar opposite poke
        this.sameSideBreaks++;
        if (this.sameSideBreaks >= 2) {
          this.confirmDirection();
          this.checkChop(); // same-bar chop is safe: reversal flip was already blocked
        }
      } else if (upBreak) {
        this.flip("up");
        this.checkChop();
      }
    } else if (this.dir === "up") {
      if (upBreak) {
        this.sameSideBreaks++;
        if (this.sameSideBreaks >= 2) {
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
    this.state = "locked";
    const s = dir === "up" ? this.eLo : this.eHi;
    this.startIdx = s.idx;
    this.startTime = s.time;
    this.startPx = s.px;
    this.lockedLevel = dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
  }

  private confirmDirection() {
    this.dirConfirmed = true;
    this.lockedLevel =
      this.dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
  }

  private flip(dir: "up" | "down") {
    this.dir = dir;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.dirConfirmed = true;
    const s = dir === "up" ? this.eLo : this.eHi;
    this.startIdx = s.idx;
    this.startTime = s.time;
    this.startPx = s.px;
    this.lockedLevel = dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
  }

  private checkChop() {
    if (this.dir === "down") {
      const tgt = this.latestAfter(this.normalHighs);
      if (tgt && this.hi > tgt.px) {
        this.lastConfirmHit = { pool: "normal", px: tgt.px, idx: tgt.idx, time: tgt.time };
        this.confirm("chop");
      }
    } else if (this.dir === "up") {
      const tgt = this.latestAfter(this.normalLows);
      if (tgt && this.lo < tgt.px) {
        this.lastConfirmHit = { pool: "normal", px: tgt.px, idx: tgt.idx, time: tgt.time };
        this.confirm("chop");
      }
    }
  }

  private checkSustain(c: FlowCandle) {
    if (!this.dirConfirmed) {
      this.sustainStreak = 0;
      return;
    }
    const ref = this.lockedLevel;
    const hit = this.dir === "down" ? c.close < ref : c.close > ref;
    this.sustainStreak = hit ? this.sustainStreak + 1 : 0;
    if (this.sustainStreak >= this.sustainBars) this.confirm("sustain");
  }

  private confirm(src: "chop" | "sustain") {
    if (this.t < this.timeCap) return;
    this.declared = true;
    this.tier = "real";
    this.endIdx = this.candIdx;
    this.endTime = this.candTime;
    this.endPx = this.candPx;
    this.confirmedAtTime = this.t;
    this.confirmedAtIdx = this.gIdx;
    this.confirmSource = src;
  }

  private resetSwing() {
    this.dir = null;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.dirConfirmed = false;
    this.state = "watch";
    this.lockedLevel = NaN;
    this.sustainStreak = 0;
    this.startIdx = -1;
    this.startTime = "";
    this.startPx = NaN;
    this.candIdx = -1;
    this.candTime = "";
    this.candPx = NaN;
  }

  private setCand(l: Lvl) {
    this.candIdx = l.idx;
    this.candTime = l.time;
    this.candPx = l.px;
  }

  private pushUnique(pool: Lvl[], l: Lvl) {
    if (!pool.some((x) => x.idx === l.idx && x.px === l.px)) pool.push(l);
  }

  private latestAfter(pool: Lvl[]): Lvl | null {
    let best: Lvl | null = null;
    for (const l of pool) {
      if (l.idx > this.startIdx && (!best || l.idx > best.idx)) best = l;
    }
    return best;
  }

  debugPools() {
    return {
      startIdx: this.startIdx,
      startPx: this.startPx,
      lockedLevelPx: this.lockedLevel,
      lastConfirmHit: this.lastConfirmHit,
      normalHighs: this.normalHighs.map((l) => l.time + "@" + l.px.toFixed(2)),
      normalLows: this.normalLows.map((l) => l.time + "@" + l.px.toFixed(2)),
    };
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
