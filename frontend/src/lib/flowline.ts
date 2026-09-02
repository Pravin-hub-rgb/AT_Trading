// Flow-Line – Algo walker + FsV2 (white line only, orange manual line removed):

// First-swing detection now lives in its own engine (see firstswing.ts),
// driven by the WalkerEngine pivot stream. flowline.ts keeps the public
// computeFsV2* surface and delegates to it.
import { SwingEngine, type FsBreakMark } from "./firstswing";
export { SwingEngine, FirstSwingEngine } from "./firstswing";

// -- branch coverage instrumentation (active only with FLOW_COV=1) --------
const FLOW_COV: Record<string, number> = {};
const cov = (tag: string) => {
  const p = typeof process !== "undefined" ? process : undefined;
  if (!p?.env?.FLOW_COV) return;
  FLOW_COV[tag] = (FLOW_COV[tag] ?? 0) + 1;
};
if (typeof process !== "undefined" && process.env?.FLOW_COV) {
  process.on("beforeExit", () => {
    console.error("[COV] " + JSON.stringify(FLOW_COV));
  });
}

export interface FlowSegment {
  dir: "B" | "S";
  startIdx: number;
  startPx: number;
  endIdx: number;
  endPx: number;
}

export interface FlowCandle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface AlgoPivot {
  idx: number; // global candle index
  time: string; // HH:MM
  kind: "H" | "L";
  px: number;
  sealed: boolean; // true = leg flipped after it; false = current forming swing
}

// =====================================================================
// ? ALGO WALKER – color-aware candle path follower
//
// Rules (course S6 + user spec):
//   - GREEN candle path: LOW prints first ? HIGH   (bottom-to-top)
//   - RED candle path: HIGH prints first ? LOW     (top-to-bottom)
//   - Each bar processed as TWO half-steps in that order.
//   - Active leg tracks a running extreme ("stamp"). Same-direction breaks
//     SHIFT the stamp (extended leg = no new pivot). An opposite-side break
//     of the PREVIOUS bar's extreme SEALS the stamp as a pivot and flips.
//   - INSIDE candle: range within prev bar ? its far-side extreme becomes a
//     PENDING pivot. Next bar resolves:
//       breaks near side  -> confirm (push pending), leg continues
//       breaks far side   -> SKIP insider (discard), seal stamp, flip leg
//   - Live-safe: only closed bars consumed; pending resolves on next close.
// =====================================================================

type Step = { side: "low" | "high"; px: number };

function barSteps(c: FlowCandle): Step[] {
  const green = c.close >= c.open;
  return green
    ? [
        { side: "low", px: c.low },
        { side: "high", px: c.high },
      ]
    : [
        { side: "high", px: c.high },
        { side: "low", px: c.low },
      ];
}

// Steppable walker – EXACT state-machine translation of the original
// batch walkDay(): same seeds, same pending/onion/band logic, same seals.
// Contract: feed CLOSED bars via processBar(); each call returns the pivots
// SEALED during that bar. finalize() emits the trailing open swing.
export class WalkerEngine {
  private k = -1;
  private dir: "up" | "down" = "up";
  private stampIdx = -1;
  private stampK = -1;
  private stampT = "";
  private stampPx = NaN;
  private prevHigh = NaN;
  private prevLow = NaN;
  // Marker band = px of the most recently PUSHED H pivot and L pivot.
  // Used to decide insider+volatile handling (skip inside / mark outside).
  // One-sided until the opposite kind actually prints its first marker.
  private bandLow: number | null = null;
  private bandHigh: number | null = null;
  private pending: WPending | null = null;
  // Running extremes since the last pushed pivot of each kind. These are the
  // trader's "real" swing marks: a confirming insider may sit inside an
  // extreme the leg already printed, and the LEG's extreme wins.
  private hiPx: number | null = null;
  private hiIdx = -1;
  private hiK = -1;
  private hiT = "";
  private loPx: number | null = null;
  private loK = -1;
  private loIdx = -1;
  private loT = "";
  private barOut: AlgoPivot[] = [];

