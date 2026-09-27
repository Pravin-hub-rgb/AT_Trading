# Is the shipped config actually right?

**Date:** 2026-09-27
**Harness:** `live_stuff/tests/exp_is_it_right.py` → `_is_it_right.json`
**Audit only. No change proposed, no change made.**

---

## The short answer

**Nothing better was found — so yes, it is still the right thing to ship. But
its edge is much thinner than the headline number suggests, and the OOS does
not statistically establish it.**

Both halves of that sentence are true at once, and the second half is the one
that should govern position sizing.

## The numbers

### bybit IS (3.67y, n=500, net +325.8R)

| statistic | value | 95% CI | p |
|---|---|---|---|
| **mean** | **+0.652R** | [0.203, 1.150] | **0.0025** |
| median | −1.099R | [−1.114, −1.074] | 0.000 |
| **trimmed mean** | **−0.226R** | [−0.437, +0.016] | **0.067** |

worst losing streak: **16 trades**

### bybit OOS (2.0y, n=279, net +70.2R)

| statistic | value | 95% CI | p |
|---|---|---|---|
| **mean** | **+0.251R** | [−0.111, +0.668] | **0.199** |
| median | −1.054R | [−1.067, −1.037] | 0.000 |
| **trimmed mean** | **−0.267R** | [−0.501, +0.013] | **0.060** |

worst losing streak: **15 trades**

## What those numbers mean

**1. The OOS mean is not significant.** p=0.199. The confidence interval spans
zero. The IS mean is significant (p=0.0025), but the OOS is a *different,
shorter, later* sample and it does not confirm at conventional levels. avgR
fell from +0.652 to +0.251 — a **62% decay** out of sample.

**2. The robust statistics are negative in both eras.** trimmed mean is −0.226R
(IS, p=0.067) and −0.267R (OOS, p=0.060). median is −1.05 to −1.10R in both.

This is Rule 13/14 in its purest form and it is not a rounding error: **the
typical trade loses about a full R.** The book is carried entirely by a tail.

**3. How thin the tail is — "net if the best N trades had never been taken":**

| | IS | OOS |
|---|---|---|
| all trades | +325.8 | +70.2 |
| minus best 1 | +271.0 | +37.6 |
| minus best 2 | +222.5 | +18.1 |
| **minus best 3** | +180.2 | **+2.1** |
| **minus best 5** | +113.5 | **−23.2** |
| minus best 10 | +6.4 | −65.7 |
| minus best 20 | −108.5 | −122.8 |

**On OOS, three trades out of 279 — 1.1% of the book — carry the entire
result.** Remove five and the OOS is negative. On IS it takes ten of 500.

**4. Consequence for risk.** A book with a −1.05R median, a 15–16 trade losing
streak, and an OOS edge that rests on three trades must be sized as though its
edge could vanish. There is no cushion.

## The verdict

* **Keep shipping it.** Across every axis tested — LTF/HTF ladder (log 103),
  min_bars forensic, 30m/2h plane, S1–S6, the 5m confirmation gate, B1/B2/FLIP
  decomposition — nothing beat it. It is the best-supported configuration
  available, and abandoning it on the strength of an audit would be strictly
  worse than keeping it.
* **Do not describe it as "a +325.8R strategy."** The defensible statement is:
  a trend-following profile with a negative median, whose profitability depends
  on a small number of large winners, and whose out-of-sample mean is not
  statistically distinguishable from zero at p<0.05.
* **The risk-match idea is now the highest-priority open item, not a
  refinement.** If the edge is three trades wide, position size is the variable
  that decides whether a bad regime is survivable. Everything tried in logs
  109–112 was an attempt to *add* edge; the measured problem is that there is
  very little to add, and the correct response is to size for its absence.
* **The wick gate remains the only thing that ever survived** (+28.1R IS, 4/4
  lanes, replicated). It was the one change that was causally motivated,
  pre-registered, and implemented with gray rather than skip. Nothing in
  109–112 came close.

## What this does not say

* It does not say the strategy is bad. Negative-median trend systems are a
  legitimate and common profile; the tail is supposed to carry them.
* It does not say the OOS is wrong evidence. p=0.199 is "not proven", not
  "disproven" — and note the OOS has been inspected heavily across this
  programme (Rule 4), so it is weaker evidence than it looks, in both
  directions.
* It proposes no code change and made none. `backend/` is untouched.
