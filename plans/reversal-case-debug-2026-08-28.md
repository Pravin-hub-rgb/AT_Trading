# Reversal Case — 28 Aug 2026 · Debug Plan

## Theory (user-stated)

- **Selling swing** forms first (low breaks at 9:20)
- Then **reverses to top** (high breaks at 9:26)
- This is the **REVERSAL CASE** — needs ONLY ONE opposite break
- Then needs **chop OR sustain** to declare
- 9:30 candle does the chop → should be declared as reversed-to-buy swing

## What the theory document says

From [`docs/first swing detection theory.md:45-53`](../docs/first%20swing%20detection%20theory.md:45):

> **Case 2: Reversal** — The market opens, moves one way, then turns around and goes the other way.
> For a **reversal to buying**: price drops from the opening high, makes a low, then reverses upward and breaks the opening high. Just one break of the opposite extreme is enough. The market has clearly flipped.
> The rule: **opposite side needs only one break**. The reversal itself is the proof.

## What the engine does on 28 Aug (predicted from code trace)

| Bar  | Time                       | Walker seals                      | Engine step                                                                                                             | State after                                    |
| ---- | -------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| 9:15 | seed                       | opens 9:15 H (assuming red)       | `barsSeen=1` seed                                                                                                       | `state=watch`                                  |
| 9:20 | low break (selling starts) | seals 9:15 H, starts down-leg     | `lock("down")` at [`firstswing.ts:181`](../frontend/src/lib/firstswing.ts:181)                                          | `state=locked, dir=down, sameSideBreaks=1`     |
| 9:26 | **up break** (reversal)    | may seal a 9:20 L (as `eLoPivot`) | `upBreak=true` → `flip("up")` at [`firstswing.ts:199`](../frontend/src/lib/firstswing.ts:199)                           | `dir=up, dirConfirmed=true, startIdx=9:20-low` |
| 9:30 | chop bar                   | (no new extreme)                  | `checkChop()` at [`firstswing.ts:255`](../frontend/src/lib/firstswing.ts:255) — needs `lo < latestAfter(normalLows).px` | depends on pool                                |

## The Bug

**Location:** [`frontend/src/lib/firstswing.ts:311-317`](../frontend/src/lib/firstswing.ts:311) (`latestAfter`) combined with [`flip()` at line 234-244`](../frontend/src/lib/firstswing.ts:234) (resets startIdx to the 9:20 low).

**The problem:**

- After the 9:26 reversal flip, `dir=up` and `startIdx = eLo.idx` (the 9:20 low).
- `normalLows` is populated ONLY when the walker demotes a previously-held `eLoPivot` to the pool (line 138-141). On a clean reversal, the FIRST low that gets demoted is whatever low was held before the 9:20 break — typically the 9:15 candle's low (if it was green-seeded) or the very first bar.
- `latestAfter` filters `idx > this.startIdx` (i.e., AFTER the 9:20 low). Most early-session lows are BEFORE 9:20, so the filter excludes them.
- Result: `tgt` is `null` → `checkChop()` returns without declaring.
- The reversal case is correctly detected direction-wise but never confirms because the chop pool is empty in the relevant index window.

## Why same-direction (continuation) works

In the continuation case, `lock()` is called when the SAME side breaks twice. The "normal" pool has been seeded with multiple lows/highs DURING the locked leg, so by the time `checkChop` runs (post-`sameSideBreaks=2`), there are plenty of pool entries with `idx > startIdx`.

## Hypothesized fix (Fix B)

Change the chop target filter so that for a **reversal flip**, the "after" filter is dropped (or relaxed) — the chop can hit ANY prior opposite pivot, not just one AFTER the new start. This matches the theory doc literally: _"if price breaks any previous pivot in the opposite direction, that's chop."_

Concretely in [`firstswing.ts`](../frontend/src/lib/firstswing.ts):

```ts
// In flip(), mark that this is a reversal-spawned swing:
private isReversal = false;
private flip(dir: "up" | "down") {
  this.dir = dir;
  this.isReversal = true;  // NEW
  // ... existing
}

// In checkChop(), use isReversal to skip the idx > startIdx filter:
private checkChop() {
  const pool = this.dir === "down" ? this.normalHighs : this.normalLows;
  const px = this.dir === "down" ? this.hi : this.lo;
  // ... find ANY target in pool
  const tgt = this.isReversal
    ? pool.filter(l => l.px relevant).pop()  // any prior opposite pivot
    : this.latestAfter(pool);
  // ...
}
```

## Step 1 — Confirm via trace (this task)

Run `fsdebug.ts` with day arg `2026-08-28` to see bar-by-bar state transitions. Expected output if my analysis is correct:

```
09:15 ...   | -   (watch)
09:20 ...   | downL  (locked, dir=down)
09:26 ...   | upD    (flip → up, declared or not)
09:30 ...   | upD    (chop check runs, pool empty in window → not declared)
...
NOT DECLARED
```

If trace matches → confirm bug → proceed to fix.
If trace declares successfully → my analysis is wrong, re-investigate.

## Step 2 (after confirmation)

Add a focused test case in [`fsv2.test.ts`](../frontend/fsv2.test.ts) (or a new file) that hardcodes the 28 Aug reversal case and asserts:

- `dir === "up"`
- `confirmSource === "chop"`
- declared within 5 min of actual 9:30

## Step 3 (after test)

Apply Fix B in [`firstswing.ts`](../frontend/src/lib/firstswing.ts):

1. Add `isReversal: boolean` flag, set in `flip()`.
2. Modify `checkChop()` to consider ALL pool entries (no `idx > startIdx` filter) when `isReversal === true`.
3. Reset `isReversal` to false in `lock()` and on next swing.

## Step 4

Re-run full history test in [`fsv2.test.ts`](../frontend/fsv2.test.ts) — ensure no regression on continuation cases.

## Files involved

- [`frontend/src/lib/firstswing.ts`](../frontend/src/lib/firstswing.ts) — the engine under test
- [`frontend/src/lib/flowline.ts`](../frontend/src/lib/flowline.ts) — walker (source of pivots, NOT buggy)
- [`frontend/fsdebug.ts`](../frontend/fsdebug.ts) — bar-by-bar trace harness
- [`frontend/fsv2.test.ts`](../frontend/fsv2.test.ts) — full-history scoring
- [`docs/first swing detection theory.md`](../docs/first%20swing%20detection%20theory.md) — ground-truth spec

## Out of scope

- flowline.ts walker logic (not the bug)
- bias / case mapping (separate engine)
- flow-line handoff (different feature)