  /** Sealed pivots emitted during THIS bar (usually empty). */
  processBar(c: FlowCandle, gIdx: number): AlgoPivot[] {
    this.barOut = [];
    this.k++;
    const k = this.k;
    const t = c.date.slice(11, 16);

    if (k === 0) {
      // ---- seed from first bar's colour ----
      const firstGreen = c.close >= c.open;
      this.emit({
        idx: gIdx,
        time: t,
        kind: firstGreen ? "L" : "H",
        px: firstGreen ? c.low : c.high,
        sealed: true,
      });
      this.dir = firstGreen ? "up" : "down";
      this.stampIdx = gIdx;
      this.stampK = 0;
      this.stampT = t;
      this.stampPx = firstGreen ? c.high : c.low;
      this.prevHigh = c.high;
      this.prevLow = c.low;
      if (firstGreen) {
        this.bandLow = c.low;
        this.loPx = null;
        this.hiPx = c.high;
        this.hiIdx = gIdx;
        this.hiK = 0;
        this.hiT = t;
        this.hiCloseGreen = true;
      } else {
        this.bandHigh = c.high;
        this.hiPx = null;
        this.loPx = c.low;
        this.loIdx = gIdx;
        this.loK = 0;
        this.loT = t;
        this.loCloseRed = true;
      }
      cov(firstGreen ? "seed:green" : "seed:red");
      return this.barOut;
    }

    let flippedThisBar = false;
    let skipSteps = false;

    // ---- pending resolution BEFORE this bar's steps ----
    // Outside bar (breaks BOTH sides) => insider SKIPPED, leg takes the
    // bar's ending direction. Single-side break => confirm/skip normally.
    const pend = this.pending;
    if (pend) {
      const pk: "H" | "L" = pend.kind;
      const stackHi = Math.max(pend.px, pend.near);
      const stackLo = Math.min(pend.px, pend.near);

      // ---- ONION RULE: nested insider absorbs into the stack ----
      // Strictly inside the current stack => consolidation continues. Every
      // stack layer contributes ONE alternating zigzag point: layer 1 its
      // FAR edge, layer 2 its NEAR edge, layer 3 FAR again... Parity of the
      // peel buffer decides which side this layer contributes. Append this
      // layer's record, shrink stack to this bar.
      if (c.high < stackHi && c.low > stackLo) {
        // ROLE-BASED (see closeStack) – pendPx = far edge BY DEFINITION.
        const wantFar = pend.inner.length % 2 === 0;
        cov((wantFar ? "onion:FAR-layer:pk" : "onion:NEAR-layer:pk") + pk);
        pend.inner.push(
          wantFar
            ? {
                idx: pend.idx,
                k: pend.k,
                time: pend.time,
                kind: pk,
                px: pend.px,
              }
            : {
                idx: pend.idx,
                k: pend.k,
                time: pend.time,
                kind: pk === "H" ? "L" : "H",
                px: pend.near,
              },
        );
        this.pending = {
          kind: pk,
          idx: gIdx,
          k,
          time: t,
          px: pk === "H" ? c.high : c.low,
          near: pk === "H" ? c.low : c.high,
          inner: pend.inner,
        };
        flippedThisBar = true;
        skipSteps = true;
      } else {
        // STRICT breaks: an exact touch/equal-print does NOT count as a break.
        const confirmHit = pk === "H" ? c.low < pend.near : c.high > pend.near;
        const skipHit = pk === "H" ? c.high > pend.px : c.low < pend.px;
        if (confirmHit && !skipHit) {
          cov("confirm:pk" + pk + (pend.inner.length > 0 ? ":peeled" : ""));
          // CONFIRM – seal pre-insider swing; a PEELED stack emits its
          // remaining alternating layers (continuation keeps the leg);
          // a plain single insider prints its far edge (+override).
          this.pushStamp();
          const p = pend;
          const hadPeel = p.inner.length > 0;
          const lastRec = this.closeStack(p);
          if (hadPeel && lastRec) {
            this.stampIdx = lastRec.idx;
            this.stampK = lastRec.k;
            this.stampT = lastRec.time;
            this.stampPx = lastRec.px;
          } else {
            let pIdx = p.idx;
            let pT = p.time;
            let pPx = p.px;
            let pK = p.k;
            if (pk === "H" && this.hiPx !== null && this.hiPx > pPx) {
              // leg already printed a higher high AFTER the reference marker
              const hiAfter =
                this.hiK > this.stampK ||
                (this.hiK === this.stampK && this.hiCloseGreen);
              if (hiAfter) {
                pIdx = this.hiIdx;
                pT = this.hiT;
                pPx = this.hiPx;
                pK = this.hiK;
              }
            }
            if (pk === "L" && this.loPx !== null && this.loPx < pPx) {
              const loAfter =
                this.loK > this.stampK ||
                (this.loK === this.stampK && this.loCloseRed);
              if (loAfter) {
                pIdx = this.loIdx;
                pT = this.loT;
                pPx = this.loPx;
                pK = this.loK;
              }
            }
            this.emit({ idx: pIdx, time: pT, kind: pk, px: pPx, sealed: true });
            this.trackBand(pk, pPx);
            this.stampIdx = pIdx;
            this.stampK = pK;
            this.stampT = pT;
            this.stampPx = pPx;
          }
          this.pending = null;
        } else if (skipHit && !confirmHit) {
          cov("skip1:pk" + pk);
          // SINGLE-SIDE far break -> reversal flip. Peeled stacks emit their
          // remaining alternating layers before the flip; single insiders
          // stay print-free (legacy).
          const p0 = pend;
          this.pending = null;
          this.pushStamp();
          this.closeStack(p0);
          this.dir = pk === "H" ? "up" : "down";
          this.stampIdx = gIdx;
          this.stampK = k;
          this.stampT = t;
          this.stampPx = pk === "H" ? c.high : c.low;
          flippedThisBar = true;
          skipSteps = true;
        } else if (skipHit) {
          // DOUBLE-BREAK (volatile candle) – marker-band decides.
          // Band = [active low marker, active high marker]; the ACTIVE leg's
          // running stamp IS its side's live marker.
          const iLo = Math.min(pend.px, pend.near); // stack low
          const iHi = Math.max(pend.px, pend.near); // stack high
          const effLo =
            this.dir === "down"
              ? this.stampPx
              : (this.bandLow ?? Number.NEGATIVE_INFINITY);
          const effHi =
            this.dir === "up"
              ? this.stampPx
              : (this.bandHigh ?? Number.POSITIVE_INFINITY);
          const insideBand =
            iHi <= effHi && iLo >= effLo && c.high <= effHi && c.low >= effLo;
          if (insideBand) {
            cov("dbl:insideBand:pk" + pk);
            // Inside band -> SKIP insider (continuation); line rides to the
            // volatile bar's extreme. (e.g. 21 Aug 11:00/11:05)
            this.pending = null;
            this.pushStamp();
            this.dir = pk === "H" ? "up" : "down";
            this.stampIdx = gIdx;
            this.stampK = k;
            this.stampT = t;
            this.stampPx = pk === "H" ? c.high : c.low;
            skipSteps = true; // bar consumed – its halves already priced in
          } else {
            cov("dbl:escape:pk" + pk);
            // Band ESCAPE -> MARK the stack's far-side extreme (mirrored):
            //   marker L (pk=H): seal L@stamp -> peel -> H@stack.high, leg down from near
            //   marker H (pk=L): seal H@stamp -> peel -> L@stack.low, leg up from near
            // The volatile bar's own halves then play out via normal steps,
            // producing both the green-volatile and red-volatile chains.
            const p = pend;
            this.pending = null;
            this.pushStamp(); // seal the running stamp (the P-candle marker)
            const lastRec = this.closeStack(p); // peel layers + final far-edge record
            if (!lastRec) {
              // single insider (no peel): legacy direct far-edge print
              this.emit({
                idx: p.idx,
                time: p.time,
                kind: pk,
                px: p.px,
                sealed: true,
              });
              this.trackBand(pk, p.px);
            }
            this.dir = pk === "H" ? "down" : "up"; // leg heads toward the near side
            this.stampIdx = p.idx;
            this.stampK = p.k;
            this.stampT = p.time;
            this.stampPx = p.near; // seed at stack's near extreme
          }
          flippedThisBar = true;
        }
      }
    }

    for (const step of skipSteps ? [] : barSteps(c)) {
      if (step.side === "low") {
        if (this.dir === "down") {
          if (step.px < this.stampPx) {
            this.stampIdx = gIdx;
            this.stampK = k;
            this.stampT = t;
            this.stampPx = step.px;
          }
        } else if (step.px < this.prevLow) {
          // up-leg violated -> seal H stamp, flip down (dead pending dies too)
          this.pending = null;
          this.pushStamp();
          this.dir = "down";
          this.stampIdx = gIdx;
          this.stampK = k;
          this.stampT = t;
          this.stampPx = step.px;
          flippedThisBar = true;
        }
      } else {
        if (this.dir === "up") {
          if (step.px > this.stampPx) {
            this.stampIdx = gIdx;
            this.stampK = k;
            this.stampT = t;
            this.stampPx = step.px;
          }
        } else if (step.px > this.prevHigh) {
          // down-leg violated -> seal L stamp, flip up (dead pending dies too)
          this.pending = null;
          this.pushStamp();
          this.dir = "up";
          this.stampIdx = gIdx;
          this.stampK = k;
          this.stampT = t;
          this.stampPx = step.px;
          flippedThisBar = true;
        }
      }
    }

    // ---- inside-candle detection -> pending far-side extreme ----
    // (checked AFTER this bar resolves: an insider never marks itself;
    //  the NEXT bar's break decides confirm vs skip)
    if (
      !this.pending &&
      !flippedThisBar &&
      c.open !== c.close &&
      c.high <= this.prevHigh &&
      c.low >= this.prevLow
    ) {
      this.pending = {
        kind: this.dir === "down" ? "H" : "L",
        idx: gIdx,
        k,
        time: t,
        px: this.dir === "down" ? c.high : c.low,
        near: this.dir === "down" ? c.low : c.high,
        inner: [],
      };
    }

    void flippedThisBar;

    // running extremes since each side's last pushed pivot
    if (this.hiPx === null || c.high > this.hiPx) {
      this.hiPx = c.high;
      this.hiIdx = gIdx;
      this.hiK = k;
      this.hiT = t;
      this.hiCloseGreen = c.close >= c.open;
    }
    if (this.loPx === null || c.low < this.loPx) {
      this.loPx = c.low;
      this.loIdx = gIdx;
      this.loK = k;
      this.loT = t;
      this.loCloseRed = c.close < c.open;
    }

    this.prevHigh = c.high;
    this.prevLow = c.low;
    return this.barOut;
  }

