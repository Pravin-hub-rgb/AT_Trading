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

function walkDay(items: { c: FlowCandle; gIdx: number }[]): AlgoPivot[] {
  const n = items.length;
  if (n === 0) return [];

  const pivots: AlgoPivot[] = [];
  const tOf = (i: number) => items[i].c.date.slice(11, 16);

  // ---- seed from first bar's colour ----
  const firstGreen = items[0].c.close >= items[0].c.open;
  pivots.push({
    idx: items[0].gIdx,
    time: tOf(0),
    kind: firstGreen ? "L" : "H",
    px: firstGreen ? items[0].c.low : items[0].c.high,
    sealed: true,
  });
  let dir: "up" | "down" = firstGreen ? "up" : "down";
  let stampIdx = items[0].gIdx;
  let stampK = 0;
  let stampT = tOf(0);
  let stampPx = firstGreen ? items[0].c.high : items[0].c.low;

  let prevHigh = items[0].c.high;
  let prevLow = items[0].c.low;

  // Marker band = px of the most recently PUSHED H pivot and L pivot.
  // Used to decide insider+volatile handling (skip inside / mark outside).
  // One-sided until the opposite kind actually prints its first marker.
  let bandLow: number | null = null;
  let bandHigh: number | null = null;

  type Pending = {
    k: number;
    kind: "H" | "L";
    idx: number;
    time: string;
    px: number; // far-side extreme (current STACK's far edge)
    near: number; // near-side extreme (current STACK's near edge)
    // Onion peel: alternating zigzag points contributed by each stack layer
    // (layer 1 = FAR edge, layer 2 = NEAR edge, layer 3 = FAR again...),
    // flushed chronologically when the stack finally resolves.
    inner: { idx: number; k: number; time: string; kind: "H" | "L"; px: number }[];
  };
  let pending: Pending | null = null;

  const flushInner = (p: Pending) => {
    for (const ip of p.inner) {
      pivots.push({ idx: ip.idx, time: ip.time, kind: ip.kind, px: ip.px, sealed: true });
      trackBand(ip.kind, ip.px);
    }
  };

  // Close a resolved stack: append its final alternating layer record (only
  // when the stack actually peeled — single insiders contribute nothing) and
  // flush chronologically. Returns the last flushed record, or null.
  const closeStack = (
    p: Pending,
  ): { idx: number; k: number; time: string; kind: "H" | "L"; px: number } | null => {
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
      pivots.push({ idx: ip.idx, time: ip.time, kind: ip.kind, px: ip.px, sealed: true });
      trackBand(ip.kind, ip.px);
      last = ip;
    }
    return last;
  };

  const trackBand = (kind: "H" | "L", px: number) => {
    if (kind === "H") {
      bandHigh = px;
      hiPx = null; // H finalized — highs restart accumulating toward next L
    } else {
      bandLow = px;
      loPx = null; // L finalized — lows restart accumulating toward next H
    }
  };

  // Running extremes since the last pushed pivot of each kind. These are the
  // trader's "real" swing marks: a confirming insider may sit inside an
  // extreme the leg already printed, and the LEG's extreme wins.
  let hiPx: number | null = null;
  let hiIdx = -1;
  let hiK = -1;
  let hiT = "";
