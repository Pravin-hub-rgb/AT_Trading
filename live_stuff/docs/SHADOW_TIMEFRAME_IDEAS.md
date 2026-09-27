# Shadow timeframes — 30m and 2h as evidence, not as the plane

**Date:** 2026-09-27 · **Status: design + pre-registration, written BEFORE the first shadow-TF run** · **Constraint: execution stays 15m LTF / 1h HTF / min_bars 50.**

## The constraint, and why it is the right one

Everything measured so far says the shipped pair is best:

- `tf_family` (log 106): 15m/1h is best on net in 11 of 12 era×lane comparisons;
  the single exception is default-off age10.
- `min_bars` forensic (log 107): the LTF is the entry generator, and coarsening
  it is not compensated by anything upstream.

So 30m and 2h are **not** candidate planes. They are candidate *information*:

> Keeping entries on 15m and context on 1h, does adding 30m or 2h evidence change
> which of the already-generated 15m entries are worth taking?

## What makes 30m structurally special (and 2h not)

30m is a strict **sub-interval** of 1h: the 1h bar `[T, T+3600)` is exactly the
30m bars `[T, T+1800)` and `[T+1800, T+3600)`. So at instant `T+1800` the 1h
bar is **half known** — its open and its first leg's high/low/close are known,
the second leg is not. That is not "finer resolution", it is a **half-bar
checkpoint on the existing 1h chain**, and it is why the user's hint (30m sits
just below 1h, so deduce something from it early) is structurally sound rather
than merely plausible.

2h is the opposite: strictly coarser, strictly more lag. Always "already known",
so a pure conviction layer, never an entry trigger.

### The hard limit: 30m can veto, it cannot enter earlier

The C15 window gate derives to

