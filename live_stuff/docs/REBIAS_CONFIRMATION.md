# P13 — the re-bias on opposite-swing confirmation: also negative, but
# for a sharper reason than P12. And a correction to record.

`exp_rebias.py`. Pins reproduced first.

## The correction, accepted

The user was right on both counts and I was wrong on both.

**1. "You cannot negate r_multiple" was over-engineered clutter.** A `-r`
screen is a reasonable approximation, and it would have returned the same
negative P12 got — the book was right 26% of the time, so inverting it
loses whatever the exit structure. The mirrored-stop replay is more
rigorous and bought a pedantic point at real time cost. Not argued.

**2. P12 tested the wrong idea entirely.** The user did not mean a blind
flip. They meant a state machine: HTF says long → the buying legs' lows
break → **wait for the next selling swing to CONFIRM** → take a position
in it → when the selling highs break, the trend is turning back → trade
with the original HTF direction again.

That is a different entry bar and a different reason, so it needed its own
run. It got one.

## The state machine as implemented

At each champion entry *t*, find the parent HTF window *(W, d_htf)*.
Scan *W..t* for **confirmed LTF legs in direction −d_htf**. If one exists
and its own defending level is **still intact** at *t*, the state is
FLIPPED and the correct action is the opposite side. If that level has
already broken, the structure is failing and the state returns to ALIGNED.

**The FLIPPED state is common, not rare:**

| | entries | FLIPPED | share |
|---|---|---|---|
| IS | 500 | **316** | **63.2%** |
| OOS | 251 | 136 | 54.2% |

**So over half of all entries already have a confirmed, intact opposing
leg available.** The signal is not rare — it is close to universal. That
alone is worth knowing: by the time the book enters, the opposing
structure has usually already formed.

## The result — every arm negative in both eras

**IS** (control replay +13.1R from 407 trades):

| arm | n | net | **dNet** | **WR** | M |
|---|---|---|---|---|---|
| R1 flip if opposing leg intact | 313 | −196.3R | **−209.4R** | **13.7%** | 221.0 |
| R2a + confirmed <12h ago | 319 | −143.3R | −156.5R | 18.2% | 173.0 |
| R2b + confirmed <36h ago | 312 | −187.1R | −200.2R | 14.4% | 217.0 |
| R3a + decay also ≥ 0.50 | 341 | −137.2R | −150.3R | 19.4% | 180.1 |
| **R3b + decay also ≥ 0.75** | 365 | **−21.5R** | **−34.6R** | **27.9%** | 71.6 |

**OOS** (control +18.3R from 202):

| arm | n | net | **dNet** | **WR** |
|---|---|---|---|---|
| R1 | 165 | −65.1R | −83.4R | 17.6% |
| R2a | 165 | −37.1R | −55.4R | 21.8% |
| R2b | 164 | −64.0R | −82.3R | 17.7% |
| R3a | 175 | −20.1R | −38.4R | 24.6% |
| **R3b** | 182 | **−7.8R** | **−26.0R** | **26.4%** |

**0 of 10 arms positive. Nothing clears a null; everything is negative.**

## Why this is a *better* negative than P12's

P12's blind flip died at **12.6% WR** — worse than random, which only
says "you inverted a book that was usually right."

**The re-bias confirms the flip, and the agreement is the finding.** R1
lands at 13.7% IS / 17.6% OOS, statistically the same failure mode as
P12's 12.6%. Adding the *confirmation requirement* and the *intactness
requirement* — two real pieces of structure the user's logic supplied, and
neither of which P12 had — moved the result by one percentage point.

**And the arms converge as evidence accumulates.** R1 (decay irrelevant,
confirmation only) is worst. Adding decay agreement moves it monotonically
back toward the control: R3b, which fires on only 27% of IS entries, sits
at −34.6R, the smallest loss of any arm. **More evidence required before
switching = less damage from switching.** That is a coherent, ordered
result across five arms and two eras, not a scatter.

## What it settles

**The opposite side is not just un-attractive after decay — it is
un-attractive whenever the opposing structure is confirmed and intact,
which is most of the time.** The user's logic is sound as market
reasoning and the data does not reward it, because on this book the
opposing leg forming is not evidence that the trade is over. It is
evidence that the market is two-legged, which is what a range is.

**This is the same wall as P9 and P11 from a third direction.** P9: the
book's winners are in non-trending tape. P11: intact structure is where
the R is, and decay is where the losses are. P13: the confirmed opposite
structure — the thing decay would send you to — is *worse* than doing
nothing. **Three independent measurements now say the same thing: this
book's edge is in the aligned, non-trending, intact-structure state, and
every attempt to route away from that state loses money.**

## Recommended

**Do not build the regime switch.** P12 and P13 together are a thorough
kill of the whole family — blind flip, magnitude flip, confirmed flip,
age-gated flip, double-confirmation flip. The remaining untested variants
(thresholds on intactness, a flip that also shortens the stop) are
refinements of a mechanism that loses 26–209R in every configuration tried.

**The one live lead remains P12's M1 asymmetry** (IS +72.5R, OOS −6.3R),
and the one open idea remains **"busy but no trade"** (signal suppression,
zero repo hits).