let loPx: number | null = null;
  let loK = -1;
  let loIdx = -1;
  let loT = "";

  const pushStamp = () => {
    pivots.push({
      idx: stampIdx,
      time: stampT,
      kind: dir === "up" ? "H" : "L",
      px: stampPx,
      sealed: true,
    });
    trackBand(dir === "up" ? "H" : "L", stampPx);
  };

  trackBand(firstGreen ? "L" : "H", firstGreen ? items[0].c.low : items[0].c.high);
  hiPx = firstGreen ? items[0].c.high : null;
  if (hiPx !== null) { hiIdx = items[0].gIdx; hiK = 0; hiT = tOf(0); }
  loPx = firstGreen ? null : items[0].c.low;
  if (loPx !== null) { loIdx = items[0].gIdx; loK = 0; loT = tOf(0); }
  cov(firstGreen ? "seed:green" : "seed:red");

  for (let k = 1; k < n; k++) {
    const c = items[k].c;

    let flippedThisBar = false;
    let skipSteps = false;

    // ---- pending resolution BEFORE this bar's steps ----
    // Outside bar (breaks BOTH sides) => insider SKIPPED, leg takes the
    // bar's ending direction. Single-side break => confirm/skip normally.
    if (pending) {
      const pk: "H" | "L" = pending.kind;
      const stackHi = Math.max(pending.px, pending.near);
      const stackLo = Math.min(pending.px, pending.near);

      // ---- ONION RULE: nested insider absorbs into the stack ----
      // Strictly inside the current stack => consolidation continues. Every
      // stack layer contributes ONE alternating zigzag point: layer 1 its
      // FAR edge, layer 2 its NEAR edge, layer 3 FAR again... Parity of the
      // peel buffer decides which side this layer contributes. Append this
      // layer's record, shrink stack to this bar.
      if (c.high < stackHi && c.low > stackLo) {
        // ROLE-BASED (see closeStack) — pendPx = far edge BY DEFINITION.
        const wantFar = pending.inner.length % 2 === 0;
        cov((wantFar ? "onion:FAR-layer:pk" : "onion:NEAR-layer:pk") + pk);
        pending.inner.push(
          wantFar
            ? { idx: pending.idx, k: pending.k, time: pending.time, kind: pk, px: pending.px }
            : { idx: pending.idx, k: pending.k, time: pending.time,
                kind: pk === "H" ? "L" : "H", px: pending.near },
        );
        pending = {
          kind: pk,
          idx: items[k].gIdx,

          k,
          time: tOf(k),
          px: pk === "H" ? c.high : c.low,
          near: pk === "H" ? c.low : c.high,
          inner: pending.inner,
        };
        flippedThisBar = true;
        skipSteps = true;
      } else {
        // STRICT breaks: an exact touch/equal-print does NOT count as a break.
        const confirmHit = pk === "H" ? c.low < pending.near : c.high > pending.near;
        const skipHit = pk === "H" ? c.high > pending.px : c.low < pending.px;
        if (confirmHit && !skipHit) {
          cov("confirm:pk" + pk + (pending.inner.length > 0 ? ":peeled" : ""));
                    // CONFIRM — seal pre-insider swing; a PEELED stack emits its
                    // remaining alternating layers (continuation keeps the leg);
                    // a plain single insider prints its far edge (+override).
                    pushStamp();
                    const p = pending;
                    const hadPeel = p.inner.length > 0;
                    const lastRec = closeStack(p);
                    if (hadPeel && lastRec) {
                        stampIdx = lastRec.idx;
                        stampK = lastRec.k;
                        stampT = lastRec.time;
                        stampPx = lastRec.px;
                    } else {
                        let pIdx = p.idx;
                        let pT = p.time;
                        let pPx = p.px;
                        let pK = p.k;
                        if (pk === "H" && hiPx !== null && hiPx > pPx) {
                            // leg already printed a higher high AFTER the reference marker
                            const hiAfter = hiK > stampK || (hiK === stampK && items[hiK].c.close >= items[hiK].c.open);
                            if (hiAfter) {
                                pIdx = hiIdx;
                                pT = hiT;
                                pPx = hiPx;
                                pK = hiK;
                            }
                        }
                        if (pk === "L" && loPx !== null && loPx < pPx) {
                            const loAfter = loK > stampK || (loK === stampK && items[loK].c.close < items[loK].c.open);
                            if (loAfter) {
                                pIdx = loIdx;
                                pT = loT;
                                pPx = loPx;
                                pK = loK;
                            }
                        }
                        pivots.push({ idx: pIdx, time: pT, kind: pk, px: pPx, sealed: true });
                        trackBand(pk, pPx);
                        stampIdx = pIdx;
                        stampK = pK;
                        stampT = pT;
                        stampPx = pPx;
                    }
                    pending = null;
                } else if (skipHit && !confirmHit) {
          cov("skip1:pk" + pk);
          // SINGLE-SIDE far break -> reversal flip. Peeled stacks emit their
          // remaining alternating layers before the flip; single insiders
          // stay print-free (legacy).
          const p0 = pending;
          const hadPeel = p0.inner.length > 0;
          pending = null;
          pushStamp();
          closeStack(p0);
          dir = pk === "H" ? "up" : "down";
          stampIdx = items[k].gIdx;
          stampK = k;
          stampT = tOf(k);
          stampPx = pk === "H" ? c.high : c.low;
          flippedThisBar = true;
          skipSteps = true;
          void hadPeel;
        } else if (skipHit) {
        // DOUBLE-BREAK (volatile candle) — marker-band decides.
        // Band = [active low marker, active high marker]; the ACTIVE leg's
        // running stamp IS its side's live marker.
        const iLo = Math.min(pending.px, pending.near); // stack low
        const iHi = Math.max(pending.px, pending.near); // stack high
        const effLo = dir === "down" ? stampPx : bandLow ?? Number.NEGATIVE_INFINITY;
        const effHi = dir === "up" ? stampPx : bandHigh ?? Number.POSITIVE_INFINITY;
        const insideBand =
          iHi <= effHi && iLo >= effLo && c.high <= effHi && c.low >= effLo;
        if (insideBand) {
            cov("dbl:insideBand:pk" + pk);
          // Inside band -> SKIP insider (continuation); line rides to the
          // volatile bar's extreme. (e.g. 21 Aug 11:00/11:05)
          pending = null;
          pushStamp();
          dir = pk === "H" ? "up" : "down";
          stampIdx = items[k].gIdx;
          stampK = k;
          stampT = tOf(k);
          stampPx = pk === "H" ? c.high : c.low;
          skipSteps = true; // bar consumed — its halves already priced in
        } else {
          cov("dbl:escape:pk" + pk);
          // Band ESCAPE -> MARK the stack's far-side extreme (mirrored):
          //   marker L (pk=H): seal L@stamp -> peel -> H@stack.high, leg down from near
          //   marker H (pk=L): seal H@stamp -> peel -> L@stack.low, leg up from near
          // The volatile bar's own halves then play out via normal steps,
          // producing both the green-volatile and red-volatile chains.
          const p = pending;
          pending = null;
          pushStamp(); // seal the running stamp (the P-candle marker)
          const lastRec = closeStack(p); // peel layers + final far-edge record
          if (!lastRec) {
            // single insider (no peel): legacy direct far-edge print
            pivots.push({ idx: p.idx, time: p.time, kind: pk, px: p.px, sealed: true });
            trackBand(pk, p.px);
          }
          dir = pk === "H" ? "down" : "up"; // leg heads toward the near side
          stampIdx = p.idx;
          stampK = p.k;
          stampT = p.time;
          stampPx = p.near; // seed at stack's near extreme
        }
        flippedThisBar = true;
      }
      }
    }

    for (const step of skipSteps ? [] : barSteps(c)) {
      if (step.side === "low") {
        if (dir === "down") {
          if (step.px < stampPx) {
            stampIdx = items[k].gIdx;
          stampK = k;
            stampT = tOf(k);
            stampPx = step.px;
          }
        } else if (step.px < prevLow) {
          // up-leg violated -> seal H stamp, flip down (dead pending dies too)
          pending = null;
          pushStamp();
          dir = "down";
          stampIdx = items[k].gIdx;
          stampK = k;
          stampT = tOf(k);
          stampPx = step.px;
          flippedThisBar = true;
        }
      } else {
        if (dir === "up") {
          if (step.px > stampPx) {
            stampIdx = items[k].gIdx;
          stampK = k;
            stampT = tOf(k);
            stampPx = step.px;
          }
        } else if (step.px > prevHigh) {
          // down-leg violated -> seal L stamp, flip up (dead pending dies too)
          pending = null;
          pushStamp();
          dir = "up";
          stampIdx = items[k].gIdx;
          stampK = k;
          stampT = tOf(k);
          stampPx = step.px;
          flippedThisBar = true;
        }
      }
    }

    // ---- inside-candle detection -> pending far-side extreme ----
    // (checked AFTER this bar resolves: an insider never marks itself;
    //  the NEXT bar's break decides confirm vs skip)
    if (!pending && !flippedThisBar && c.open !== c.close && c.high <= prevHigh && c.low >= prevLow) {
      pending = {
        kind: dir === "down" ? "H" : "L",
        idx: items[k].gIdx,

        k,
        time: tOf(k),
        px: dir === "down" ? c.high : c.low,
        near: dir === "down" ? c.low : c.high,
        inner: [],
      };
    }

    void flippedThisBar;

    // running extremes since each side's last pushed pivot
    if (hiPx === null || c.high > hiPx) {
      hiPx = c.high;
      hiIdx = items[k].gIdx;
      hiK = k;
      hiT = tOf(k);
    }
    if (loPx === null || c.low < loPx) {
      loPx = c.low;
      loIdx = items[k].gIdx;
      loK = k;
      loT = tOf(k);
    }

    prevHigh = c.high;
    prevLow = c.low;
  }

  // trailing open swing (not yet confirmed)
  pivots.push({
    idx: stampIdx,
    time: stampT,
    kind: dir === "up" ? "H" : "L",
    px: stampPx,
    sealed: false,
  });

  return enforceAlternation(dedupe(pivots));
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