  /** Trailing open swing (unsealed) – call once after the day ends. */
  finalize(): AlgoPivot | null {
    if (this.k < 0) return null;
    return {
      idx: this.stampIdx,
      time: this.stampT,
      kind: this.dir === "up" ? "H" : "L",
      px: this.stampPx,
      sealed: false,
    };
  }

  private emit(p: AlgoPivot) {
    this.barOut.push(p);
  }

  private trackBand(kind: "H" | "L", px: number) {
    if (kind === "H") {
      this.bandHigh = px;
      this.hiPx = null; // H finalized – highs restart accumulating toward next L
    } else {
      this.bandLow = px;
      this.loPx = null; // L finalized – lows restart accumulating toward next H
    }
  }

  private pushStamp() {
    this.emit({
      idx: this.stampIdx,
      time: this.stampT,
      kind: this.dir === "up" ? "H" : "L",
      px: this.stampPx,
      sealed: true,
    });
    this.trackBand(this.dir === "up" ? "H" : "L", this.stampPx);
  }

  // Close a resolved stack: append its final alternating layer record (only
  // when the stack actually peeled – single insiders contribute nothing) and
  // flush chronologically. Returns the last flushed record, or null.
  private closeStack(p: WPending): {
    idx: number;
    k: number;
    time: string;
    kind: "H" | "L";
    px: number;
  } | null {
    if (p.inner.length === 0) return null;
    // ROLE-BASED edges: pendPx is ALWAYS the far edge, pendNear the near
    // edge – regardless of which is numerically higher. (max/min here was a
    // latent pk=L bug: it silently swapped roles on up-leg stacks.)
    const wantFar = p.inner.length % 2 === 0;
    const rec: {
      idx: number;
      k: number;
      time: string;
      kind: "H" | "L";
      px: number;
    } = wantFar
      ? { idx: p.idx, k: p.k, time: p.time, kind: p.kind, px: p.px }
      : {
          idx: p.idx,
          k: p.k,
          time: p.time,
          kind: p.kind === "H" ? "L" : "H",
          px: p.near,
        };
    p.inner.push(rec);
    let last: {
      idx: number;
      k: number;
      time: string;
      kind: "H" | "L";
      px: number;
    } | null = null;
    while (p.inner.length > 0) {
      const ip = p.inner.shift()!;
      this.emit({
        idx: ip.idx,
        time: ip.time,
        kind: ip.kind,
        px: ip.px,
        sealed: true,
      });
      this.trackBand(ip.kind, ip.px);
      last = ip;
    }
    return last;
  }

  // Tie-break helpers for the confirm-override: original used
  // items[hiK].close >= items[hiK].open evaluated against the EXTREME BAR
  // itself; we capture that bit when the extreme updates.
  private hiCloseGreen = false;
  private loCloseRed = false;
}

