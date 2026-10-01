# P12 — decay as a regime switch. The flip is decisively dead. The
# asymmetry arm is the most interesting thing found in days.

`exp_decay_switch.py`. Pins reproduced first. Seven arms, three
thresholds, both eras.

## The technical trap, handled first

A direction flip cannot be tested by negating `r_multiple` — flipping a
long to a short moves the stop to the other side and the target with it,
so it is a different trade. **Every flip arm here is a path-true 1m
replay**: enter opposite at the same bar, mirrored stop at `risk`, target
at 3R (the book's own `htf_rr`), first touch wins. `r_multiple` is never
negated anywhere.

**And the control for that replay is damning on its own:**

| | n | net |
|---|---|---|
| **CONTROL replay** (same side, 3R target) | 407 | **+13.1R** |
| champion (real trail exits) | 500 | **+325.8R** |

**Replacing the trail with a 3R target costs the book 313R.** The repo
already found this — `EXPERIMENT_LOG.md:669`, Stage 2: "the structural
trail/holding logic is the dominant source of payoff; simple fixed exits
do not reproduce the edge." So the replay control is a weak book, and any
flip arm has to beat *that*, not the champion.

## U2 — the flip. Dead, and badly.

| decay ≥ | IS net | IS dNet vs control | IS WR | OOS net | OOS dNet |
|---|---|---|---|---|---|
| 0.50 | **−203.3R** | **−216.5R** | **12.6%** | — | — |
| 0.75 | −62.4R | −75.5R | 24.9% | +15.2R | +0.0R |
| 1.01 | — | — | — | +15.2R | **+0.0R** |

**At the most useful threshold the flip produces −216R and a 12.6% win
rate** — worse than random, which is what happens when you systematically
invert a book whose original side was right 26% of the time. And at the
tightest threshold it changes literally nothing (+0.0R dNet), because
`decay >= 1.01` is empty.

**The user's intuition — "trend might be changing, so take the other
side" — is false here.** High decay means the *up-leg structure* is
being taken out. It does not mean the next move is down. P11 already
showed the forward edge at high decay is −0.16R IS / −0.63R OOS, i.e.
worse, not reversed. **A switch needs the opposite side to be right; here
it is not merely wrong, it is anti-correlated.**

## U1 — the gate. Also dead.

| decay ≥ | IS net | dNet | OOS net | dNet |
|---|---|---|---|---|
| 0.50 | +88.6R | **−237.2R** | — | — |
| 0.75 | +383.9R | +58.1R | +78.5R | +8.3R |
| 1.01 | — | — | +78.5R | +8.3R |

**At 0.75 it looks like +58R IS / +8R OOS — both positive, which would
normally pass.** But it clears nothing (M = 475.4R), and P11 already
showed the `decay ≥ 0.75` cohort is the *worst* one (20.3% WR) — so this
"gain" is the same trade-deleting effect that killed `max_concurrent`,
`campaign caps` and `window_r_cap`. **Falsifier (d) fires: the gain is
from deleting trades, not from the signal.**

## M1 — the asymmetry arm. The interesting one.

`broken_buying_lows − broken_selling_highs`, i.e. a *directional
imbalance* rather than a magnitude.

| | n | net | dNet | WR | M |
|---|---|---|---|---|---|
| **IS** | 373 | **+398.3R** | **+72.5R** | **32.2%** | 507.2 |
| **OOS** | 196 | +63.9R | **−6.3R** | 26.0% | 142.1 |

**IS +72.5R at 32.2% WR — the best single number any arm produced today.
OOS −6.3R.**

**This is the one arm whose sign disagrees across eras, so by the
pre-registered falsifier (b) it is not a finding either.** But it is
directionally interesting in the right way, and it is the arm that
deserves a follow-up rather than a closure: asymmetry is the only version
of the decay idea that measures *which way* the structure is failing
rather than *how much*, and the flip result above is strong evidence that
"how much" is not the informative part.

## M2/M3/M4 — the "obvious" refinements, all inside the null

| arm | IS dNet | OOS dNet |
|---|---|---|
| M2 velocity ≤ 0 (decay not rising) | +31.0R | +15.8R |
| M3 decay<0.5 OR age>2d | +25.9R | +1.5R |
| M4 drop if decay high AND 1h underwater | +34.7R / +55.7R | +12.5R / +8.3R |

M2 is positive in **both** eras — the only one that is. It is also tiny,
inside M in both, and it is essentially "skip trades while decay is
actively rising", which is the same family as the `1h underwater` floor
already rejected 0/7 in `CHAMPION_FLOOR_REJECTED.md`. **Not promoted.**

## The honest summary

**Every arm the user proposed fails, and the flip fails hardest and most
informatively.** What the sweep actually establishes:

1. **Decay magnitude is not a directional signal.** It says the up-leg
   structure is deteriorating; it does not say the next move is down, and
   inverting on it is anti-profitable.
2. **Asymmetry might be.** The one arm measuring direction rather than
   magnitude is the only one with a large IS number, and it has the wrong
   sign in OOS. That is a lead, not a result.
3. **Everything positive in this sweep is trade-deletion.** U1 and M4 in
   particular are the familiar brake effect, inside M in both eras.

**And the control row is the most important number in the file:** the 3R
replay control is +13.1R against the champion's +325.8R. Any future
flip-style arm has to be compared against a book that already lost 313R
to the replay simplification, which is a high bar that hides real effects.

## Recommended follow-up, and it is narrow

**Do not build a regime switch from decay magnitude — that direction is
closed by U2, decisively.**

**The one live lead is M1**, and it should be run as a pre-registered
two-sided test at fixed thresholds (asym ≤ 0, ≤ +0.25, ≥ +0.5) with the
two-era sign agreement required, before anything is built on it. If it
does not hold both eras it joins the P9/P11 family of descriptive signals
that locate the book's R without predicting it.
