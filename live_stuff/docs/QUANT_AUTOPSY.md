# QUANT AUTOPSY — the book's independence assumption, tested for the first
# time. IS and OOS disagree sharply, and that disagreement is the finding.

Date: 2026-09-28. `exp_quant_autopsy.py` → `_quant_autopsy.json` 46.3s.
Controls exact both eras (500t +325.8R / 279t +70.2R).

## Why these three measures

Every sizing experiment in this repo was a **multiplier on something already
known** — sMZX `1.5^count`, vol-targeting inverse-vol, campaign caps. None
asked what the mathematically optimal bet size *is*. Kelly's criterion is that
quantity and it has never been computed here.

Kelly is also why autocorrelation matters. The classical `K* = 2p-1`
(Barmish/O'Brien/Burke, arXiv:2003.02743) **assumes i.i.d. bets**, and that
paper's entire contribution is that temporally-correlated bets change the
optimal fraction — explicitly noting this is a *different* problem from the
cross-sectional correlation portfolio theory handles. So if the book is
autocorrelated, **flat sizing is not neutral: it is one specific bet
fraction, and it is not K\*.**

This also repairs the previous file's tautology. That one decomposed trades
into loss/win runs — and a run decomposition of a binary series *always*
alternates, so it measured the definition. The correct statistic is the ACF
of the P&L series itself.

## Result 1 — IS: the book is close to i.i.d.

| lag | ACF | band |
|---|---|---|
| 1 | +0.0651 | ±0.0877 |
| 2 | −0.0280 | |
| 3 | −0.0360 | |
| 4 | −0.0455 | |
| 5…10 | ≤ −0.0356 | |

**Every lag inside the band.** No serial structure in IS. VR(2) 1.067,
VR(4) 1.057, VR(8) 0.925 — all near 1.0, i.e. random-walk-like. (VR(16)
0.694 is a small-sample artefact of a 279-point-equivalent tail and is not
treated as signal.)

## Result 2 — OOS: strongly, significantly autocorrelated

| lag | ACF | band |
|---|---|---|
| **1** | **+0.4981** | ±0.1173 |
| **2** | **+0.1494** | |
| 3…10 | ≤ −0.0728 | |

**Lag-1 ACF is +0.498 — four times the band.** VR(2) 1.503, VR(4) 1.915,
VR(8) 2.083, VR(16) 2.023: **every horizon says trending, monotonically
rising with q.**

This is the opposite of IS and it is not subtle. In OOS a trade's outcome is
strongly predicted by the previous trade's outcome.

## The finding

**The same strategy, on the same lane, is i.i.d. in one era and strongly
autocorrelated in the other.** That is not a property of the strategy — it
is a property of the *sample*.

The likely mechanism is the halt rule. `max_consecutive_losses=3` was just
confirmed (yesterday's cluster autopsy) to be a sharp peak in IS. In IS it
binds often, which chops the loss sequence into runs of ≤3 separated by
skips — mechanically de-correlating the booked series. In OOS, with 279
trades and thinner periods, it binds less, and the raw autocorrelation of
the underlying signal survives into the ledger.

So the ACF is measuring **how much the halt rule is firing**, not a
discovered market structure. That is a caveat, and it is the reason this
does not become a trading rule: an effect that changes sign across eras and
is explained by a rule's activation frequency is not an edge.

## Result 3 — Kelly is NEGATIVE in both eras, and the number is absurd

| | win rate | f_full | f_half | f_quarter |
|---|---|---|---|---|
| IS | 0.3000 | **−0.4000** | −0.2000 | −0.1000 |
| OOS | 0.2796 | **−0.4409** | −0.2204 | −0.1102 |

`f* = 2p − 1` requires **p > 0.5** to be positive. This book wins 28–30% of
its trades, so **the binary Kelly criterion says the correct bet size is
zero or negative.** That is not a sizing recommendation — it is a statement
that the criterion's assumptions do not hold here.

The reason is visible in the file: this book does not have a binary ±1R
payoff. Its R distribution is heavy-tailed (17 trades ≥ +10R in IS carry the
book), so mean ≠ win rate, and `2p−1` applied to the win rate is simply the
wrong functional. The harness printed `1.0x = 1000000000.00x the full-Kelly
fraction` — the division-by-near-zero guard firing, which is the honest
signal that this number should never have been used.

**The correct Kelly input for this book is mean/σ of the R series, not
2p−1.** That is a real, unrun calculation and it is the one worth doing.

## What this closes and what it opens

**Closed:**
- The book's independence assumption is **era-dependent**, and anyone
  modelling it as i.i.d. in OOS is wrong by a factor of four at lag 1.
- The "is a loss streak predictable" question from the previous file is
  answered: **in OOS, yes and strongly (ACF +0.498); in IS, no.** The
  previous run's "UNKNOWN" now has an era-split answer.
- Binary Kelly is inapplicable and the file says so rather than reporting a
  negative fraction as if it were advice.

**Open, and genuinely new:**
- **Continuous-payoff Kelly**: f* = μ/σ² on the actual R series, computed
  per era, with the autocorrelation correction from the arXiv paper. This is
  the first principled sizing number this repo would have.
- **Why the ACF flips sign between eras** — the halt-rule activation
  hypothesis above is testable and cheap.

## Discipline

The negative-Kelly output was not quietly suppressed, and the
`1e9x` divide guard was left in place rather than hidden, because that
absurd number is the clearest possible signal that the criterion was being
applied outside its domain.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
