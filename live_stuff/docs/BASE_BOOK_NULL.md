# P5 — the base-book null. M is larger than the book.

`exp_base_null.py`. Pins reproduced first, both exact (IS 500t/+325.8R
NET, OOS 279t/+70.1R NET). Published as run, whatever it says.

## The result

Move-block bootstrap, block = 20 trades, 10,000 draws, seed 20260928.
Blocks of consecutive trades, resampled with replacement until the trade
count is restored — this preserves within-block serial dependence, the
win/loss run structure, the streak process and the trade count, none of
which a shuffle preserves.

| | observed | null mean | null p05\|net\| | **M (p95)** | percentile | p |
|---|---|---|---|---|---|---|
| **IS** | **+325.8R** | +316.5R | 159.4R | **479.9R** | 45.7th | **0.914** |
| **OOS** | **+70.1R** | +69.2R | 6.2R | **193.4R** | 47.9th | **0.958** |

**The champion's own net sits at the 46th and 48th percentile of a
reshuffle of itself.**

| | M |
|---|---|
| **IS** | **479.9R** |
| **OOS** | **193.4R** |

## What this means, stated plainly

**The champion's +325.8R IS is not distinguishable from reordering its own
500 trades. Neither is +70.1R OOS.** The book lands dead centre of its own
null distribution in both eras. The null mean is +316.5R against an
observed +325.8R — a difference of nine R on a three-hundred-R book.

This is not a statement that the book has no edge in some deeper sense. It
is a statement about **what the block bootstrap can resolve**. A book of
500 trades with a 30% win rate and heavy tail has an enormous reshuffle
variance, and a single net figure cannot distinguish skill from luck at
this sample size. **The null is wide because the tail is wide.**

## The consequence for everything in this repo

**Every dNet result must clear M before it counts.**

| | M |
|---|---|
| IS dNet must exceed | **479.9R** |
| OOS dNet must exceed | **193.4R** |

Now look at the registry against that bar:

- The `exp_trail_half=1` result (`EXPERIMENT_LOG.md:20`) — IS **+325.8 →
  +429.6**, OOS **+70.2 → +110.5** — is a **+103.8R** IS dNet and a
  **+40.3R** OOS dNet. **Both are inside the null.** The OOS maxDD halving
  (−42%) that made it look compelling is not accompanied by a net move
  that clears M.
- `partial_r` (multi sw10 +247.9 vs no-partial +163.6, = **+84.3R**) is
  inside the null in both eras.
- The `live_R` floor, rejected at 0/7, was rejected for real reasons and
  would in any case have been inside M.

**This does not mean every one of those is wrong.** It means the repo has
been scoring arms against a number whose significance was never
established, and several of the headline wins are inside chance.

## Why a shuffle would have flattered the book — and why this one does not

`IS_IT_RIGHT.md` reports OOS ACF lag-1 = +0.498. A plain shuffle destroys
that serial dependence, which collapses the reshuffle variance and makes
the observed net look several standard deviations out. **The block
bootstrap is the conservative choice and it is the honest one.** The
existing `exp_montecarlo_dd.py` nulls drawdown and streak only, never the
book's net; this is the first null on the number everything is scored
against.

## What would actually settle it

1. **The forward slice.** `data/forward/bybit/` has been left untouched
   all session. It cannot confirm anything until M exists — and M now
   exists, so it can. A single family-wise pre-registered pass there is
   the only out-of-sample arbiter left. **This unblocks the item the
   queue has been calling "one look only, ~60-70 trades" — with M=193.4R
   a 60-trade slice can rule things OUT and confirm nothing, which is
   exactly what was already suspected.**
2. **A metric with less reshuffle variance.** Net R on 500 trades is
   tail-dominated. Per-year, per-regime, or ex-best-5 decompositions
   would have far tighter nulls, and the repo already computes several of
   them. The right question is not "is the book good" but "which
   decomposition of the book survives its own null."

## The uncomfortable summary

The programme has spent a long time improving a number that its own
reshuffle distribution cannot distinguish from luck. That is worth knowing
and worth publishing. It is not a reason to stop — it is a reason to
**stop trusting single net-R deltas**, and to require either a forward
pass or a variance-reduced statistic before calling anything a result.

One caveat on method: the block length of 20 was pre-registered to match
`exp_montecarlo_dd.py`, not tuned. A shorter block would widen the null
further; a much longer one would narrow it and eventually destroy the
serial structure the method exists to preserve. 20 is a reasonable middle
but it is a choice, and a sensitivity check over block lengths is the
obvious next thing.
