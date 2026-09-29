# P1-PROBE — the nesting premise is monotone but flat. P1 not justified.

`exp_nesting_probe.py`. Pins reproduced first (IS 500t/+325.8R, OOS
279t/+70.1R). This tests P1's **premise**, not P1 itself.

## Why a probe rather than the build

P1 proposes rewriting swing generation so legs nest instead of tiling
(`btc_swing.py:150` — `next_start_pos = end_pos + 1`, so leg k+1 always
starts one bar after leg k's extreme). That is the component F1 showed to
be knife-edge: swapping the LTF structure cost 84R IS / 55R OOS, and
`min_bars=50` is a sharp optimum. A large build on an untested premise is
a bad bet when the premise has a cheap test.

**The cheap test:** if nesting information is worth generating, then
nesting depth computed from the *existing* tiling should already show
signal. The book already sits inside tiled legs; the depth around each
entry is computable today.

## The result — a strong monotone gradient that does not clear the null

**IS**

| cohort | n | net | WR | M | |
|---|---|---|---|---|---|
| nest_1h low | 167 | **−4.1R** | 22.8% | 95.1R | inside |
| nest_1h mid | 167 | +117.2R | 33.5% | 237.8R | inside |
| nest_1h high | 166 | **+243.8R** | 33.7% | 304.5R | inside |

**OOS**

| cohort | n | net | WR | M | |
|---|---|---|---|---|---|
| nest_1h low | 94 | **−10.3R** | 28.7% | 39.6R | inside |
| nest_1h mid | 93 | +39.7R | 30.1% | 85.1R | inside |
| nest_1h high | 92 | +49.1R | 25.0% | 83.5R | inside |

**NONE clear. Not one cohort, in either era, beats a reshuffle of itself.**

## What this does and does not say

**There is a real, monotone, two-era gradient.** Entering late in a 1h
leg is worth roughly **+248R IS / +59R OOS** versus entering early, and
the win rate moves 22.8% → 33.7% in IS. That is the largest and cleanest
ordering effect found today, and it is exactly the kind of thing that
looks like a discovery.

**It is still inside the null, in both eras, at every tercile.** IS high
is +243.8R against M = 304.5R. OOS high is +49.1R against M = 83.5R. A
cohort of 90-167 trades with a 30% win rate simply cannot be resolved
against a reshuffle of itself — the same wall P5 and P8 hit.

**So P1's premise is not disproved. It is unmeasured.** The gradient is
consistent with nesting mattering and entirely consistent with nesting
not mattering. Given `M ≈ 480R` IS, that is the expected state of affairs
for any feature on this book, and it is the reason P5 was worth running
first.

## Two limitations, stated because they weaken the negative

**1. `nest_15m` came out DEGENERATE.** All 500 IS trades landed in a
single tercile — the feature carried no variance. Cause: `entry_idx`
sits near the start of its own 15m leg by construction, because a trade
is a *break of that very leg*, so the entry is always early in it. So
`nest_both` is identical to `nest_1h` in every row above; the LTF half of
the nesting idea was not actually tested.

**This matters.** P1's thesis is specifically about *two-level* nesting —
"this 15m pullback inside a 15m up-leg inside a 1h up-leg." Half of that
label is missing. The probe tested one level well and the other not at
all.

**2. Position-in-time is a weak proxy for containment.** `nest_1h` here
is *where in the window's lifetime* the entry falls, not where it sits in
the leg's price structure. That is closer to window age (W1) than to
nesting, and W1 already failed.

## Recommendation

**Do not build P1 on this evidence, and do not close it either.**

- The one-level gradient is real and two-era monotone. It is the single
  most promising descriptive signal found today.
- It cannot be promoted at n = 90-167 per tercile against M ≈ 84-305R.
- The genuinely novel half — LTF-inside-HTF containment — was not
  measured here, because the natural label collapses.

**If P1 is ever built, the falsifier that matters is its own (c):** if the
containment-aligned cohort turns out to be a subset of the
`RANGE_PEAK_GRAY` cohort the repo already showed is the book's best (WR
41-42% vs 27.8%), then nesting is re-discovering range position and fails
4/4 the same way. **The `nest_1h` gradient's monotone ordering makes that
warning more relevant, not less** — late-in-leg entries being good is
exactly what "near the extreme" already predicts.