type WPending = {
  k: number;
  kind: "H" | "L";
  idx: number;
  time: string;
  px: number; // far-side extreme (current STACK's far edge)
  near: number; // near-side extreme (current STACK's near edge)
  // Onion peel: alternating zigzag points contributed by each stack layer
  // (layer 1 = FAR edge, layer 2 = NEAR edge, layer 3 FAR again...),
  // flushed chronologically when the stack finally resolves.
  inner: {
    idx: number;
    k: number;
    time: string;
    kind: "H" | "L";
    px: number;
  }[];
};

function walkDay(items: { c: FlowCandle; gIdx: number }[]): AlgoPivot[] {
  if (items.length === 0) return [];
  const eng = new WalkerEngine();
  const all: AlgoPivot[] = [];
  for (const it of items) all.push(...eng.processBar(it.c, it.gIdx));
  const tail = eng.finalize();
  if (tail) all.push(tail);
  return enforceAlternation(dedupe(all));
}

// Zigzag law: cross-candle H,H / L,L can never render. Same-kind neighbours
// collapse into the more extreme mark (same-candle volatile pairs like
// "10:55 H + L" are different kinds and pass through untouched).
function enforceAlternation(pivots: AlgoPivot[]): AlgoPivot[] {
  const out: AlgoPivot[] = [];
  for (const p of pivots) {
    const last = out[out.length - 1];
    if (last && last.kind === p.kind) {
      const better = p.kind === "H" ? p.px > last.px : p.px < last.px;
      if (better) out[out.length - 1] = p;
      continue;
    }
    out.push(p);
  }
  return out;
}

function dedupe(pivots: AlgoPivot[]): AlgoPivot[] {
  const out: AlgoPivot[] = [];
  for (const p of pivots) {
    const last = out[out.length - 1];
    if (last && last.idx === p.idx && last.kind === p.kind && last.px === p.px)
      continue;
    out.push(p);
  }
  return out;
}

export function computeAlgoPivots(candles: FlowCandle[]): AlgoPivot[] {
  const byDay = new Map<string, { c: FlowCandle; gIdx: number }[]>();
  candles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const all: AlgoPivot[] = [];
  byDay.forEach((items) => {
    all.push(...walkDay(items));
  });
  return all;
}

// NOTE: the old FirstSwingEngine (fixed mPoints=20 point-distance trigger,
// plus a two-close rule) has been retired per the first-swing-detection
// rebuild spec – it predated FsV2Engine and used an unscaled fixed-point
// threshold. FsV2Engine below is now the only first-swing engine.
// >>> If anything outside this file still imports FirstSwingEngine or
// computeFirstSwingDeclared, repoint it at computeFsV2Declared /
// computeFsV2Results before shipping this change. <<<

// =====================================================================
// ?? FS v2 ENGINE – first-swing detection (1-min, walker-driven)
//
// Indefinite monitoring, no fallback tier (removed per user spec).
//   REAL – CONTINUATION   session extreme extends twice in a row, same
//                         direction (A/B open extremes, break?C, break?D)
//                         ? direction confirmed.
//   REAL – REVERSAL       one extreme breaks, then price reverses and
//                         breaks the OTHER original extreme – a single
//                         break is enough here ? direction confirmed.
//   (both REAL paths)     once direction is confirmed, wait for
//                         CHOP-BACK (a prior opposite pivot breaks) or
//                         7-BAR SUSTAIN (price holds past the broken
//                         level) to actually declare.
//   No fallback – if neither fires, engine keeps monitoring until EOD.
//   Nothing declares before `timeCap` (hard gate, not deferred).
//
// Live-safe: closed bars only; declared end never repaints.
// =====================================================================

export interface FsV2Opts {
  sustainBars?: number;
  simpleMode?: boolean;
  timeCap?: string; // nothing declares before this (default "09:29")
}

interface FsLevel {
  px: number;
  idx: number;
  time: string;
}

export class FsV2Engine {
  private walker = new WalkerEngine();
  private barsSeen = 0;

  // live session extremes (path-stamped – freshest candle wins)
  private eHi: FsLevel = { px: -Infinity, idx: -1, time: "" };
  private eLo: FsLevel = { px: Infinity, idx: -1, time: "" };
  // current EXTREME PIVOTS (walker-sealed; init from bar 0)
  private eHiPivot: FsLevel | null = null;
  private eLoPivot: FsLevel | null = null;

  // unbroken normal-pivot levels (one-time-use triggers)
  private normalHighs: FsLevel[] = [];
  private normalLows: FsLevel[] = [];

  dir: "up" | "down" | null = null;
  startIdx = -1;
  startTime = "";
  startPx = NaN;
  candIdx = -1;
  candTime = "";
  candPx = NaN;
  declared = false;
  tier: "real" | null = null;
  endTime = "";
  endIdx = -1;
  endPx = NaN;
  confirmedAtTime = "";
  confirmedAtIdx = -1;
  lastConfirmHit: {
    pool: string;
    px: number;
    idx: number;
    time: string;
  } | null = null;
  confirmSource: "chop" | "sustain" | null = null;
  breakMarks: {
    idx: number;
    time: string;
    kind: "B1" | "B2" | "FLIP";
    dir: "up" | "down";
    px: number;
  }[] = [];

  private timeCap = "09:29";

  // -- direction detection: same-side vs opposite-side breaks --
  private baseDir: "up" | "down" | null = null; // direction of first extreme break
  private sameSideBreaks = 0; // consecutive breaks in baseDir
  private oppositeSideBreaks = 0; // breaks opposite to baseDir
  private dirConfirmed = false; // direction confirmed by breaks
  private dirConfirmedIdx = -1;

  // -- single-E-break trigger --
  // After direction is set, ONE live cross of the current E-pivot level in
  // the swing direction TRIGGERS the swing (freezes the broken pivot level
  // as the sustain reference). After trigger, only chop or 7-bar sustain
  // can confirm (REAL tier). If neither ever fires, Fallback covers it –
  // there is no separate "invalidated" state.
  locked = false;

