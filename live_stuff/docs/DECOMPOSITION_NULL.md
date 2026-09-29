# P8 — no decomposition of the champion clears its own null

`exp_decomposition_null.py`. Pins reproduced first, both exact. Each split
gets its **own** move-block bootstrap null built from its own trade
sequence — a 2023 book is not judged by a 2025 book reshuffle.

## Every split, every era: inside its own null

**IS**

| split | n | net | WR | M | null mean | |
|---|---|---|---|---|---|---|
| all | 500 | +356.9R | 30.0% | 479.9R | +316.5R | inside |
| 2023 | 107 | +95.0R | 31.8% | 170.8R | +72.2R | inside |
| 2024 | 161 | +93.9R | 23.0% | 152.7R | +71.8R | inside |
| 2025 | 130 | +79.2R | 33.1% | 147.8R | +77.1R | inside |
| 2026 | 102 | +88.8R | 35.3% | 128.8R | +65.0R | inside |
| **ex-best-5** | 495 | **+138.9R** | 29.3% | 427.5R | **−10.0R** | inside |

**OOS**

| split | n | net | WR | M | null mean | |
|---|---|---|---|---|---|---|
| all | 279 | +78.5R | 28.0% | 193.4R | +69.2R | inside |
| 2021 | 152 | −25.8R | 25.7% | 60.3R | −24.6R | inside |
| 2022 | 127 | +104.3R | 30.7% | 203.4R | +103.5R | inside |
| regime=flip | 221 | +106.4R | 28.5% | 211.9R | +91.0R | inside |
| regime=decisive | 58 | −27.9R | 25.9% | 30.0R | −21.7R | inside |
| **ex-best-5** | 274 | **−16.0R** | 26.6% | 232.4R | **−76.7R** | inside |

**NONE clear. Not one decomposition beats a reshuffle of itself.**

## The three findings worth keeping

**1. Consistency is not significance.** Every year is positive in IS
(+95.0, +93.9, +79.2, +88.8) with win rates of 23–35%. That *looks* like a
robust book. But every one of them sits inside its own year's null, and
the null mean is positive too (+72.2, +71.8, +77.1, +65.0). **A
consistently positive book whose reshuffle mean is also positive is
exactly what a book with no skill looks like when it has a fat right
tail.** The repo has been reading year-over-year consistency as
robustness. This says that reading is wrong.

**2. Removing the tail does not reveal a hidden core — it destroys the
book.** IS ex-best-5 is +138.9R against a null mean of **−10.0R**. The
observed is 149R *above* the reshuffle mean and still inside the null,
because M is 427.5R. **The top 5 trades are +218.9R of +445.2R gross —
49% of the book's P&L in 1% of its trades.** OOS is blunter: ex-best-5 is
**−16.0R net**, i.e. the champion without its best 5 trades does not
profit at all. **This is the repo's tail-concentration finding, now
quantified against a null: the book IS the tail.** There is no
lower-variance core hiding underneath it.

**3. The regimes are mirror images, and both are noise.** OOS
`decisive` −27.9R and `flip` +106.4R look like a routing discovery. Both
are inside their own nulls (M 30.0 and 211.9). The 2021 book is
**negative** (−25.8R) and still inside its null. **A book that loses
money in a calendar year and is statistically indistinguishable from a
reshuffle of itself is the cleanest possible demonstration that net R
alone carries no information at these sample sizes.**

## What this closes, and what it does not

**It closes the "find the robust component" thread.** Three natural
decompositions — by year, by regime, by tail-removal — were all available
and all fail. There is no sub-part of this book that is individually
distinguishable from luck.

**It does not say the book has no skill.** The P5 caveat applies with full
force: every null here is built from 100–500 trades with a heavy right
tail, and that variance is irreducible at this sample size. What it says
is that **no decomposition of the champion, as currently measured, is
strong enough to distinguish from a reshuffle of itself** — and that
includes the total, every year, both regimes, and the ex-tail core.

**The honest programme-level statement:** this book can be improved by
+R amounts that are inside its own noise floor. Every dNet the registry
has recorded — `exp_trail_half=1` at +103.8R, `partial_r` at +84.3R, the
`live_R` floor at whatever it was — is far below M, and so is everything
they produced. The forward window at n=5 cannot help. What would help is
either ~10× the sample or a mechanism with a causal story that predicts
*which* trades, not just a net delta after the fact.

## One methodological note

`htf_regime` splits **all 500 IS trades to `flip`** — the champion's IS
book is entirely flip-routed, with zero decisive trades. The `decisive`
split exists only in OOS (58 trades). So the "by regime" decomposition
has no IS counterpart at all, and its OOS arms are 58 and 221 trades —
too small for the null to say much either way. That asymmetry is worth
knowing before anyone builds on the OOS regime contrast.
