# MULTI-SWING 1h BIAS CONFIRMATION (2-of-3) — CLOSED BY THE PROBE, before
# a harness was written. The rule cannot reject anything.

Date: 2026-09-28. `probe_bias_timeline.py`. No run was needed.

## What was proposed

Nemotron's P3: "Requiring 2 consecutive same-direction 1h swings before
opening a bias window will filter chop regimes where the 1h bias flips
rapidly." It was the next open item on the queue, and the only remaining
direction that intervenes on the **bias timeline** rather than filtering
an exhausted trade population.

## The probe, and what it found

    [is]  1h bars 32,434    1h swings 1,601
    [is]  BIAS WINDOWS 331   direction flips 148 (44.8%)
    [is]  1h swing dir alternation 954/1600 (59.6%)
    [is]  a 2-of-3 rule on the swing chain would KEEP 1599/1599 (100.0%)
    [oos] 1h bars 17,520    1h swings 903
    [oos] BIAS WINDOWS 210   direction flips 99 (47.4%)
    [oos] 1h swing dir alternation 535/902 (59.3%)
    [oos] a 2-of-3 rule on the swing chain would KEEP 901/901 (100.0%)

**The rule keeps 100% of swings in both eras. It cannot reject anything.**

## Why: the chain is built in runs of two

    first 24 swing dirs: [1, 1, -1, -1, 1, -1, 1, -1, -1, 1, 1, 1, 1, 1, 1, -1, ...]
    3-windows passing 2-of-3: 1599 of 1599

The direction sequence comes in **same-direction PAIRS** (1,1 / -1,-1 / ...).
Any window of three consecutive swings therefore contains at least two of
the same sign, always. A 2-of-3 majority rule is a **tautology on this
data** — it is satisfied by construction, so it selects every swing and
gates nothing.

This is a direct consequence of how the chain is built. PROBE 1 already
established that each swing is seeded after the previous one's end
(`btc_swing.py:150-152`); the engine needs a confirming break before it
declares, so a completed swing is typically followed by another in the same
direction before the first counter-move qualifies. The pair structure is
not an accident of this sample.

## What the proposal would have needed

A majority rule that can actually bind needs a threshold the sequence can
fail — e.g. **4-of-5**, or **3 consecutive** in the same direction before
the window opens, or a rule on window *duration* rather than direction
count. Those are different rules and none has been pre-registered.

The probe also surfaced a second number worth keeping: **mean window
length is 76.1 hours (IS) and 66.0 hours (OOS)**, with a **44.8% / 47.4%
direction flip rate**. So a bias window runs about three days and flips
roughly every other one — the timeline is not choppy at the window level at
all, which is itself evidence against the premise that rapid 1h bias
flipping is a problem worth filtering.

## Verdict

- **CLOSED as specified.** The rule is vacuous on this chain: 100% keep in
  both eras. Do not re-run it, and do not report "2-of-3 kept 100%, so the
  book is unchanged" as a null result — it is a rule that cannot fail.
- **A window-duration rule is a genuinely untested idea** and is the
  natural successor: with a 76-hour mean and a 45% flip rate, "do not open
  a new bias within N hours of the last flip" is testable and could bite.
  Not pre-registered yet, so not run.
- This is the second time a probe prevented a run today (after PROBE 1's
  wave discovery). The cost of the probe is ~20 seconds.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
