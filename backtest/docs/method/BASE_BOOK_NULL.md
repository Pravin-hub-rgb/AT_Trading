
> ## !! SUPERSEDED 2026-10-10 - the M in this file is WRONG BY ~2x
>
> `method/NULL_AUDIT_P5.md` re-derived the null on the book this file NAMES but
> does not use. Three separate problems, any one of which invalidates the bar:
>
> 1. **The pins quoted here belong to a different book.** This file's first
>    paragraph says "IS 500t / +325.8R NET, OOS 279t / +70.1R NET". That is
>    `champion_multi_sw10`. The shipping book `fsent_champ_long` is 528t / +533.37R
>    IS and 311t / +239.59R OOS. The quoted pins do not match the registry either -
>    `champion_multi_sw10` reads 502 / +279.33 there.
> 2. **M is roughly half the correct size.** Re-derived on the real book:
>    **M = 771.09R IS and 384.36R OOS**, against the 381.7 / 205.5 quoted below.
>    Every dNet in the repo has been judged against a bar half its real size, and
>    the error runs in the permissive direction.
> 3. **M is an absolute R figure and cannot be a portable bar.** A null's width
>    scales with the book's trade count and its per-trade spread -
>    `BOOTSTRAP_NULL_P63.md` already says that comparing a fixed null against a
>    different-length run "is comparing two different things", and the registry
>    then went on quoting M as a fixed threshold anyway.
>
> **On the absolute test nothing in the fsent family clears the corrected bar,
> which is expected and is not the interesting result.** The shipping book sits at
> the 58th and 45th percentile of a reshuffle of its own trades. The question a
> candidate actually needs answered is whether swapping the parent's trades for its
> own beats swapping them at random. That is the paired permutation, and there
> `fsent_champ_long_mcloff` returns p = 0.0312 IS and p = 0.0117 OOS - the only
> book in the family significant in both eras.
>
> The original run below is kept as history. It is correct for the book it was
> measured on and it is not a bar for the book that ships.

# P5 — the base-book null. M is larger than the book.

> **UPDATED 2026-10-01. M has been re-derived on the shipping book. Read the
> second table before using any number from this file.**
>
> C16 changed the shipped SL pivot from the origin pivot to the leg pivot, so the
> book this null was computed on is no longer the book that trades. The original
> result is kept below as history; it is correct for the origin book and wrong as
> the programme's bar.
>
> Method is unchanged and cannot drift: same block bootstrap, block 20 trades,
> 10,000 draws, seed 20260928, and `exp_base_null_leg.py` imports P5's own
> `block_bootstrap_nets` rather than reimplementing it.
>
> | era | **origin (superseded)** | **leg (current bar)** |
> |---|---|---|
> | IS | 500t / +325.8R / **M 479.9R** | 499t / +239.1R / **M 381.7R** |
> | OOS | 279t / +70.1R / **M 193.4R** | 280t / +72.8R / **M 205.5R** |
>
> The leg-book null in full:
>
> | era | observed | null mean | null p05\|net\| | **M (p95)** | percentile |
> |---|---|---|---|---|---|
> | IS | **+239.1R** | +218.6R | 62.3R | **381.7R** | 41.0th |
> | OOS | **+72.8R** | +77.1R | 6.9R | **205.5R** | 50.3rd |
>
> **The shipping book is indistinguishable from a reshuffle of itself in both eras,
> exactly as the origin book was.** Origin 46th and 48th percentile; leg 41st and
> 50.3rd. C16 moved the in-sample net by 86.7R and changed this picture not at all,
> because the question being tested is whether the trade ORDER carries information.
> It does not. The null is wide because the tail is wide.
>
> One correction to the direction argument made when this was re-derived. The leg
> null was expected to be uniformly narrower, on the reasoning that fewer trades
> and smaller per-trade R imply a tighter band. That holds in sample, where M
> falls from 479.9R to 381.7R, and fails out of sample, where it widens from
> 193.4R to 205.5R because the leg slice carries 280 trades rather than 279. It was
> reasoning presented as a result and should have been labelled as such.
>
> **Every dNet result must clear M before it counts** — and from 2026-10-01 that
> means M = 381.7R IS and M = 205.5R OOS.
>
> The original P5 run follows, unchanged, for the record.

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

- The `exp_trail_half=1` result (`method/EXPERIMENT_LOG.md:20`) — IS **+325.8 →
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

`method/IS_IT_RIGHT.md` reports OOS ACF lag-1 = +0.498. A plain shuffle destroys
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
