# RETRACEMENT DEPTH AT ENTRY — the P1/P2 quantity. Tested, and it is
# NOT A VALID COMPARISON. The ladder is flat and the harness is wrong.

Date: 2026-09-28. `exp_retrace_depth.py` → `_retrace_depth.json` 47.0s.
Baselines exact: 500t +325.8R IS / 279t +70.2R OOS.

## What was run

For every B2/FLIP entry the champion can take, how deep did price retrace
against the trade before the break fired, in units of the trade's own
risk. Five pre-registered bands, both eras, each cell printed against the
baseline. This is the P1/P2 quantity relocated to the level where it
actually exists (PROBE 1: the chain is sequential with a mean 10.3-bar
gap, so no nested wave pair exists — but the pullback inside one entry's
own leg does).

## Two problems, and the second one is mine

### 1. THE HARNESS IS NOT THE CHAMPION'S BOOK — my bug

| | baseline | sum of ladder cells |
|---|---|---|
| IS | 500 trades | **1,285** |
| OOS | 279 trades | **700** |

The cells contain 2-2.5× the baseline's trades, so **each rung is not a
subset of the champion's book** and the "vs baseline" column is
meaningless.

Cause: I enumerated signals with `_collect_signals` and then applied only
`busy_until` + `cooldown`. **I did not apply the HTF bias-window gate or
the `ext_stop_r` gate** — `v18_streak_halt.py` requires the 15m signal to
fall inside a 1h window (`s + 2700 < bar_ts <= e + 2700`) in the same
direction, and drops ~78% of signals on that alone. Without it I built a
larger, ungated book and compared it to a gated one.

**The comparison is invalid and I am not going to rescue it by
re-interpreting the numbers.** The fix is to gate the signals identically
to the engine, and then re-run.

### 2. THE DISTRIBUTION IS BURIED AT THE FLOOR

    IS  retrace depth (R): p10 0.998  p25 1.058  MED 1.243  p75 1.796  p90 3.337
    OOS retrace depth (R): p10 0.999  p25 1.081  MED 1.273  p75 1.862  p90 3.159

**Essentially every signal already sits at depth ≥ 1.0.** The two shallow
bands (`<0.25`, `0.25-0.50`) contain 12 trades in IS and **zero** in OOS.

This is a definitional consequence, not a market fact. I defined depth as
"worst adverse excursion over the last 60 bars, in units of risk", and by
the time a B2/FLIP break has fired price has *already* travelled away from
the extreme — often by more than the trade's own risk. **The measurement
starts counting after the pullback is over**, so a five-band ladder on this
definition has one populated bucket and four empty ones.

The right definition would be measured **from the swing's extreme to the
entry bar**, not from a rolling 60-bar window — but that needs the swing
segment, which is a different computation and would have to be re-probed
before use.

## What the numbers would have said, if the harness were right

Nothing survives. IS trim: +0.207, −0.060, −0.084, −0.093 (falling). OOS
trim: +0.155, −0.257, −0.203. **Not monotone, not same-sign.** Even
ignoring the harness bug, there is no signal here.

## Verdict

- **CLOSED as specified, on two independent grounds:** the harness does
  not reproduce the champion's book, and the feature is saturated at its
  floor so the ladder has no gradient to measure.
- **Do not re-run with just the window gate fixed** unless the depth
  definition is changed too — a correctly-gated book on this definition
  would still be ~one populated bucket.
- If retracement depth is revisited it must be measured **swing-extreme →
  entry**, and that needs its own probe first.

## Honest note on the P1/P2 family

This was the idea all four second-researchers ranked first, and it has now
failed in both of its reachable forms: the wave-labelling form
(structurally impossible on a stitched chain) and the entry-depth form
(this). **The underlying intuition — pullback depth predicts continuation —
is not something this mark set can express**, because by the time the mark
fires the pullback is already in the past.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