  // -- X) micro-top/lows: zero-lag local extremes (no walker seal needed) --
  private microHighs: FsLevel[] = [];
  private microLows: FsLevel[] = [];
  private pHigh = NaN;
  private pHighIdx = -1;
  private pHighT = ""; // previous bar high
  private ppHigh = NaN;
  private ppHighIdx = -1;
  private ppHighT = ""; // bar-before-that high
  private pLow = NaN;
  private pLowIdx = -1;
  private pLowT = "";
  private ppLow = NaN;
  private ppLowIdx = -1;
  private ppLowT = "";

  // -- Y) N-candle sustain beyond the broken extreme --
  private lockedLevelPx = NaN; // E-level that was crossed at lock (frozen)
  private sustainStreak = 0;
  private histH: number[] = []; // per-bar highs/lows for touch-seeding
  private histL: number[] = [];

  constructor(private opts: FsV2Opts = {}) {
    this.timeCap = this.opts.timeCap ?? "09:29";
  }

  processBar(c: FlowCandle, gIdx: number) {
    if (this.declared) return;
    this.barsSeen++;
    const t = c.date.slice(11, 16);
    const green = c.close >= c.open;

    if (this.barsSeen === 1) {
      this.eHi = { px: c.high, idx: gIdx, time: t };
      this.eLo = { px: c.low, idx: gIdx, time: t };
      this.eHiPivot = { ...this.eHi };
      this.eLoPivot = { ...this.eLo };
    }

    // ---- B) consume walker seals FIRST (records/pools/E-pivots only) ----
    // Direction is decided ONLY by the live E-break path below (block A) –
    // this block just maintains the sealed-pivot bookkeeping (eHiPivot/
    // eLoPivot reference levels, and the normalHighs/normalLows pools used
    // later by chop-break confirmation). It used to ALSO call initiate()
    // independently whenever a walker-sealed pivot extended – a second,
    // laggier trigger for direction that could silently reset progress the
    // live path had already made. Removed: one source of truth for
    // direction now, per the rebuild spec.
    for (const p of this.walker.processBar(c, gIdx)) {
      if (!p.sealed) continue;
      if (p.kind === "H") {
        const cur = this.eHiPivot!;
        if (p.px > cur.px) {
          // NEW EXTREME-HIGH PIVOT – demote old to normals (only true extremes, not every small high)
          this.normalHighs.push(cur);
          this.eHiPivot = { px: p.px, idx: p.idx, time: p.time };
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
        } else {
          this.pushUnique(this.normalLows, {
            px: p.px,
            idx: p.idx,
            time: p.time,
          });
        }
      }
    }

    // Invalidate swing if opposite extreme breaks the start before declaration (e.g., up swing low broken by 09:29)
    if (this.dirConfirmed && this.dir && !this.declared && this.startIdx >= 0) {
      if (this.dir === "up" && this.eLo.px < this.startPx) {
        this.dir = null;
        this.locked = false;
        this.dirConfirmed = false;
        this.dirConfirmedIdx = -1;
        this.baseDir = null;
        this.sameSideBreaks = 0;
        this.oppositeSideBreaks = 0;
        this.sustainStreak = 0;
        this.lockedLevelPx = NaN;
        this.microHighs.length = 0;
        this.microLows.length = 0;
        this.startIdx = -1;
        this.startTime = "";
        this.startPx = NaN;
        this.candIdx = -1;
        this.candTime = "";
        this.candPx = NaN;
      } else if (this.dir === "down" && this.eHi.px > this.startPx) {
        this.dir = null;
        this.locked = false;
        this.dirConfirmed = false;
        this.dirConfirmedIdx = -1;
        this.baseDir = null;
        this.sameSideBreaks = 0;
        this.oppositeSideBreaks = 0;
        this.sustainStreak = 0;
        this.lockedLevelPx = NaN;
        this.microHighs.length = 0;
        this.microLows.length = 0;
        this.startIdx = -1;
        this.startTime = "";
        this.startPx = NaN;
        this.candIdx = -1;
        this.candTime = "";
        this.candPx = NaN;
      }
    }

    // ---- A) live path steps: stamps, final trigger ----
    // Capture extremes BEFORE halves loop – if they update this bar, a new
    // extreme was printed and the sustain streak should NOT count this bar
    // (the "hold" is measured AFTER the extreme is final, not during it).
    const eLoBefore = this.eLo.px;
    const eHiBefore = this.eHi.px;

    // ---- X) micro local-extremes: completed 2-side pivots, zero seal-lag ----
    // Bar k-1 was a LOCAL TOP/BOTTOM if its extreme beat previous bar and is confirmed by next bar.
    // Classic: next bar lower high (c.high < pHigh) for tops, higher low for bottoms.
    // Immediate-break: next bar breaks opposite side (c.low < pLow for tops) still counts as pivot
    // (fixes 20 July 12:51->12:52 where 12:52 immediately breaks 12:51).
    // Guarded by dirConfirmed so chop cannot fire before direction is set.
    if (
      this.dirConfirmed &&
      this.dir &&
      this.barsSeen >= 3 &&
      Number.isFinite(this.ppHigh)
    ) {
      const topFormed =
        this.pHigh > this.ppHigh && (c.high < this.pHigh || c.low < this.pLow);
      const botFormed =
        this.pLow < this.ppLow && (c.low > this.pLow || c.high > this.pHigh);
      if (topFormed && this.pHighIdx > this.startIdx) {
        this.pushUnique(this.microHighs, {
          px: this.pHigh,
          idx: this.pHighIdx,
          time: this.pHighT,
        });
      }
      if (botFormed && this.pLowIdx > this.startIdx) {
        this.pushUnique(this.microLows, {
          px: this.pLow,
          idx: this.pLowIdx,
          time: this.pLowT,
        });
      }
    }

    this.histH.push(c.high);
    this.histL.push(c.low);

    const halves: [number, boolean][] = green
      ? [
          [c.low, true],
          [c.high, false],
        ]
      : [
          [c.high, true],
          [c.low, false],
        ];
    for (const [px, isLow] of halves) {
      if (this.declared) break;

      // live extreme stamps – always update, even before timeCap
      if (px > this.eHi.px) {
        this.eHi = { px, idx: gIdx, time: t };
        if (this.dir === "up") this.setCand(this.eHi);
      }
      if (px < this.eLo.px) {
        this.eLo = { px, idx: gIdx, time: t };
        if (this.dir === "down") this.setCand(this.eLo);
      }

      // nothing else (lock / dirConfirm / chop) before timeCap
      if (t < this.timeCap) continue;

      // direction detection: count same-side and opposite-side breaks
      // Only count NEW extreme breaks (lower than previous eLo / higher than previous eHi)
      // Any break > / < counts, no point threshold
      if (this.dirConfirmed) {
      } else if (this.locked || this.dir) {
        const eLoLvl = this.eLoPivot ? this.eLoPivot.px : this.eLo.px;
        const eHiLvl = this.eHiPivot ? this.eHiPivot.px : this.eHi.px;
        if (this.baseDir === "down" && px < eLoLvl && px < eLoBefore) {
          this.sameSideBreaks++;
          if (this.sameSideBreaks >= 2) {
            this.dirConfirmed = true;
            this.dirConfirmedIdx = gIdx;
            this.lockedLevelPx = px;
          }
        } else if (this.baseDir === "up" && px > eHiLvl && px > eHiBefore) {
          this.sameSideBreaks++;
          if (this.sameSideBreaks >= 2) {
            this.dirConfirmed = true;
            this.dirConfirmedIdx = gIdx;
            this.lockedLevelPx = px;
          }
        } else if (this.baseDir === "down" && px > eHiLvl && px > eHiBefore) {
          this.oppositeSideBreaks = 1;
          this.dir = "up";
          this.dirConfirmed = true;
          this.dirConfirmedIdx = gIdx;
          this.lockedLevelPx = eHiLvl; // reversal: sustain must reference the level that flipped it
        } else if (this.baseDir === "up" && px < eLoLvl && px < eLoBefore) {
          this.oppositeSideBreaks = 1;
          this.dir = "down";
          this.dirConfirmed = true;
          this.dirConfirmedIdx = gIdx;
          this.lockedLevelPx = eLoLvl; // reversal: sustain must reference the level that flipped it
        }
      }

      // -- v3 fast-path: single E-break LOCK + opposite-break INVALIDATION --
      if (!this.locked) {
        const eLoLvl = this.eLoPivot ? this.eLoPivot.px : this.eLo.px;
        const eHiLvl = this.eHiPivot ? this.eHiPivot.px : this.eHi.px;
        const downBreak = this.dir === "down" && px < eLoLvl;
        const upBreak = this.dir === "up" && px > eHiLvl;
        const firstBreakDown = !this.dir && px < eLoLvl;
        const firstBreakUp = !this.dir && px > eHiLvl;
        const firstBreak = firstBreakDown || firstBreakUp;

        if (downBreak || firstBreakDown) {
          this.locked = true;
          this.lockedLevelPx = eLoLvl;
          this.setCand(this.eLo);
          if (!this.dir) {
            this.dir = "down";
            this.initiate("down", t);
            this.baseDir = "down";
            this.sameSideBreaks = 1;
            this.breakMarks.push({
              idx: gIdx,
              time: t,
              kind: "B1",
              dir: "down",
              px,
            });
          } else if (this.baseDir === "down") {
            this.sameSideBreaks++;
            if (this.sameSideBreaks >= 2) {
              this.dirConfirmed = true;
              this.dirConfirmedIdx = gIdx;
              this.lockedLevelPx = px;
              this.breakMarks.push({
                idx: gIdx,
                time: t,
                kind: "B2",
                dir: "down",
                px,
              });
            }
          } else {
            this.oppositeSideBreaks = 1;
            this.dir = "up";
            this.dirConfirmed = true;
            this.dirConfirmedIdx = gIdx;
            this.breakMarks.push({
              idx: gIdx,
              time: t,
              kind: "FLIP",
              dir: "up",
              px,
            });
          }
        } else if (upBreak || firstBreakUp) {
          this.locked = true;
          this.lockedLevelPx = eHiLvl;
          this.setCand(this.eHi);
          if (!this.dir) {
            this.dir = "up";
            this.initiate("up", t);
            this.baseDir = "up";
            this.sameSideBreaks = 1;
            this.breakMarks.push({
              idx: gIdx,
              time: t,
              kind: "B1",
              dir: "up",
              px,
            });
          } else if (this.baseDir === "up") {
            this.sameSideBreaks++;
            if (this.sameSideBreaks >= 2) {
              this.dirConfirmed = true;
              this.dirConfirmedIdx = gIdx;
              this.lockedLevelPx = px;
              this.breakMarks.push({
                idx: gIdx,
                time: t,
                kind: "B2",
                dir: "up",
                px,
              });
            }
          } else {
            this.oppositeSideBreaks = 1;
            this.dir = "down";
            this.dirConfirmed = true;
            this.dirConfirmedIdx = gIdx;
            this.breakMarks.push({
              idx: gIdx,
              time: t,
              kind: "FLIP",
              dir: "down",
              px,
            });
          }
        }
      }

      // CHOP-BREAK: after direction confirmed, break of the *most recent* opposite pivot = chop.
      // For shorts we break the latest high pivot (normal or micro) after start; for longs the latest low.
      // Any > / < counts, no point threshold. Allow immediate next-bar break for highs (12:51->12:52)
      // but require 1 bar gap for lows to avoid tiny 09:35->09:36 wiggle.
      if (this.dirConfirmed && this.dir && this.startIdx >= 0) {
        if (this.dir === "down") {
          const normalCands = this.normalHighs.filter(
            (l) => l.idx > this.startIdx && l.idx + 1 < gIdx,
          );
          if (normalCands.length > 0) {
            const target = normalCands.reduce(
              (a, b) => (b.idx > a.idx ? b : a),
              normalCands[0],
            );
            if (px > target.px) {
              this.lastConfirmHit = {
                pool: "normal",
                px: target.px,
                idx: target.idx,
                time: target.time,
              };
              this.confirmSource = "chop";
              this.confirm(gIdx, t);
              return;
            }
          }
          const microCands = this.microHighs.filter(
            (l) => l.idx > this.startIdx && l.idx + 1 < gIdx,
          );
          if (microCands.length > 0) {
            const target = microCands.reduce(
              (a, b) => (b.idx > a.idx ? b : a),
              microCands[0],
            );
            if (px > target.px) {
              this.lastConfirmHit = {
                pool: "micro",
                px: target.px,
                idx: target.idx,
                time: target.time,
              };
              this.confirmSource = "chop";
              this.confirm(gIdx, t);
              return;
            }
          }
        } else {
          const normalCands = this.normalLows.filter(
            (l) => l.idx > this.startIdx && l.idx + 1 < gIdx,
          );
          if (normalCands.length > 0) {
            const target = normalCands.reduce(
              (a, b) => (b.idx > a.idx ? b : a),
              normalCands[0],
            );
            if (px < target.px) {
              this.lastConfirmHit = {
                pool: "normal",
                px: target.px,
                idx: target.idx,
                time: target.time,
              };
              this.confirmSource = "chop";
              this.confirm(gIdx, t);
              return;
            }
          }
          const microCands = this.microLows.filter(
            (l) => l.idx > this.startIdx && l.idx + 1 < gIdx,
          );
          if (microCands.length > 0) {
            const target = microCands.reduce(
              (a, b) => (b.idx > a.idx ? b : a),
              microCands[0],
            );
            if (px < target.px) {
              this.lastConfirmHit = {
                pool: "micro",
                px: target.px,
                idx: target.idx,
                time: target.time,
              };
              this.confirmSource = "chop";
              this.confirm(gIdx, t);
              return;
            }
          }
        }
      }
    }

    // ---- Y) N-candle sustain beyond the broken extreme (bar-level) ----
    if (t < this.timeCap) {
      this.sustainStreak = 0;
    } else if (this.dirConfirmed && this.dir && !this.declared) {
      const n = this.opts.sustainBars ?? 7;
      const ref = this.lockedLevelPx;
      const madeNewExtreme =
        this.dir === "down" ? this.eLo.px < eLoBefore : this.eHi.px > eHiBefore;
      if (madeNewExtreme) {
        this.sustainStreak = 0;
      } else {
        this.sustainStreak =
          this.dir === "down"
            ? c.close < ref
              ? this.sustainStreak + 1
              : 0
            : c.close > ref
              ? this.sustainStreak + 1
              : 0;
      }
      if (this.sustainStreak >= n) {
        this.confirmSource = "sustain";
        this.confirm(gIdx, t);
        return;
      }
    } else {
      this.sustainStreak = 0;
    }

    // shift micro history for next bar (local extreme detection uses prev 2 bars)
    this.ppHigh = this.pHigh;
    this.ppHighIdx = this.pHighIdx;
    this.ppHighT = this.pHighT;
    this.pHigh = c.high;
    this.pHighIdx = gIdx;
    this.pHighT = t;
    this.ppLow = this.pLow;
    this.ppLowIdx = this.pLowIdx;
    this.ppLowT = this.pLowT;
    this.pLow = c.low;
    this.pLowIdx = gIdx;
    this.pLowT = t;
  }

