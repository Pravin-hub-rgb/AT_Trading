# ZigZag Flow-Line

> A color-aware candle-path structure engine that reads price action the way a
> discretionary trader does — and draws it as a live zigzag line.

**Three implementations, one brain:**

| File | Role |
|------|------|
| `frontend/src/lib/flowline.ts` | 🧠 The engine (TypeScript, replay/offline) |
| `frontend/algotest.ts` | 🔬 The proof — regression harness vs hand-marked truth |
| `docs/pinescript/flowline.pine` | 📈 The live version (Pine v6, TradingView) |

---

## The Story

This thing was *earned*.

It started with a hand-drawn orange line on a chart — 31 pivots on 21 Aug 2026,
marked by a human who reads order flow for a living. The mission from
`docs/flow-line-handoff.md`: build `computeAlgoFlowLine()` so its white line
matches that drawing **exactly**, then generalize.

### Attempt #1: leave it to the machines

The first approach was simple — hand the orange line points to AI agents and
let them figure the rules out on their own. They had the ground truth, they
had the data, how hard could it be?

Days of agent-driven debugging followed. Every session ended with "fixed!" and
every next session started with two new things broken. The agents kept
inventing plausible-looking heuristics — deviation zigzags, fixed thresholds,
HH/LL-tag zigzags wired to the wrong toggles — each one *approximately* wrong
in a brand-new way. Stray braces killed builds. Lines joined trading days
across thin air. The white line wandered further from the orange one with every
patch. Progress: **zero**.

### Attempt #2: the human wrote the algorithm

Then came the shift that actually worked: **the trader wrote the algorithm
himself**. Not as bullet points for an agent to interpret — as real logic:
*green prints low first*, *this break seals, this one shifts*, *skip the
insider here, mark it there*. Case by case, bar by bar, walking the chart with
the OHLC open. Each rule landed in code the same day it was understood. And
suddenly the edge cases stopped being terrifying — insiders, stacked onions,
volatile sweeps, band escapes — because each one got **diagnosed by the person
who could actually see the structure**, then covered explicitly, then locked
behind a regression test.

The AI's role shrank to what it's good at: translating trader-speak into
TypeScript, running the harness, catching typos. The thinking was human.

Three things from that phase are load-bearing forever:

1. **The SL-trailing insight** — the backend's `_manage_1m_chunk()` already
   knew how to walk candles "like crazy" for stop-loss fills: green candles
   print LOW first, red candles print HIGH first. That color-aware intrabar
   ordering became the heart of the walker.
2. **Trader quotes became specs** — *"low of both candles is same but it
   didn't break so we can't consider it"* → strict breaks; *"we can't go
   zig-zig or zag-zag"* → alternation law; *"there shouldn't be any candle
   high higher than the marked one"* → envelope law.
3. **Ground truth stayed sacred** — orange = hardcoded manual pivots, white =
   algorithm only. This identity never flipped again.

Final score across four hand-marked days: **71/71 pivots exact** — time, type
and price.

---

## The Rules (as encoded)

### Foundations (course S6)

| Rule | Implementation |
|------|----------------|
| GREEN candle path: LOW → HIGH (bottom-to-top) | Each bar processed as ordered half-steps `[low, high]` |
| RED candle path: HIGH → LOW (top-to-bottom) | Ordered half-steps `[high, low]` |
| Extended leg: continuous same-direction breaks = ONE move | Same-direction breaks only **shift** the stamp (running extreme); no new pivot |
| Swing magnitude varies wildly (5–50 pts) | No fixed thresholds anywhere — pure structural logic |

### Pivot sealing

A stamp becomes a **pivot** when a later bar breaks the **previous bar's
opposite extreme** — checked strictly (`==` doesn't count; learned from
20 Aug where 10:40/10:45 shared an identical low). Because bars are processed
as path-ordered half-steps, violent bars resolve themselves naturally:

- Selling flow + outside GREEN bar → `…H → L@bar.low → H@bar.high` (two marks, one candle)
- Double-flips inside one bar (21 Aug 10:00 H+L, 10:20 H+L) emerge automatically

### Insiders & volatiles — the matrix

