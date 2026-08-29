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
  // Arming gate (theory doc + flowline behaviour): A/B don't exist until the
  // flowline makes its FIRST pivot — until the walker emits its first
  // flip-sealed pivot (the bar-1 seed doesn't count), no lock/flip may fire.
  // The living session extremes at arming moment ARE A/B; they cannot move
  // without immediately breaking out (which is the lock).
  private armed = false;
  // Held pre-cap trigger (9:29 rule): a chop/sustain that fires before the
  // timeCap is held here — carrying the TRIGGER candle (for the FS marker) —
  // and flushed on the first bar at/after the cap. First trigger wins.
  private pendingConfirm: { src: "chop" | "sustain"; idx: number; time: string } | null = null;
  lastConfirmHit: { pool: string; px: number; idx: number; time: string } | null = null;
  // Direction-building break markers (chart: B1/B2/FLIP). Continuation day:
  // B1 (first A/B break → lock) + B2 (fresh-extreme extension → confirm).
  // Reversal day: B1 + FLIP (opposite extreme break → confirm). A flip day
  // like 2025-09-05 can carry several FLIPs — the last one wins.
  breakMarks: FsBreakMark[] = [];

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

    // 0) 9:29 rule (theory doc): a trigger HELD from before the cap is flushed
    //    and declared on the first bar at/after the cap — but the FS marker
    //    stays on the TRIGGER candle (the one that actually broke the level).
    if (this.pendingConfirm && this.t >= this.timeCap) {
      const pend = this.pendingConfirm;
      this.confirm(pend.src, { idx: pend.idx, time: pend.time });
      if (this.declared) return;
    }

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

    // 2) (removed) The old invalidation reset contradicted the theory doc: an
    //    opposite-original-extreme break IS the reversal flip (handled in
    //    step()), not swing-death. Living-extreme flips fire on the same bar
    //    the new extreme prints — strictly before the old next-bar reset.

    // 3) Direction / break step — per BAR, against the FROZEN LIVING SESSION
    //    EXTREMES (A/B — zero-lag, updated at end of each bar). The theory doc
    //    is explicit: locks/reversals are breaks of the session extremes, and
    //    continuation = EXTENDING the extreme twice — never re-breaking one
    //    fixed level. Walker-sealed pivots are used ONLY as chop-back targets
    //    ("previous marked pivot").
    //    COUNTING ALWAYS RUNS — the timeCap gates DECLARATION only (confirm()
    //    holds pre-cap triggers as pending). Locks / flips / chop observations
    //    before 09:29 are remembered so a pre-cap reversal case (e.g. 28 Aug:
    //    09:20 E-low break → 09:26 E-high break) is not lost.
    const upBreak = c.high > this.eHiPrev.px;
    const downBreak = c.low < this.eLoPrev.px;
    // ARMING GATE: before the first flowline pivot exists there is no A/B to
    // break — early pokes of the single opening candle are noise (24 Aug:
    // 9:16 +0.4pt poke must NOT lock a swing).
    if (this.armed) this.step(downBreak, upBreak);

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
    this.breakMarks.push({ idx: this.gIdx, time: this.t, kind: "B1", dir, px: this.lockedLevel });
  }

  private confirmDirection() {
    this.dirConfirmed = true;
    this.lockedLevel =
      this.dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
    this.breakMarks.push({
      idx: this.gIdx, time: this.t, kind: "B2", dir: this.dir!, px: this.lockedLevel,
    });
  }

  private flip(dir: "up" | "down") {
    this.dir = dir;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.dirConfirmed = true;
    this.pendingConfirm = null; // thesis reversed — any held trigger died with it
    const s = dir === "up" ? this.eLo : this.eHi;
    this.startIdx = s.idx;
    this.startTime = s.time;
    this.startPx = s.px;
    this.lockedLevel = dir === "up" ? this.eHiPrev.px : this.eLoPrev.px;
    this.breakMarks.push({ idx: this.gIdx, time: this.t, kind: "FLIP", dir, px: this.lockedLevel });
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
    // FRESH-EXTREME reset (theory doc): a bar extending the swing belongs to
    // the move, not the hold — also withdraws any held sustain trigger.
    const fresh = this.dir === "down" ? c.low < this.eLo.px : c.high > this.eHi.px;
    if (fresh) {
      this.sustainStreak = 0;
      if (this.pendingConfirm?.src === "sustain") this.pendingConfirm = null;
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

  private confirm(src: "chop" | "sustain", trig?: { idx: number; time: string }) {
    // 9:29 rule: nothing DECLARES before the cap — but the trigger is HELD as
    // pending (carrying the trigger candle) and flushed on the first bar
    // at/after the cap (step 0). First trigger wins.
    if (this.t < this.timeCap) {
      if (!this.pendingConfirm) {
        this.pendingConfirm = { src, idx: this.gIdx, time: this.t };
      }
      return;
    }
    this.pendingConfirm = null;
    this.declared = true;
    this.tier = "real";
    this.endIdx = this.candIdx;
    this.endTime = this.candTime;
    this.endPx = this.candPx;
    // FS marker sits on the TRIGGER candle when flushed from pending
    // (e.g. 21 Aug: 9:28 breached the 9:26 pivot — marker at 09:28,
    // declaration announced at the 9:29 cap).
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

  private latestAfter(pool: Lvl[]): Lvl | null {
    let best: Lvl | null = null;
    for (const l of pool) {
      // SELF-RATCHET GUARD (price-movement order, 24 Aug 10:03): the current
      // bar's own fresh pivot must NOT become the chop target — the candle
      // that breaks the previous pivot would otherwise be measured against
      // its own extreme and block its own confirmation. One helper serves
      // chop targets for BOTH directions, so this mirror is automatic.
      if (l.idx === this.gIdx) continue;
      if (l.idx > this.startIdx && (!best || l.idx > best.idx)) best = l;
    }
    return best;
  }

  debugPools() {
    return {
      armed: this.armed,
      pending: this.pendingConfirm,
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
