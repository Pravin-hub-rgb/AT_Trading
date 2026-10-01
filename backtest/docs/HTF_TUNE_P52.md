# Giving the 1h layer the 15m layer's treatments — and a lookahead that looked like the win of the session

> Runs 2026-09-29. Harnesses `exp_htf_tune.py` (P52), `exp_streak_gate.py`
> (P53). Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## Why this was tried

P3 established that the 1h layer earns nothing on its own — FLIP +1.9R IS
and **−23.6R OOS**, B2 −49.6R and −21.7R. Every brake in the engine was
tuned on the 15m side; the 1h side runs raw (`htf_rr=3.0`,
`window_end="exit"`, `cap_days=16`, no entry filter, no cooldown, no streak
management). The layer was never scored, so it was never tuned. The owner's
question was exactly right: **give the 1h layer the treatments the 15m layer
already has, and see if that changes it.**

It does not. And the way it fails is worth more than the result would have
been.

---

## P52 — the number that looked like the best of the session

Gating the 15m book on the 1h layer's own losing streak:

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| skip while 1h streak ≥ 1 | **+180.9R** PF 5.17 | **+94.8R** PF 4.45 | **+164.3R** PF 5.69 | **+77.6R** PF 4.49 |
| skip while 1h streak ≥ 3 | +80.3R PF 3.16 | +60.5R PF 2.68 | +76.5R | +45.8R |
| window's 1h leg reached 3R | +112.0R PF 4.71 | +82.3R PF 3.46 | +80.9R | +72.1R |

**4/4 positive, monotone in the right direction, PF up to 5.69, and
+180.9R in champion IS is 0.93 × M.** By every yardstick this sheet uses,
that is the best result of the entire session.

**It is also a lookahead, and it was not accepted.**

## P53 — the causality rebuild, and what it cost

P52 counted a leg toward the streak if `leg.entry_ts <= window_start`. But a
leg that has *started* and not yet *closed* has no known outcome. The only
defensible definition is `leg.exit_ts <= window_start` — the leg had
finished before the window opened.

| skip while 1h streak ≥ 1 | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| P52, `entry_ts <= start` | **+180.9R** | **+94.8R** | **+164.3R** | **+77.6R** |
| **P53, `exit_ts <= start`** | **−234.2R** | **−91.9R** | **−261.0R** | **−71.3R** |

**Every cell flips, and the sign flips with it.** The entire apparent win was
read from the future. Under the causal rule the arm is 4/4 negative and
monotonically useless at every setting from 1 to 6.

### The probe, and why it is flat

P53 also re-ran each arm with the cutoff moved one hour *earlier*, which
hands the gate strictly more information. **A causal rule must get worse or
stay flat when given the future; an arm that improves under the probe is
leaking.** The probe is flat to within a trade or two on almost every cell
(`utcsat IS streak≥3` moves 302→303 trades and +201.8R→+204.8R, which is
one window boundary), which is what a genuinely causal rule looks like.

**The lesson is the repo's own, applied to a result I produced myself:** a
big number is not evidence of an edge, it is evidence that something was
counted. This is log 119's label-leakage rule and log 124's void-run rule
arriving on a result I was actively tempted to keep.

## A4 is not a rule, it is a hindsight measurement

"Keep only windows whose 1h leg reached 3R" scored 4/4 positive. It is
**only knowable at the window's end.** It is a measurement of what windows
turned out to be worth, which is genuinely interesting, and it must never be
shipped. Recorded here so the number is not rediscovered and mistaken for a
filter.

## PART B — decay computed on the 1h chain to gate the window

The untried idea: decay has only ever been computed on 15m buying legs to
gate 15m entries. Computing it on the 1h leg chain to decide whether a
window opens at all is a different question.

| 1h-decay < | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 0.50 | 143t −276.5R | 42t −48.0R | 131t −301.6R | 37t −47.7R |
| 0.75 | 251t −235.2R | **95t +25.5R** | 235t −243.1R | **88t +25.9R** |
| 1.00 | 350t −185.1R | **164t +31.6R** | 322t −198.1R | **139t +25.5R** |

**Era-flipped and dead** — the same shape as every other feature in this
thread that gates by structure: negative in both IS cells, mildly positive
in both OOS cells, magnitude ~0.13 × M.

## A1 is dropped, not reported

P52's cooldown arm printed byte-identical books at every setting from 1 to
13 days. That was a harness bug — `last_bad` was computed once from the whole
book and then reused, so every window saw the same value. It is not an
inert parameter, and it is not reported as one.

## Verdict

**Both of the owner's ideas were tested. Neither survives.**

- **Applying the 15m layer's treatments to the 1h layer**: the streak gate
  looked like +180.9R and is −234.2R once it is causal.
- **Decay on the 1h chain gating the window open**: era-flipped, ~0.13 × M.

This is the fourth time this session that a large or clean-looking result
turned out to be an artefact rather than an edge, and the second time the
artefact was in a file I wrote. The standing rule is the one log 119
established: **an arm that partitions trades using any realised field is void
on sight** — and here it extends to *the gating window's own inputs*, which
must be knowable at the instant the window opens.

The 1h layer stays untuned, and that is now an evidence-based decision
rather than an oversight. Nothing adopted; champion unchanged.