An **inside candle** holds its far-side extreme as *pending*. The next closed
bar resolves it. The **marker band** = [lowest active L marker, highest active
H marker] (the running stamp counts as its side's live marker).

| Setup | Resolution | Output |
|------|------------|--------|
| insider, near-side break | **Confirm** | seal pre-insider swing → print insider edge → resume |
| insider, far-side break | **Skip** | discard, flip toward the break |
| volatile, both breaks, inside band | **Skip all** | ride straight to the volatile extreme (21 Aug 11:00/11:05) |
| volatile, both breaks, band escape | **Mark stack far edge** | e.g. `L@12:25 → H@12:30 → L@12:35` (20 Aug) |

### Onion stacks 🧅

Insider → volatile → insider → volatile… any N-deep chain of nested insiders.
Each nesting **buffers the rejected outer edge**; resolution flushes buffered
edges chronologically, then prints the innermost near-edge. Born from 24 Aug
where two stacked insiders demanded `9:55 L → 10:00 H → 10:05 L`.

### The Laws

1. **Alternation Law** — cross-candle `H,H` / `L,L` can never render. A final
   merge pass collapses same-kind neighbors (extreme wins). Same-candle
   volatile pairs (`10:55 H+L`) are exempt by nature.
2. **Envelope Law** — after an L marker, no candle low may undercut it before
   an H prints; symmetric for highs. Enforced by the harness on **every day**
   of data, hard-failing on hand-marked days (0 violations), reporting
   candidates elsewhere.
3. **Leg-extreme memory** — a confirming insider sitting inside an extreme the
   leg already printed can never demote it (19 Aug: `H@10:00 107.80`, not the
   insider's `102.50`).

---

## Architecture

```
candles ──▶ per-day group ──▶ seed (color) ──▶ state machine ──▶ pivots ──▶ segments
                                          │
   state: dir · stamp · prevHigh/Low      │ loops until day ends
          pending(+onion buffer)          ▼
          marker band                sealed pivot chain
          hi/lo leg memory
```

- **Live-safe**: state advances on closed candles only. The forming swing is a
  separate provisional mark that never lies about history.
- **Per-day isolation**: sessions never connect — no 15:25→09:15 bridges.

## Validation

`bun frontend/algotest.ts` — exits non-zero on any drift.

```
19 Aug window [09:50..10:20] :  4/4   (sweep-reversal volatile)
20 Aug full day              : 32/32
21 Aug full day              : 31/31
24 Aug window [09:55..10:20] :  4/4   (stacked insiders)
ENVELOPE law                 :  0 violations on marked days
```

Plus ~250 unlabeled days scanned daily by the envelope validator — residual
candidates are catalogued in the test output for future ruling.

## TradingView usage

1. Open `docs/pinescript/flowline.pine`, copy everything.
2. TradingView → Pine Editor → paste → **Add to chart** (NIFTY 50, 5-min recommended; rules are timeframe-universal — live-tested on 5-min and 1-min).
3. Inputs: leg colors, forming-swing color, width, optional H/L tags,
   retrace warning distance (points) + retracing color.
4. **The forming swing is breach-gated** — three live states:

   | State | Trigger | Dashed line |
   |-------|---------|-------------|
   | **EXTENDING** | live price breaches the stamped extreme | endpoint rides the tick (`bar_index`, `price`) |
   | **HOLDING** | no breach yet | endpoint stays **pinned at the stamp** — no poke into weak candles |
   | **FLIP-BREWING** | live candle is beyond its flip trigger (down-leg: high > prevHigh · up-leg: low < prevLow) | line tints toward the NEW leg's color instantly — solid seal commits on this candle's close |
   | **RETRACING** | price pulls back ≥ N pts from the extreme (and no flip brewing) | line turns orange (momentum-break cue) |

   Priority when multiple apply: FLIP-BREWING > RETRACING > normal.

   On seal, the dashed line solidifies into a permanent segment and the
   preview jumps to anchor the next leg.

**Repaint contract:** sealed pivots never move or vanish. The dashed forming
swing updates tick-by-tick by design — it is the live question, not history.
Its tip position follows the breach rules above; only the *forming* leg ever
changes, and it changes exactly when the structure itself extends.

**Alternation guard (Pine = TS):** cross-candle `H,H` / `L,L` marks are
structurally impossible — a stronger same-kind print EXTENDS the existing leg,
a weaker one is dropped. Same-candle volatile pairs (`H+L`) pass through.

## Port notes (TS → Pine)

- TS's bar loop == Pine's native per-bar execution; all `let` state became
  `var` fields on one UDT mutated via methods (Pine functions can't touch globals).
- `barstate.isconfirmed` gates every mutation — the literal translation of
  "closed candles only".
- Day rollover finalizes the open swing (dotted gray tail) and wipes per-day
  state; the new session seeds from its own first candle.
- Line budget: TV keeps the newest 500 segments, silently GC-ing older ones —
  display-only, machine state unaffected.

## Known Limitations (accepted, documented)

| Case | What happens | Ruling |
|------|--------------|--------|
| `2025-11-24 09:20` zone | Ambiguous multi-insider cluster; order-flow trace unclear even by eye | **Dropped** — intentionally unhandled |
| Inside-band skip discards buffered stack layers | e.g. `2026-02-23`: buffered swing-high `H@09:55(43.95)` dropped when a volatile double-break resolves inside the band → later wick exceeds final H-mark (envelope candidate) | **Accepted** — emitting them broke 21 Aug GT; revisit only if this family recurs on hand-marked days |
| Unlabeled-day envelope candidates (~6) | Micro-wicks (0.3–6.5 pts) between sealed markers | Warn-only — reviewed periodically, never block |

## Roadmap

- [ ] Rule-refine remaining unlabeled envelope candidates
- [ ] Mark more days orange → grow the GT suite (the more wild days, the stronger the proof)
- [ ] TradingView webhook experiments (if automation ever becomes interesting)
 - [x] Timeframe-universality — rules carry to any TF (1-min live-tested); no TF-lock in the script

---

*Built by a trader who wouldn't accept "approximately right", powered by a
trailing-stop engine that walks candles like crazy.*