  debugPools() {
    return {
      startIdx: this.startIdx,
      startPx: this.startPx,
      lockedLevelPx: this.lockedLevelPx,
      lastConfirmHit: this.lastConfirmHit,
      normalHighs: this.normalHighs.map((l) => l.time + "@" + l.px.toFixed(2)),
      microHighs: this.microHighs.map((l) => l.time + "@" + l.px.toFixed(2)),
    };
  }

  private initiate(dir: "up" | "down", t: string) {
    this.dir = dir;
    this.microHighs.length = 0;
    this.microLows.length = 0;
    this.sustainStreak = 0;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.oppositeSideBreaks = 0;
    this.dirConfirmed = false;
    this.dirConfirmedIdx = -1;
    // swing start = the counter-extreme at initiation moment
    const s = dir === "up" ? this.eLo : this.eHi;
    this.startIdx = s.idx;
    this.startTime = s.time;
    this.startPx = s.px;
    this.setCand(dir === "up" ? this.eHi : this.eLo);
    void t;
  }

  private setCand(l: FsLevel) {
    this.candIdx = l.idx;
    this.candTime = l.time;
    this.candPx = l.px;
  }

  private pushUnique(pool: FsLevel[], l: FsLevel) {
    if (!pool.some((x) => x.idx === l.idx && x.px === l.px)) pool.push(l);
  }

