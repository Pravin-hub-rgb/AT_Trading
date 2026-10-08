# Idea: a size channel, and why it is the only thing left that matters

Date: 2026-10-08. This is a design note, not a result. Nothing adopted, nothing
built.

## The problem, stated by the repo itself

`NEXT_ROUND_BRIEF.md` §7 lists it as a known blocker:

> **No size channel** — `v18_streak_halt.py` has zero hits for
> equity/size/notional/qty. **Any sizing change has no execution channel**, and
> sizing cannot change net R in R-units anyway (P9). Kelly, vol-targeting and
> fixed-fraction are **not answerable in this repo**.

Verified still true today:

| file | size/qty/notional/equity hits |
|---|---:|
| `v18_streak_halt.py` | **0** |
| `unified.py` | 4 — all `hrisk`, which is a distance not a quantity |

The engine books a trade as `{entry_price, sl, target, r_multiple}`. `r_multiple`
is *already* the normalised unit the whole repo reports in. **There is no place
to put a size because the engine never had one.**

## Why this matters more than any filter, and it is not close

Everything this session tested is a **trade-selection** question: keep this
trade, drop that one. That entire family of questions has been exhausted — nine
consecutive measurements adopted nothing, and the repo's own history is 31
experiments where one rule survived period control and still failed family-wise.

**Position sizing is the only lever that is not trade selection.** It changes the
shape of the equity curve without removing a single trade, which is why it is the
one thing the `EQUITY_LENS_EXT_AND_NOHALT` governance rule keeps pointing at and
cannot resolve: the halt decision is a drawdown-budget decision, and drawdown is
a function of size.

Three observations from today that make this concrete rather than abstract:

1. **The cap experiment proved the negative case.** `exp_max_concurrent` from 2
   to 8 costs R in both eras and does **not** reduce drawdown above cap=4 — IS
   drawdown stays at 13.4R regardless. **Capping trades is not risk control.**
   It deletes return and leaves the drawdown.

2. **The blend experiment showed the positive case.** Cutting A to half size plus
   B at half size takes OOS max drawdown from 8.1R to 2.3R. **Most of that is
   sizing**, not diversification — halving A alone would get most of the way.

3. **The book holds up to 11 concurrent positions.** Total concurrent exposure is
   unbounded in the backtest and bounded only by capital in reality. **The
   backtest cannot express the risk the live account actually carries**, and that
   gap has been open the whole time.

## What a size channel would have to do

Not a `qty` field. A channel that answers one question: **given the account and
the book's own drawdown history, how much is risked on trade N?** That needs:

- an account-equity input the engine does not have
- a drawdown-aware rule, not a constant fraction — the same R that is correct at
  +533R is wrong at a −15R drawdown
- and it must not change `r_multiple`, because the repo's entire measurement
  system is R-denominated and a size change that moved net R would silently
  invalidate every pin in the registry

That third constraint is the real one. **A size channel that alters R would make
the whole results DB meaningless.** It has to be a parallel output, not a
multiplier on the existing one.

## The honest scope

This is **architectural work on the engine**, not a sweep. It is:

- the largest change this session would make
- untestable against the existing pins by construction
- and the one thing where a wrong answer costs real money rather than a wasted
  afternoon

It is also, on the evidence above, the only remaining direction that is not
trade selection. Every other lever in this repo has been pulled.

## What I would NOT do

I would not build it and then tune it. The pattern this session established nine
times over is that a knob tuned against an answer already in view produces a
number that survives scrutiny for one commit and then does not.

If it is built, the sizing rule should be derived from the drawdown budget the
owner already writes down in `EQUITY_LENS_EXT_AND_NOHALT.md`, not fitted to the
backtest — which means the rule comes first and the implementation second, and the
implementation is not worth starting until the rule exists.

**Nothing built, nothing adopted.**