```
entry_instant (bar_ts + 900) > htf_close_instant (s + 3600)

## Idea space

Numbered so they can be cited. S1-S4 are pre-registered below; S5-S7 are queued
and explicitly NOT run in this pass.

**S1 — 30m leg-agreement veto.** At entry take the direction of the last *closed*
30m bar. Veto when it opposes the 1h swing direction. Mechanism: parent trend
and immediately-preceding sub-bar disagree ⇒ 1h context is fraying and the 15m
trigger is late.

**S2 — 30m early-flip veto (the user's idea, sharpened).** Detect whether the
*current, still-forming* 1h bar's first 30m leg has already broken the prior 1h
swing level in the trade's direction. A leading read on the *next* 1h flip, used
as a veto: do not take a 15m entry that a forming 1h bar is about to contradict.
Causal — the first leg has closed.

**S3 — 2h slow-context veto.** Veto when the last closed 2h swing direction
opposes the 1h swing direction. Mechanism: 1h trends fighting the 2h chain are
counter-trend inside a slower move.

**S4 — agreement stacking / tail removal.** Bucket every 15m entry by how many of
{1h, 30m, 2h} agree. Mechanism: the harmful trades are not in the signal, they
are in the *weakly-confirmed tail*. Composition question, not a signal
question — and the cheapest and most falsifiable of the four.

**S5 (queued) — 30m chop as a smoother regime read.** The engine's 15m chop has a
30m analogue. **Low prior:** log 105 proved the HTF chop/garch windows are
inert, so expect inertness and do not be surprised.

**S6 (queued) — 30m/2h shadow book as a feature.** Run the full F3 strategy
independently and use *its signal presence* at each 15m entry as a binary
feature. A true ensemble rather than a plane change. Ambitious, hard to validate.

**S7 (queued) — 2h in the window machinery.** A slower swing chain for the
16-day window and trail. Changes window semantics, highest blast radius, last.

## Pre-registration for S1-S4 (fixed now, before running)

**Arms.** One shipped 15m/1h book per lane per era (champion, utcsat, age10; IS
+ OOS), identical to the validated control — 500t/+325.8, 454t/+358.9,
130t/+435.7 IS and 279t/+70.2, 253t/+60.2, 76t/+43.2 OOS. Each entry is then
labelled by S1-S4 and the book re-reported by bucket.

**No thresholds to search.** Every predicate here is binary (agrees / opposes).
Deliberate: the `6.026` lesson from the wick gate was that a searched threshold
needs a stability window and a post-hoc marker. A binary predicate has no knob
to overfit, so that failure mode is structurally unavailable.

**What counts as a hit.** All three:
- the split holds in the **same direction in both eras**, and
- the retained bucket's avgR beats the dropped bucket's by a margin whose
  **bootstrapped 95% CI excludes zero**, and
- it does not depend on a bucket with n < 30.

**Hard priors from existing work, so nothing is rediscovered:**
- Removing trades is **not** the same as gating them. The wick work measured
  path-true skip at −39.0R IS where gray was +28.1R, because skip frees the slot
  and admits a *replacement*. A post-hoc bucket measurement is a **composition**
  result only.
- So if any of S1-S4 passes Phase 1 it must then be re-run **in-engine** and
  compared gray-vs-skip before being called a result. Phase 1 can only say "this
  part of the book is worse", never "this filter helps".

---

# RESULTS — Phase 1 (run 2026-09-27, 90s, all 6 controls EXACT)

Harness `exp_shadow_tf.py` → `_shadow_tf.json`. Shipped 15m/1h books reproduced
exactly (500t/+325.8, 454t/+358.9, 130t/+435.7 IS; 279t/+70.2, 253t/+60.2,
76t/+43.2 OOS). The causality helper is unit-checked before use (5 boundary cases
+ empty input), and swing stamps use `confirmed_at_idx` — verified equal to
`confirmed_at_time` on 300/300 sampled swings — never the backdated
`seg.start_idx`.

## S1 — 30m bar direction vs trade direction

Pre-registered prediction: **opposing trades should be worse.**

| lane | era | agree n / avgR | oppose n / avgR | diff | 95% CI | p |
|---|---|---|---|---|---|---|
| champion | IS | 431 / +0.60 | 69 / **+1.00** | −0.41 | [−2.64, +1.22] | 0.745 |
| utcsat | IS | 389 / +0.71 | 65 / **+1.26** | −0.55 | [−2.86, +1.17] | 0.652 |
| champion | OOS | 235 / +0.33 | 44 / **−0.18** | +0.51 | [−0.44, +1.34] | 0.270 |
| utcsat | OOS | 213 / +0.33 | 40 / **−0.23** | +0.55 | [−0.38, +1.36] | 0.219 |

**FAIL on two counts.** The sign *flips* between eras on both live lanes — in IS
the opposing bucket is the better one, in OOS the worse one — so the
same-direction gate is not met. And neither era is individually significant. The
near-mirror of the IS and OOS diffs with CIs this wide is what noise around zero
looks like, not a mechanism.

`age10` opposing buckets are n=15 (IS) and n=10 (OOS) — below the pre-registered
n<30 floor, so they carry no weight and are not read.

## S3 — 2h swing direction vs trade direction

Same pre-registered prediction: opposing should be worse.

| lane | era | agree n / avgR | oppose n / avgR | diff | p |
|---|---|---|---|---|---|
| champion | IS | 312 / +0.52 | 188 / **+0.87** | −0.36 | 0.528 |
| utcsat | IS | 290 / +0.63 | 164 / **+1.07** | −0.43 | 0.486 |
| age10 | IS | 67 / +2.67 | 63 / **+4.08** | −1.41 | 0.393 |
| champion | OOS | 178 / +0.13 | 101 / **+0.47** | −0.34 | 0.477 |
| utcsat | OOS | 159 / +0.17 | 94 / **+0.36** | −0.19 | 0.717 |
| age10 | OOS | 37 / +0.24 | 39 / **+0.88** | −0.65 | 0.277 |

**The direction is consistent — 6 of 6 cells, both eras, all three lanes — and it
is the *opposite* of the pre-registered mechanism.** Trades that push against the
slow 2h context are consistently the *better* ones.

**It is still not adoptable.** Every p is above 0.27, every CI straddles zero, and
the pre-registration required a CI excluding zero. What is honestly reportable is
the *pattern*: this system mildly prefers counter-2h context, which fits a
swing-flip/fade system better than a trend-follower at the slow scale. That is an
interpretation, not a measured edge, and the effect size (0.19-0.65 avgR) is small
enough to be nothing.

## S4 — agreement stack (1h always agrees, plus 30m, plus 2h)

| lane | era | k1 (neither) | k2 (one) | k3 (both) |
|---|---|---|---|---|
| champion | IS | 21 / +0.37 | 215 / **+1.01** | 264 / +0.38 |
| utcsat | IS | 18 / +0.76 | 193 / **+1.19** | 243 / +0.48 |
| champion | OOS | 15 / −0.16 | 115 / **+0.38** | 149 / +0.19 |
| utcsat | OOS | 16 / +0.13 | 102 / +0.20 | 135 / **+0.28** |

Not monotone, and not stable: k2 leads in three of four live cells but loses to
k3 in OOS utcsat. Every k1 bucket is n<30 and excluded by the pre-registration.
`age10` runs the *opposite* way on IS (k1 4.85 > k2 4.53 > k3 1.85 — more
agreement, worse), a second reason not to generalise from it.

## Verdict — a null, reported as a null

| predicate | same direction both eras? | any CI excludes zero? | verdict |
|---|---|---|---|
| S1 30m agreement | **no** (sign flips) | no | **fail** |
| S3 2h agreement | yes (6/6) but **backwards** | no | **fail, pattern noted** |
| S4 stack | no | no | **fail** |

**No shadow-timeframe predicate earns Phase 2.** The pre-registration said a null
would be reported as one and not re-run with extra predicates until something
fires, so no additional split was tried after seeing these numbers. The obvious
"keep trades where 30m and 2h both oppose" is exactly the fishing the wick `6.026`
episode warned about, and S3's own numbers show why: that effect sits inside the
noise band.

Two structural reasons the CIs are this wide, so the null is read correctly: the
opposing buckets are small (10-188 trades) and high-variance, and the IS era is
already 3.67 years / 500 trades, so there is no obvious way to buy more n from the
same data.

**Honest summary: 30m and 2h add no usable discrimination to the shipped 15m/1h
book as *veto* evidence.** That says nothing about the queued S6 (shadow book as a
feature — a genuinely different object) and nothing about the excluded
early-entry idea, which is a causality question rather than a composition one.

## What I would do next, and why it is not this

- **Do not** add more agreement predicates. The mechanism is absent, and S3's
  direction already agrees in all six cells without ever being significant.
- **S6 (shadow book) is the interesting survivor** because it is a different
  object: not "does the 30m bar point the same way" but "did an independent
  30m/2h system also want a trade here". Independence is the part that might
  carry information, and it is the one thing S1-S4 never tested.
- **The early-entry idea stays excluded** until someone deliberately designs a
  C15 experiment, with its own pre-registration and its own review.

- The baseline is the **raw** shipped book, not the wick gate. Shadow-TF numbers
  must not be read as incremental to a different, already-validated filter.

**Reporting.** n, net, avgR, PF, maxDD, wr, dnet/yr, retained fraction, and R
removed. Bootstrap every per-trade comparison (20k resamples, corrected two-sided
p per Rule 9). With ~500 IS / ~279 OOS trades these CIs will be wide and a null
is the likely outcome — that is a legitimate result, to be reported as one and
not re-run with extra predicates until something fires.

```

so **the 1h bar must already be closed** before a 15m entry is permitted. A 30m
half-bar therefore *cannot* enter earlier without breaking that gate — and this
repo has a documented history of causality mistakes that cost several cycles
(AGENT_COORDINATION "Causality rule"; log 104's `2700` leak).

| use of 30m | status |
|---|---|
| **veto** an already-generated 15m entry | safe, causal, in scope |
| **enter earlier** on a 30m signal | **out of scope** — breaks C15, needs its own pre-registered causality experiment |

The early-entry version is the more valuable idea and the more dangerous one.
Excluded from this pass deliberately, not forgotten.
# END_MARKER
