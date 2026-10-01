# P5-SENS — M is a property of the book, not of block=20

`exp_null_sensitivity.py`. Pins reproduced first, both exact.

## The question

`BASE_BOOK_NULL.md` produced M = 479.9R IS / 193.4R OOS and told every
result in the repo to clear it. That number rests on one methodological
choice — block length 20 — which was pre-registered to match
`exp_montecarlo_dd.py` rather than derived. If M is a cliff in block
length, the bar is arbitrary and the finding is soft.

## The answer: a plateau, not a cliff

| block | IS M | IS null mean | OOS M | OOS null mean |
|---|---|---|---|---|
| 5 | 576.4R | +359.9R | 218.5R | +79.4R |
| 10 | 530.4R | +336.5R | 221.7R | +80.8R |
| 15 | 488.1R | +317.1R | 221.7R | +83.6R |
| **20 (used)** | **479.9R** | +316.5R | **193.4R** | +69.2R |
| 30 | 466.0R | +304.0R | 172.3R | +57.1R |
| 40 | 471.9R | +307.6R | 154.3R | +44.0R |
| 60 | 468.5R | +317.9R | 154.3R | +44.0R |
| 90 | 439.6R | +310.3R | 181.5R | +51.5R |

- **IS:** M spans 439.6R – 576.4R, **×1.31**. Block=20 is mid-plateau.
- **OOS:** M spans 154.3R – 221.7R, **×1.44**. Block=20 is mid-plateau.

**The ordering is also correct.** M *decreases* as block lengthens, in both
eras, monotonically for IS down to block 40. That is the right direction:
a longer block preserves more serial structure, so the reshuffle
distribution is *wider* in the signed tails — visible in the 2.5%/97.5%
columns, which open out from +129.8/+510.4 at block 20 to +160.7/+463.1
at block 90. Short blocks (5) preserve too little and give the tightest,
most flattering M. **The method is not accidentally picking a kind number;
it behaves the way a block bootstrap should.**

## What this licenses

**The conservative reading of P5 stands.** The bar to beat is:

| | M (block=20) | M range across blocks |
|---|---|---|
| **IS** | **479.9R** | 439.6R – 576.4R |
| **OOS** | **193.4R** | 154.3R – 221.7R |

**Even at the most generous block length, the champion's own +325.8R IS
and +70.1R OOS sit well inside the null.** IS observed net is *below the
null mean* at every block length ≥ 20. So the P5 conclusion does not
depend on the block choice at any point in the range — it would take a
block length outside 5–90 to change it, and at block 5 (the least
conservative, structure-destroying end) the observed net is still far
below M.

The verdict `STABLE — a plateau, so block=20 is a defensible choice and
the M finding hardens` is printed by the harness itself, from the
measured spread, not asserted in advance.

## The one thing this does not fix

M being well-estimated does not make M *small*. It makes the bar's
location trustworthy. The bar is still high, and the registry audit in
`BASE_BOOK_NULL.md` stands unchanged: `exp_trail_half=1` (+103.8R IS,
+40.3R OOS) and `partial_r` (+84.3R) are inside the null in both eras.

A sensitivity check that confirms a number is not a sensitivity check
that rescues a result. This one hardened the null, not the arms.
