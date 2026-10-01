# P18 — the symmetric version was already computed, and it does not help

`exp_symmetric_decay.py`. Pins reproduced first, scored on **P16's
unchanged bar** so the comparison is honest.

## The user's catch

> "woh cheez joh hai nah swing lows breaks for buying swing and highs for
> selling bhi karre ho right"

**They are right that both are computed and right that only one was used.**
`decay_pair()` (`exp_decay_switch.py:165`) returns
`(broken_up_frac, broken_dn_frac)` — buying legs defended by their lows,
selling legs defended by their highs. **P11 and P15 reported only the first
component. The second was computed and discarded.** M1 (asymmetry) was the
one arm that came out with a large IS number and the wrong OOS sign.

So three definitions exist and only one was properly scored:

| | definition |
|---|---|
| **UP-ONLY** | broken buying lows — what P11/P15 used |
| **SYMMETRIC** | broken buying lows **+** broken selling highs |
| **ASYMMETRIC** | up − down — P12's M1, the lead |

## Result: 0 of 13 clear the bar

| arm | n | IS net | R/tr | PF | std | **streak** | worstY | OOS net |
|---|---|---|---|---|---|---|---|---|
| up < 0.5 | 164 | +88.6R | 0.717 | 2.10 | 5.67 | 8 | **−5.1** | +102.0R |
| **up < 0.75** | 307 | **+383.9R** | **1.427** | **3.34** | 6.76 | 11 | **+70.8** | +84.2R |
| up < 1.01 (all) | 500 | +356.9R | 0.890 | 2.38 | 5.55 | 16 | +102.2 | +78.5R |
| sym < 0.5 | 164 | +88.6R | 0.717 | 2.10 | 5.67 | 8 | −5.1 | +102.0R |
| sym < 1.0 | 431 | +397.5R | 1.099 | 2.74 | 5.93 | 14 | +107.4 | +66.5R |
| sym < 1.25 (all) | 500 | +356.9R | 0.890 | 2.38 | 5.55 | 16 | +102.2 | +78.5R |
| asym arms | — | all inside the null in at least one era | | | | | | |

**Falsifier (b) fires: all three decay definitions are closed together,
and P16's recommendation stands unchallenged.**

## What the comparison actually shows

**1. `sym` is a strictly worse version of `up`.** The best symmetric arm
(`sym < 1.0`, 431 trades) gives +397.5R IS but **OOS +66.5R — below the
champion's +70.1R** and below `up<0.75`'s +84.2R. And at the thresholds
where they should differ (`sym<0.5` and `up<0.5`) **the numbers are
byte-identical** — 164 trades, +88.6R, std 5.67, streak 8. **At low decay
the two features carry the same information**, because in a low-decay
state almost no selling highs are broken either. Symmetry only starts to
differ once you are already cutting aggressively, and by then it costs
OOS.

**2. The 2025 regression is confirmed as a property of the signal, not of
the half that was used.** `up<0.75` has `worstY = +70.8R` against the
champion's +102.2R, so the year floor fails — and `sym` does not repair it.
**Using the full signal does not fix the one thing that killed the decay
family under P16's bar.**

**3. Asymmetry is now properly closed.** M1 was P12's surviving lead
(IS +72.5R, OOS −6.3R). Scored on the same bar as everything else, **no
asymmetric arm clears it.** It joins the P9/P11 family of descriptive
signals that locate the book's R without predicting it.

## The honest reading of the user's suggestion

**The instinct was right — the feature was under-used — and it turns out
not to matter.** The symmetric version is computable, was already
implemented, and is worse on the metric that counts (OOS), identical
where it should be different, and does not repair the year regression.

**That is a useful negative in a different way from the other two today:**
this one is not "we tried it and it lost money" but "the missing half of
the signal was already computed, and adding it changes nothing." Which
also means **there is no untested variant of the decay idea left** — up,
down, sum, difference, all scored on one bar.

## Recommendation, unchanged

**`nest1h>0.25 + age>0.5d`** (P16) remains the leading candidate: 352
trades, +409.0R, R/trade +1.339, PF 3.13, losing streak 13 vs 16, OOS
+85.7R, every IS year at or above the champion's, and the only survivor
carrying no hour-of-day term.

**The decay family is closed under P16's bar in all three forms.** If the
bar is relaxed back to P15's (which had no year floor), `decay<0.75` is
better than P16's recommendation on net and R/trade and worse only on the
2025 year — but that is a bar change, not a finding, and the bar was
tightened for a reason.