  private confirm(gIdx: number, t: string) {
    // hard timeCap – nothing declares before timeCap, not deferred
    if (t < this.timeCap) return;
    this.declared = true;
    this.tier = "real";
    this.endIdx = this.candIdx;
    this.endTime = this.candTime;
    this.endPx = this.candPx;
    this.confirmedAtTime = t;
    this.confirmedAtIdx = gIdx;
  }

  /** Re-initialize the engine to detect a new swing starting from a pre-defined
   *  price level (e.g., the first swing's extreme).
   *
   *  After reset, the next processBar increments barsSeen to 2, skipping the
   *  barsSeen==1 initialization – the seed bar is already set. */
  reset(seedPx: number, seedIdx: number, seedTime: string) {
    // Fresh walker (pivot history not shared with previous swing)
    this.walker = new WalkerEngine();

    // Fake barsSeen=1 state so next processBar goes to barsSeen=2
    this.barsSeen = 1;
    // t/green/g_idx are internal; just set the seed time for timeCap check
    void seedTime; // consumed below

    // Seed extremes – these are the "session start" for second-swing detection
    this.eHi = { px: seedPx, idx: seedIdx, time: seedTime };
    this.eLo = { px: seedPx, idx: seedIdx, time: seedTime };
    this.eHiPivot = { px: seedPx, idx: seedIdx, time: seedTime };
    this.eLoPivot = { px: seedPx, idx: seedIdx, time: seedTime };

    // Zero all direction/state
    this.dir = null;
    this.baseDir = null;
    this.sameSideBreaks = 0;
    this.oppositeSideBreaks = 0;
    this.dirConfirmed = false;
    this.dirConfirmedIdx = -1;
    this.locked = false;
    this.lockedLevelPx = NaN;

    // Zero swing start/candidate
    this.startIdx = -1;
    this.startTime = "";
    this.startPx = NaN;
    this.candIdx = -1;
    this.candTime = "";
    this.candPx = NaN;

    // Zero declaration
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

    // Clear pools
    this.normalHighs.length = 0;
    this.normalLows.length = 0;
    this.microHighs.length = 0;
    this.microLows.length = 0;
    this.histH.length = 0;
    this.histL.length = 0;
    this.breakMarks.length = 0;
  }
}

