// Flow-Line – Algo walker + FsV2 (white line only, orange manual line removed):

// Walker only — first-swing now lives in Python backend (POST /api/swings/first_second).
// flowline.ts keeps only WalkerEngine + white flowline for visual debug.

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
