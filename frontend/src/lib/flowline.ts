// Flow-Line — TWO SYSTEMS side-by-side (permanent identity):
//
//   🟠 ORANGE = computeFlowLine()     → MANUAL_PIVOTS (hardcoded ground truth)
//   ⚪ WHITE  = computeAlgoFlowLine() → ALGO walker (zero hardcoding)
//
// Orange is ALWAYS the manual line. White is ALWAYS the algo. Never swap.
// Naya date mark karna ho toh MANUAL_PIVOTS mein rows jodo.

// ── branch coverage instrumentation (active only with FLOW_COV=1) ────────
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

interface FlowCandle {
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

// ===== GROUND TRUTH: user-defined manual pivots =====
const MANUAL_PIVOTS: Record<string, { time: string; kind: "H" | "L" }[]> = {
  "2026-08-20": [
    { time: "09:15", kind: "H" },
    { time: "09:20", kind: "L" },
    { time: "09:25", kind: "H" },
    { time: "09:30", kind: "L" },
    { time: "09:45", kind: "H" },
    { time: "09:50", kind: "L" },
    { time: "09:55", kind: "H" },
    { time: "10:00", kind: "L" },
    { time: "10:15", kind: "H" },
    { time: "10:25", kind: "L" },
    { time: "10:30", kind: "H" },
    { time: "10:35", kind: "L" },
    { time: "10:45", kind: "H" },
    { time: "10:55", kind: "L" },
    { time: "11:00", kind: "H" },
    { time: "11:20", kind: "L" },
    { time: "11:30", kind: "H" },
    { time: "11:40", kind: "L" },
    { time: "11:45", kind: "H" },
    { time: "11:55", kind: "L" },
    { time: "11:55", kind: "H" },
    { time: "12:05", kind: "L" },
    { time: "12:15", kind: "H" },
    { time: "12:25", kind: "L" },
    { time: "12:30", kind: "H" },
    { time: "12:35", kind: "L" },
    { time: "12:50", kind: "H" },
    { time: "12:55", kind: "L" },
    { time: "13:00", kind: "H" },
    { time: "13:05", kind: "L" },
    { time: "13:10", kind: "H" },
    { time: "13:15", kind: "L" },
  ],
  "2026-08-21": [
    { time: "09:15", kind: "H" },
    { time: "09:20", kind: "L" },
    { time: "09:25", kind: "H" },
    { time: "09:30", kind: "L" },
    { time: "09:50", kind: "H" },
    { time: "09:55", kind: "L" },
    { time: "10:00", kind: "H" },
    { time: "10:10", kind: "L" },
    { time: "10:15", kind: "H" },
    { time: "10:20", kind: "L" },
    { time: "10:30", kind: "H" },
    { time: "10:35", kind: "L" },
    { time: "10:55", kind: "H" },
    { time: "10:55", kind: "L" },
    { time: "11:05", kind: "H" },
    { time: "11:10", kind: "L" },
    { time: "11:15", kind: "H" },
    { time: "11:20", kind: "L" },
    { time: "11:30", kind: "H" },
    { time: "11:45", kind: "L" },
    { time: "11:50", kind: "H" },
    { time: "12:15", kind: "L" },
    { time: "12:20", kind: "H" },
    { time: "12:25", kind: "L" },
    { time: "12:35", kind: "H" },
    { time: "12:40", kind: "L" },
    { time: "12:45", kind: "H" },
    { time: "12:55", kind: "L" },
    { time: "13:05", kind: "H" },
    { time: "13:20", kind: "L" },
    { time: "13:30", kind: "H" },
  ],
};

// ===== 🟠 MANUAL FLOW LINE (ground truth) =====
export function computeFlowLine(candles: FlowCandle[]): FlowSegment[] {
  const byDay = new Map<string, { c: FlowCandle; gIdx: number }[]>();
  candles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const segs: FlowSegment[] = [];
  byDay.forEach((items, dayKey) => {
    const marks = MANUAL_PIVOTS[dayKey];
    if (!marks) return; // unmarked days -> no orange line

    const pts: { idx: number; px: number }[] = [];
    for (const m of marks) {
      const item = items.find((it) => it.c.date.slice(11, 16) === m.time);
      if (!item) continue;
      pts.push({
        idx: item.gIdx,
        px: m.kind === "H" ? item.c.high : item.c.low,
      });
    }

    for (let i = 0; i + 1 < pts.length; i++) {
      const a = pts[i];
      const b = pts[i + 1];
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

// =====================================================================
// ⚪ ALGO WALKER — color-aware candle path follower
//
// Rules (course S6 + user spec):
//   - GREEN candle path: LOW prints first → HIGH   (bottom-to-top)
//   - RED candle path: HIGH prints first → LOW     (top-to-bottom)
//   - Each bar processed as TWO half-steps in that order.
//   - Active leg tracks a running extreme ("stamp"). Same-direction breaks
//     SHIFT the stamp (extended leg = no new pivot). An opposite-side break
//     of the PREVIOUS bar's extreme SEALS the stamp as a pivot and flips.
//   - INSIDE candle: range within prev bar → its far-side extreme becomes a
//     PENDING pivot. Next bar resolves:
//       breaks near side  -> confirm (push pending), leg continues
//       breaks far side   -> SKIP insider (discard), seal stamp, flip leg
//   - Live-safe: only closed bars consumed; pending resolves on next close.
// =====================================================================

type Step = { side: "low" | "high"; px: number };

function barSteps(c: FlowCandle): Step[] {
  const green = c.close >= c.open;
  return green
    ? [{ side: "low", px: c.low }, { side: "high", px: c.high }]
    : [{ side: "high", px: c.high }, { side: "low", px: c.low }];
}

// Steppable walker — EXACT state-machine translation of the original
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
        this.hiPx = c.high; this.hiIdx = gIdx; this.hiK = 0; this.hiT = t;
        this.hiCloseGreen = true;
      } else {
        this.bandHigh = c.high;
        this.hiPx = null;
        this.loPx = c.low; this.loIdx = gIdx; this.loK = 0; this.loT = t;
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
        // ROLE-BASED (see closeStack) — pendPx = far edge BY DEFINITION.
        const wantFar = pend.inner.length % 2 === 0;
        cov((wantFar ? "onion:FAR-layer:pk" : "onion:NEAR-layer:pk") + pk);
        pend.inner.push(
          wantFar
            ? { idx: pend.idx, k: pend.k, time: pend.time, kind: pk, px: pend.px }
            : { idx: pend.idx, k: pend.k, time: pend.time,
                kind: pk === "H" ? "L" : "H", px: pend.near },
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
          // CONFIRM — seal pre-insider swing; a PEELED stack emits its
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
              const hiAfter = this.hiK > this.stampK || (this.hiK === this.stampK && this.hiCloseGreen);
              if (hiAfter) {
                pIdx = this.hiIdx;
                pT = this.hiT;
                pPx = this.hiPx;
                pK = this.hiK;
              }
            }
            if (pk === "L" && this.loPx !== null && this.loPx < pPx) {
              const loAfter = this.loK > this.stampK || (this.loK === this.stampK && this.loCloseRed);
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
          // DOUBLE-BREAK (volatile candle) — marker-band decides.
          // Band = [active low marker, active high marker]; the ACTIVE leg's
          // running stamp IS its side's live marker.
          const iLo = Math.min(pend.px, pend.near); // stack low
          const iHi = Math.max(pend.px, pend.near); // stack high
          const effLo = this.dir === "down" ? this.stampPx : this.bandLow ?? Number.NEGATIVE_INFINITY;
          const effHi = this.dir === "up" ? this.stampPx : this.bandHigh ?? Number.POSITIVE_INFINITY;
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
            skipSteps = true; // bar consumed — its halves already priced in
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
              this.emit({ idx: p.idx, time: p.time, kind: pk, px: p.px, sealed: true });
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
    if (!this.pending && !flippedThisBar && c.open !== c.close && c.high <= this.prevHigh && c.low >= this.prevLow) {
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

  /** Trailing open swing (unsealed) — call once after the day ends. */
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
      this.hiPx = null; // H finalized — highs restart accumulating toward next L
    } else {
      this.bandLow = px;
      this.loPx = null; // L finalized — lows restart accumulating toward next H
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
  // when the stack actually peeled — single insiders contribute nothing) and
  // flush chronologically. Returns the last flushed record, or null.
  private closeStack(p: WPending): { idx: number; k: number; time: string; kind: "H" | "L"; px: number } | null {
    if (p.inner.length === 0) return null;
    // ROLE-BASED edges: pendPx is ALWAYS the far edge, pendNear the near
    // edge — regardless of which is numerically higher. (max/min here was a
    // latent pk=L bug: it silently swapped roles on up-leg stacks.)
    const wantFar = p.inner.length % 2 === 0;
    const rec: { idx: number; k: number; time: string; kind: "H" | "L"; px: number } = wantFar
      ? { idx: p.idx, k: p.k, time: p.time, kind: p.kind, px: p.px }
      : { idx: p.idx, k: p.k, time: p.time, kind: p.kind === "H" ? "L" : "H", px: p.near };
    p.inner.push(rec);
    let last: { idx: number; k: number; time: string; kind: "H" | "L"; px: number } | null = null;
    while (p.inner.length > 0) {
      const ip = p.inner.shift()!;
      this.emit({ idx: ip.idx, time: ip.time, kind: ip.kind, px: ip.px, sealed: true });
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
  inner: { idx: number; k: number; time: string; kind: "H" | "L"; px: number }[];
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
    if (last && last.idx === p.idx && last.kind === p.kind && last.px === p.px) continue;
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

// ===== 🟡 FIRST SWING ENGINE (live-safe state machine) =====
// Same contract as the flow-line walker:
//   - processBar() consumes CLOSED candles only — zero hindsight
//   - color-aware half-steps (green: L→H · red: H→L)
//   - candidate end rides bar-by-bar while tracking (the live question)
//   - declared END freezes forever — sealed, never repaints
//
// Phases:
//   LOCK   : direction declares when a half-step breaks ALL-prior-bars'
//            opposite extreme. Start = the running counter-extreme so far
//            (data: 88% of swings start at the 09:15 bar itself).
//   TRACK  : running extreme E extends in direction (candidate end).
//   DECLARE: first trigger to fire freezes E as THE end:
//     T-A  counter-move ≥ mPoints from candidate (path-ordered half-step)
//     T-B  two consecutive closes against the move ("2-candle behaviour")

export interface FirstSwingOpts {
  mPoints?: number; // T-A trigger distance in points (default 20)
  twoClose?: boolean; // enable T-B (default true)
}

export class FirstSwingEngine {
  private barsSeen = 0;
  private prevClose: number | null = null;
  private refHi = -Infinity; // all-prior-bars high (lock reference)
  private refLo = Infinity; // all-prior-bars low
  private hiIdx = -1; private hiT = ""; private hiPx = -Infinity;
  private loIdx = -1; private loT = ""; private loPx = Infinity;

  locked = false;
  dir: "up" | "down" | null = null;
  startIdx = -1; startTime = ""; startPx = NaN;
  candIdx = -1; candTime = ""; candPx = NaN;
  declared = false;
  endTime = ""; endPx = NaN; endIdx = -1; declaredAtTime = "";

  constructor(
    private mPoints = 20,
    private twoClose = true,
  ) {}

  get phase(): "locking" | "tracking" | "declared" {
    return this.declared ? "declared" : this.locked ? "tracking" : "locking";
  }

  private declare(gIdx: number, t: string) {
    this.declared = true;
    this.endIdx = this.candIdx;
    this.endTime = this.candTime;
    this.endPx = this.candPx;
    this.declaredAtTime = t;
    void gIdx;
  }

  processBar(c: FlowCandle, gIdx: number) {
    if (this.declared) return;
    const green = c.close >= c.open;
    const t = c.date.slice(11, 16);
    this.barsSeen++;


    const halves: [number, boolean][] = green
      ? [[c.low, true], [c.high, false]]
      : [[c.high, true], [c.low, false]];
    // flag meaning here: true = LOW-side step, false = HIGH-side step

    for (const [px, isLow] of halves) {
      if (!this.locked) {
        // maintain running stamped extremes
        if (px > this.hiPx) { this.hiPx = px; this.hiIdx = gIdx; this.hiT = t; }
        if (px < this.loPx) { this.loPx = px; this.loIdx = gIdx; this.loT = t; }

        if (this.barsSeen > 1) {
          if (!isLow && px > this.refHi) {
            // UP-LOCK: broke every prior high → swing = run-up from lowest low
            this.locked = true;
            this.dir = "up";
            this.startIdx = this.loIdx; this.startTime = this.loT; this.startPx = this.loPx;
            this.candIdx = gIdx; this.candTime = t; this.candPx = px;
          } else if (isLow && px < this.refLo) {
            // DOWN-LOCK: broke every prior low → swing = slide from highest high
            this.locked = true;
            this.dir = "down";
            this.startIdx = this.hiIdx; this.startTime = this.hiT; this.startPx = this.hiPx;
            this.candIdx = gIdx; this.candTime = t; this.candPx = px;
          }
        }
        if (!this.locked) continue;
        // just locked THIS step → fall through so the bar's remaining
        // half-step(s) immediately get tracking treatment (T-A can even
        // fire on the same bar)
      }

      if (this.declared) break;

      // ---- TRACK / DECLARE (path-ordered) ----
      if (this.dir === "up") {
        if (isLow) {
          if (this.candPx - px >= this.mPoints) { this.declare(gIdx, t); return; }
        } else if (px > this.candPx) {
          this.candIdx = gIdx; this.candTime = t; this.candPx = px;
        }
      } else {
        if (!isLow) {
          if (px - this.candPx >= this.mPoints) { this.declare(gIdx, t); return; }
        } else if (px < this.candPx) {
          this.candIdx = gIdx; this.candTime = t; this.candPx = px;
        }
      }
    }

    // T-B: two consecutive closes against the move (closed-bar info)
    if (!this.declared && this.twoClose && this.prevClose !== null && this.locked) {
      if (this.dir === "up") {
        this.lowerStreak = c.close < this.prevClose ? this.lowerStreak + 1 : 0;
        if (this.lowerStreak >= 2) this.declare(gIdx, t);
      } else {
        this.higherStreak = c.close > this.prevClose ? this.higherStreak + 1 : 0;
        if (this.higherStreak >= 2) this.declare(gIdx, t);
      }
    }

    // roll references AFTER the bar completes
    if (!this.locked) {
      this.refHi = Math.max(this.refHi === -Infinity ? c.high : Math.max(this.refHi, c.high), c.high);
      this.refLo = Math.min(this.refLo === Infinity ? c.low : Math.min(this.refLo, c.low), c.low);
    }
    this.prevClose = c.close;
  }

  private lowerStreak = 0;
  private higherStreak = 0;
}

// Batch helper (offline/chart): replay each day through a fresh engine and
// emit start→declared-end segments. IDENTICAL path to live processing.
export function computeFirstSwingDeclared(
  candles: FlowCandle[],
  opts: FirstSwingOpts = {},
): FlowSegment[] {
  const byDay = new Map<string, { c: FlowCandle; gIdx: number }[]>();
  candles.forEach((c, gIdx) => {
    const d = c.date.slice(0, 10);
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push({ c, gIdx });
  });

  const segs: FlowSegment[] = [];
  byDay.forEach((items) => {
    const eng = new FirstSwingEngine(opts.mPoints ?? 20, opts.twoClose ?? true);
    for (const it of items) eng.processBar(it.c, it.gIdx);
    if (!(eng.declared && eng.startIdx >= 0)) return;
    segs.push({
      dir: eng.dir === "up" ? "B" : "S",
      startIdx: eng.startIdx,
      startPx: eng.startPx,
      endIdx: eng.endIdx,
      endPx: eng.endPx,
    });
  });
  return segs;
}

// =====================================================================
// 🟡 FS v2 ENGINE — user-spec stage machine (1-min, walker-driven)
//
// Blocks:
//   E-PIVOTS   session extreme high/low (start: first bar's hi+lo).
//              New-extreme-PIVOT seals = direction progress events.
//   STAGES     selling: 2 consecutive new E-LOW pivots (count 1 → 2)
//              buying : mirror with E-HIGH pivots
//   ZONE       range-position shortcut: price entering the opposite deep
//              zone (≤ zonePct% of [E-lo, E-hi]) converts to stage-2 of
//              that side — works WITHOUT any prior count too.
//   FINAL      one NORMAL (non-extreme) opposite pivot level broken:
//              sell-swing confirmed by a normal HIGH break; buy by a
//              normal LOW break. END stamp = deepest extreme so far.
// Demoted extremes join the normal pool. First swing per day only.
// Live-safe: closed bars only; declared end never repaints.
// =====================================================================

export interface FsV2Opts {
  zonePct?: number; // deep-zone % of range (default 25)
  armBars?: number; // min bars before zone rules arm (default 5)
  armRangePts?: number; // min range pts before zone arms (default 20)
  sustainBars?: number; // N consecutive closes beyond broken extreme = confirm (default 7)
  simpleMode?: boolean; // v4-simple: reversal(90% flip) IS the lock; one chop break confirms
}

interface FsLevel {
  px: number;
  idx: number;
  time: string;
}

export class FsV2Engine {
  private walker = new WalkerEngine();
  private barsSeen = 0;

  // live session extremes (path-stamped — freshest candle wins)
  private eHi: FsLevel = { px: -Infinity, idx: -1, time: "" };
  private eLo: FsLevel = { px: Infinity, idx: -1, time: "" };
  // current EXTREME PIVOTS (walker-sealed; init from bar 0)
  private eHiPivot: FsLevel | null = null;
  private eLoPivot: FsLevel | null = null;

  // unbroken normal-pivot levels (one-time-use triggers)
  private normalHighs: FsLevel[] = [];
  private normalLows: FsLevel[] = [];

  dir: "up" | "down" | null = null;
  stage = 0;
  startIdx = -1; startTime = ""; startPx = NaN;
  candIdx = -1; candTime = ""; candPx = NaN;
  declared = false;
  endTime = ""; endIdx = -1; endPx = NaN; confirmedAtTime = "";
  confirmedAtIdx = -1;
  convertedByZone = false;
  lastConfirmHit: { pool: string; px: number; idx: number; time: string } | null = null;
  confirmSource: "chop" | "sustain" | null = null;

  // ── v3 fast-path (single-E-break lock) ──
  // After direction is set, ONE live cross of the current E-pivot level in
  // the swing direction LOCKS the swing instantly (end rides the live
  // extreme from there). If instead an OPPOSITE normal-pivot breaks before
  // any such lock (and before natural stage-2), the day is INVALIDATED —
  // no-swing; renderer draws it red.
  locked = false;
  invalidated = false;

  private upStreak = 0;
  private downStreak = 0;
  private zoneSide: "up" | "down" | null = null; // last zone-conversion side
  private touchedUp = false; // price reached upper deep-zone while armed
  private touchedDown = false;

  // ── X) micro-top/lows: zero-lag local extremes (no walker seal needed) ──
  private microHighs: FsLevel[] = [];
  private microLows: FsLevel[] = [];
  private pHigh = NaN; private pHighIdx = -1; private pHighT = "";   // previous bar high
  private ppHigh = NaN; private ppHighIdx = -1; private ppHighT = ""; // bar-before-that high
  private pLow = NaN; private pLowIdx = -1; private pLowT = "";
  private ppLow = NaN; private ppLowIdx = -1; private ppLowT = "";

  // ── Y) N-candle sustain beyond the broken extreme ──
  private lockedLevelPx = NaN; // E-level that was crossed at lock (frozen)
  private sustainStreak = 0;
  private armedSeen = false;
  private histH: number[] = []; // per-bar highs/lows for touch-seeding
  private histL: number[] = [];

  constructor(private opts: FsV2Opts = {}) {}

  get zonePct() { return this.opts.zonePct ?? 25; }
  get simple() { return this.opts.simpleMode ?? false; }

  processBar(c: FlowCandle, gIdx: number) {
    if (this.declared || this.invalidated) return;
    this.barsSeen++;
    const t = c.date.slice(11, 16);
    const green = c.close >= c.open;

    if (this.barsSeen === 1) {
      this.eHi = { px: c.high, idx: gIdx, time: t };
      this.eLo = { px: c.low, idx: gIdx, time: t };
      this.eHiPivot = { ...this.eHi };
      this.eLoPivot = { ...this.eLo };
    }

    // ---- B) consume walker seals FIRST (records/pools/E-pivots) ----
    for (const p of this.walker.processBar(c, gIdx)) {
      if (!p.sealed) continue;
      if (p.kind === "H") {
        const cur = this.eHiPivot!;
        if (p.px > cur.px) {
          // NEW EXTREME-HIGH PIVOT — demote old to normals, count it
          this.normalHighs.push(cur);
          this.eHiPivot = { px: p.px, idx: p.idx, time: p.time };
          this.upStreak++;
          this.downStreak = 0;
          if (!this.simple) {
            if (this.dir !== "up") {
              this.initiate("up", t);
              this.stage = 1;
              this.convertedByZone = false;
            } else {
              this.stage = Math.min(2, Math.max(this.stage, this.upStreak));
            }
          }
        } else {
          this.pushUnique(this.normalHighs, { px: p.px, idx: p.idx, time: p.time });
        }
      } else {
        const cur = this.eLoPivot!;
        if (p.px < cur.px) {
          this.normalLows.push(cur);
          this.eLoPivot = { px: p.px, idx: p.idx, time: p.time };
          this.downStreak++;
          this.upStreak = 0;
          if (!this.simple) {
            if (this.dir !== "down") {
              this.initiate("down", t);
              this.stage = 1;
              this.convertedByZone = false;
            } else {
              this.stage = Math.min(2, Math.max(this.stage, this.downStreak));
            }
          }
        } else {
          this.pushUnique(this.normalLows, { px: p.px, idx: p.idx, time: p.time });
        }
      }
    }

    // ---- A) live path steps: stamps, zone, final trigger ----
    const armed =
      this.barsSeen > (this.opts.armBars ?? 5) &&
      this.eHi.px - this.eLo.px >= (this.opts.armRangePts ?? 20);

    // Capture extremes BEFORE halves loop — if they update this bar, a new
    // extreme was printed and the sustain streak should NOT count this bar
    // (the "hold" is measured AFTER the extreme is final, not during it).
    const eLoBefore = this.eLo.px;
    const eHiBefore = this.eHi.px;

    // ---- X) micro local-extremes: completed 2-side pivots, zero seal-lag ----
    // Bar k-1 was a LOCAL TOP/BOTTOM if its extreme beat both neighbours and
    // bar k failed to exceed it — detectable at k's close, no lookahead.
    if (this.dir && this.barsSeen >= 3 && Number.isFinite(this.ppHigh)) {
      const topFormed = this.pHigh > this.ppHigh && c.high < this.pHigh;
      const botFormed = this.pLow < this.ppLow && c.low > this.pLow;
      if (topFormed && this.pHighIdx > this.startIdx) {
        this.pushUnique(this.microHighs, { px: this.pHigh, idx: this.pHighIdx, time: this.pHighT });
      }
      if (botFormed && this.pLowIdx > this.startIdx) {
        this.pushUnique(this.microLows, { px: this.pLow, idx: this.pLowIdx, time: this.pLowT });
      }
    }

    this.histH.push(c.high);
    this.histL.push(c.low);

    const halves: [number, boolean][] = green
      ? [[c.low, true], [c.high, false]]
      : [[c.high, true], [c.low, false]];
    for (const [px, isLow] of halves) {
      if (this.declared) break;

      // live extreme stamps
      if (px > this.eHi.px) {
        this.eHi = { px, idx: gIdx, time: t };
        if (this.dir === "up") this.setCand(this.eHi);
      }
      if (px < this.eLo.px) {
        this.eLo = { px, idx: gIdx, time: t };
        if (this.dir === "down") this.setCand(this.eLo);
      }

      // zone conversion / re-arm bookkeeping
      // A deep-zone entry counts as CONVERSION only if price had earlier
      // touched the OPPOSITE deep zone while armed (true range reversal —
      // the 18-Aug "shadiest" pattern). Prevents micro-opening-range abuse.
      const rng = this.eHi.px - this.eLo.px;
      if (armed && rng > 0) {
        const pos = ((px - this.eLo.px) / rng) * 100;
        const z = this.zonePct;

        // ── one-time seeding: opening bars get evaluated against the
        // armed-time range so pre-arm tops/bottoms count as touches
        // (the 17-Aug failure: session top preceded arming) ──
        if (!this.armedSeen) {
          this.armedSeen = true;
          const hiCut = 100 - z;
          for (let h = 0; h < this.histH.length; h++) {
            const ph = ((this.histH[h] - this.eLo.px) / rng) * 100;
            const pl = ((this.histL[h] - this.eLo.px) / rng) * 100;
            if (ph >= hiCut) this.touchedUp = true;
            if (pl <= z) this.touchedDown = true;
          }
        }

        if (pos >= 100 - z) this.touchedUp = true;
        if (pos <= z) this.touchedDown = true;

        if (pos <= z) {
          const alreadyDone = this.dir === "down" && this.stage >= 2;
          const wantsChange =
            !alreadyDone &&
            this.zoneSide !== "down" &&
            this.touchedUp; // reversal proof required
          if (wantsChange) {
            this.zoneSide = "down";
            if (this.dir !== "down") this.initiate("down", t);
            this.stage = Math.max(this.stage, 2);
            this.convertedByZone = true;
          }
        } else if (pos >= 100 - z) {
          const alreadyDone = this.dir === "up" && this.stage >= 2;
          const wantsChange =
            !alreadyDone &&
            this.zoneSide !== "up" &&
            this.touchedDown;
          if (wantsChange) {
            this.zoneSide = "up";
            if (this.dir !== "up") this.initiate("up", t);
            this.stage = Math.max(this.stage, 2);
            this.convertedByZone = true;
          }
        } else {
          this.zoneSide = null; // middle band re-arms both sides
        }
      }


  // ── v3 fast-path: single E-break LOCK + opposite-break INVALIDATION ──
      if (this.dir && !this.locked) {
        if (this.dir === "down") {
          // lock: live cross BELOW the current E-LOW pivot level
          const eLoLvl = this.eLoPivot ? this.eLoPivot.px : this.eLo.px;
          if (px < eLoLvl) {
            this.locked = true;
            this.lockedLevelPx = eLoLvl;
            this.setCand(this.eLo);
          } else if (!this.simple && this.convertedByZone && this.startIdx >= 0) {
            // invalidation: reversal(zone)-established day dies if an opposite
            // fresh chop-high breaks BEFORE the E-break lock arrives
            const hit = this.normalHighs.find((l) => l.idx > this.startIdx && px > l.px);
            if (hit) {
              this.invalidated = true;
              return;
            }
          }
        } else {
          const eHiLvl = this.eHiPivot ? this.eHiPivot.px : this.eHi.px;
          if (px > eHiLvl) {
            this.locked = true;
            this.lockedLevelPx = eHiLvl;
            this.setCand(this.eHi);
          } else if (!this.simple && this.convertedByZone && this.startIdx >= 0) {
            const hit = this.normalLows.find((l) => l.idx > this.startIdx && px < l.px);
            if (hit) {
              this.invalidated = true;
              return;
            }
          }
        }
      }

      // final confirmation: ANY FRESH normal OPPOSITE pivot crossed by wick
      // (stage ≥ 2 OR locked). Fresh = formed AFTER the swing started —
      // the 19-Aug confirming high was a bounce pivot born mid-move,
      // never a stale pre-move level.
      if ((this.stage >= 2 || this.locked) && this.dir && this.startIdx >= 0) {
        if (this.dir === "down") {
          let hit = this.normalHighs.find((l) => l.idx > this.startIdx && px > l.px);
          let pool = "normal";
          if (!hit) {
            hit = this.microHighs.find((l) => l.idx > this.startIdx && px > l.px);
            pool = "micro";
          }
          if (hit) {
            this.lastConfirmHit = { pool, px: hit.px, idx: hit.idx, time: hit.time };
            this.confirmSource = "chop";
            this.confirm(gIdx, t);
            return;
          }
        } else {
          let hit = this.normalLows.find((l) => l.idx > this.startIdx && px < l.px);
          let pool = "normal";
          if (!hit) {
            hit = this.microLows.find((l) => l.idx > this.startIdx && px < l.px);
            pool = "micro";
          }
          if (hit) {
            this.lastConfirmHit = { pool, px: hit.px, idx: hit.idx, time: hit.time };
            this.confirmSource = "chop";
            this.confirm(gIdx, t);
            return;
          }
        }
      }
    }

    // ---- Y) N-candle sustain beyond the broken extreme (bar-level) ----
    if ((this.stage >= 2 || this.locked) && this.dir && !this.declared && !this.invalidated) {
      const n = this.opts.sustainBars ?? 7;
      const ref =
        this.locked
          ? this.candPx
          : this.dir === "down"
            ? this.eLoPivot?.px ?? this.eLo.px
            : this.eHiPivot?.px ?? this.eHi.px;
      // If this bar printed a new extreme in the swing direction, it's part
      // of the MOVE, not the HOLD. Reset streak so the 7-count starts after
      // the extreme is final (bar that makes the low/high doesn't count).
      const madeNewExtreme =
        this.dir === "down" ? this.eLo.px < eLoBefore : this.eHi.px > eHiBefore;
      if (madeNewExtreme) {
        this.sustainStreak = 0;
      } else {
        this.sustainStreak =
          this.dir === "down" ? (c.close > ref ? this.sustainStreak + 1 : 0)
                                : (c.close < ref ? this.sustainStreak + 1 : 0);
      }
      if (this.sustainStreak >= n) {
        this.confirmSource = "sustain";
        this.confirm(gIdx, t);
        return;
      }
    } else {
      this.sustainStreak = 0;
    }
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
    this.declared = true;
    this.endIdx = this.candIdx;
    this.endTime = this.candTime;
    this.endPx = this.candPx;
    this.confirmedAtTime = t;
    this.confirmedAtIdx = gIdx;
  }
}

// Batch helper: replay each day through FsV2 (identical to live path).
// Returns BOTH outcomes: declared swings (cyan) and invalidated days
// (red — no-swing per v3 rule), each with its start→end segment.
export interface FsV2Result {
  day: string;
  invalid: boolean;
  confIdx: number; // global candle index of the CONFIRM bar (-1 if invalid)
  seg: FlowSegment;
  source: "chop" | "sustain" | null;
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
    const eng = new FsV2Engine(opts);
    for (const it of items) eng.processBar(it.c, it.gIdx);
    if (!eng.invalidated && !eng.declared) return;
    if (eng.startIdx < 0) return;
    out.push({
      day,
      invalid: eng.invalidated,
      confIdx: eng.confirmedAtIdx,
      seg: {
        dir: eng.dir === "up" ? "B" : "S",
        startIdx: eng.startIdx,
        startPx: eng.startPx,
        endIdx: eng.endIdx,
        endPx: eng.endPx,
      },
      source: eng.confirmSource,
    });
  });
  return out;
}

// Backward-compatible wrapper: declared-only segments.
export function computeFsV2Declared(
  candles: FlowCandle[],
  opts: FsV2Opts = {},
): FlowSegment[] {
  return computeFsV2Results(candles, opts)
    .filter((r) => !r.invalid)
    .map((r) => r.seg);
}

// ===== ⚪ ALGO FLOW LINE =====
export function computeAlgoFlowLine(candles: FlowCandle[]): FlowSegment[] {
  // Each day is walked and chained SEPARATELY — no line ever connects
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

