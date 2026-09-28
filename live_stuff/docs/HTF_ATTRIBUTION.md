# P3-A — the 1h window is not decoration. It is the whole edge.

`probe_htf_attribution.py`. Answers the user's challenge directly:

> "the 15m layer trades inside a window that is DEAD 70% of the time, and
> we still get +325R — so either the 1h window contributes none of that
> R, or we are missing something."

**The second horn. And the mechanism is now named.**

## Q3 — is the gate binding? Yes, overwhelmingly

| | IS | OOS |
|---|---|---|
| cascade (1h-gated) | **396t +227.5R**, PF 1.87 | **242t +22.7R**, PF 1.14 |
| **same 15m engine, ungated** | 843t **+17.0R**, PF 1.04 | 530t **−24.7R**, PF 0.91 |
| gate effect | **+210.5R** | **+47.4R** |

**The 1h window is not decoration. It converts a coin-flip into a book.**
The same 15m engine, same swings, same exits — remove the window and IS
goes +227.5R → +17.0R and OOS goes **positive → negative**. Half the
trades die, and the survivors are the ones worth having.

**So nothing is being missed. The +325R is not the 15m layer's — it is the
1h window's, collected in 15m clothing.**

## Q2 — where that R actually comes from

Cascade R attributed to what its parent window ultimately did:

| window outcome | IS | | OOS | |
|---|---|---|---|---|
| | n | net | n | net |
| **target (+3R)** | 97 | **+231.4R** (WR 55.7%) | 39 | **+87.4R** (WR 53.8%) |
| **sl (−1R)** | 187 | **−133.6R** (WR 8.6%) | 113 | **−63.5R** (WR 11.5%) |
| time (16d cap) | 102 | +131.2R (WR 29.4%) | 52 | −4.0R (WR 29.4%) |
| outside window | 10 | −1.4R | 38 | +2.9R |

**This is the finding.** The 1h window's *exit* is a perfect classifier of
whether its 15m trades worked:

- windows that reached **+3R** → their 15m trades run **55.7% WR, +231R**
- windows that hit **−1R** → their 15m trades run **8.6% WR, −133R**

An **8.6% win rate** is not a bad cohort, it is a cohort that should not
be traded at all. And it is 47% of all IS trades.

## The corrected picture — and it is a good one

The framing in `BIAS_WINDOW_THEORY.md` was wrong in its conclusion. I wrote
that the 15m layer trades inside a dead window and finds its own edge. The
truth is the reverse:

**The 1h swing's direction is a strong predictor, but the 1h swing's 3R/-1R
exit is a much stronger one.** The window is not a *permission* slice
("you may trade in this direction"). It is a **quality oracle** — and the
oracle's verdict only becomes knowable at the window's exit, 1.1 days
later on median.

**That is exactly the "something we are missing."** The 1h book has no
standalone edge (Q1: best is flip at +50.6R IS but **−6.0R OOS**, PF
0.96 — it is worthless as a book). But its trades, *read as events rather
than as positions*, partition the 15m book into a cohort worth +231R and a
cohort worth −134R.

## Why this re-ranks the queue

- **W1 (duration) and P4 (cap_days) become the central items, not side
  ones.** The oracle's verdict arrives at the exit, so *when* the window
  ends is the whole ballgame. `cap_days` controls the verdict's timing for
  5-7% of windows, and those time-capped windows are the IS book's
  **+131.2R** bucket — the second-largest contributor. Cutting cap to 8
  days would destroy it. **P4's pre-registered direction (cap=8 ≥ 0) is
  probably wrong, and the reason is now visible: the time bucket is
  profitable in IS and flat/negative in OOS.**
- **The unexploited item is reading the oracle EARLY.** The verdict is
  knowable in hindsight but partially in real time — the window is at +1.5R
  or −1R *during* its life, and the 1h leg's live state is a live feature.
  This is the natural successor, and it is **not** the dead `r_touch`
  (which closed the *window*; this would act on the 15m layer *inside* a
  still-open window).

## Caveats, stated before anyone leans on this

1. **Q2 is partly circular.** A window that hits +3R and one that hits −1R
   are different price paths, so of course the 15m trades inside them
   differ. The number is real; the *causal* claim is not yet earned. What
   is not circular is Q3: removing the window kills the book, and that is
   a live gate, not a hindsight label.
2. **The `time` bucket is unstable** — +131.2R IS, −4.0R OOS, on 102 and
   52 trades. That is a cohort that does not survive its era and should
   not be leaned on.
3. **Trimmed means are negative everywhere** (cascade tm −0.288 IS,
   −0.334 OOS). The cascade's edge is entirely in the top tail, exactly
   as the other autopsies found. Consistent, not new.
4. One seed list, one era each, ungated baseline run at `cap_days=999` /
   `breakeven_r=1.0` — a fair "same engine, no window" control, but it is
   not the champion's exact config.