// -- Second Swing Detection ----------------------------------------------------

/** Mirror of the backend's detectSecondSwing() – runs a fresh FsV2 engine
 *  seeded from the first-swing's end-point, feeding bars AFTER that endpoint.
 *
 *  Returns one FsV2Result per day (or null for days with no first swing). */
export interface SecondSwingDetail extends FsV2Result {
  fs1Dir: "up" | "down" | null;
}

export function computeSecondSwingResults(
  sourceCandles: FlowCandle[],
  fs1Results: FsV2Result[],
  opts: FsV2Opts = {},
): SecondSwingDetail[] {
  // Build a fast lookup: day -> fs1 result
  const fs1ByDay = new Map<string, FsV2Result>();
  for (const r of fs1Results) {
    if (r.seg !== null) fs1ByDay.set(r.day, r);
  }

  // Group candles by day
  const byDay = new Map<string, { c: FlowCandle; gIdx: number }[]>();
  sourceCandles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const out: SecondSwingDetail[] = [];

  byDay.forEach((items, day) => {
    const fs1 = fs1ByDay.get(day);
    if (!fs1 || fs1.seg === null || fs1.confIdx < 0) return;

    // SECOND SWING: start from 09:28 as new 09:15 – give ALL OHLC from 09:28
    // to the first-swing engine exactly as you said: "from 9:28 give all the
    // ohlc value to first swing engine". This is a fresh engine fed from 09:28
    // inclusive, so 09:28 nothing, 09:29 nothing (arm), 09:30 B1 breaking 09:29
    // low, 09:36 B2 breaking 09:31 low – your 09:30/09:36.
    const seedIdx = fs1.seg!.endIdx + 1;
    const afterFs1 = items.filter((it) => it.gIdx >= seedIdx);
    if (afterFs1.length === 0) return;

    const eng = new SwingEngine(opts);
    // No reset – just feed from 09:28 as bar 1, exactly like 09:15 for 1st swing.
    // This gives B1@09:30, B2@09:36 per your observation.

    for (const it of afterFs1) eng.processBar(it.c, it.gIdx);

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
      fs1Dir: fs1.dir,
    });
  });

  return out;
}

// Batch helper: replay each day through FsV2 (identical to live path).
// Outcome is now only "real" (declared) or "none" (still monitoring / EOD no-call).
// Fallback tier removed – engine keeps monitoring until chop/sustain fires.
export interface FsV2Result {
  day: string;
  outcome: "real" | "none";
  confIdx: number; // global candle index of the CONFIRM bar (-1 if none)
  seg: FlowSegment | null;
  source: "chop" | "sustain" | null;
  dir: "up" | "down" | null;
  // Direction-building break markers (B1 = first A/B break ? lock,
  // B2 = fresh-extreme extension ? confirm, FLIP = opposite extreme ? confirm).
  breaks?: FsBreakMark[];
}

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
    const eng = new SwingEngine(opts);
    for (const it of items) eng.processBar(it.c, it.gIdx);

    if (!eng.declared || eng.startIdx < 0) {
      // still monitoring or no swing by EOD – explicit none
      // For backward compat, emit none only if day fully processed; callers filtering seg!=null will ignore.
      if (eng.declared) return;
      // emit none for completeness if you need it, else return empty – keeping legacy: no segment.
      // To preserve explicit none, uncomment below:
      // out.push({ day, outcome: "none", confIdx: -1, seg: null, source: null, dir: null });
      return;
    }
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

// Backward-compatible wrapper: declared segments only (real),
// dropping explicit "none" no-call days.
export function computeFsV2Declared(
  candles: FlowCandle[],
  opts: FsV2Opts = {},
): FlowSegment[] {
  return computeFsV2Results(candles, opts)
    .filter((r): r is FsV2Result & { seg: FlowSegment } => r.seg !== null)
    .map((r) => r.seg);
}

// ===== ? ALGO FLOW LINE =====
export function computeAlgoFlowLine(candles: FlowCandle[]): FlowSegment[] {
  // Each day is walked and chained SEPARATELY – no line ever connects
  // one day's last pivot to the next day's first pivot.
  const byDay = new Map<string, { c: FlowCandle; gIdx: number }[]>();
  candles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const segs: FlowSegment[] = [];
  byDay.forEach((items) => {
    const pivots = walkDay(items);
    for (let i = 0; i + 1 < pivots.length; i++) {
      const a = pivots[i];
      const b = pivots[i + 1];
      segs.push({
        dir: b.px >= a.px ? "B" : "S",
        startIdx: a.idx,
        startPx: a.px,
        endIdx: b.idx,
        endPx: b.px,
      });
    }
  });
  return segs;
}
