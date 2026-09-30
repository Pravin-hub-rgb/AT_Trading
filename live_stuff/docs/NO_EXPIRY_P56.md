# Does the 1h layer earn its keeping? Direction yes, expiry no

> Run 2026-09-29. Harness `exp_no_expiry.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The question

P55 closed every attempt to **gate on the 1h layer's structure**. That left
the prior question open, and the prior question is the bigger one:

> if the 1h layer's only measured job is supplying direction (P3: FLIP
> +1.9R IS, **−23.6R OOS**, PF never above 1.20), **what does the window's
> EXPIRY actually buy?**

A window ends at −1R, +3R or 16 days. All three are trade outcomes or a
duration cap. So: remove the expiry entirely and see what is left.

## Method

Every closed HTF trade's `exit_ts` is pushed to the end of the 1h series, so
`to_intervals` builds a window that never expires. **Once the 1h layer
declares a direction, that direction stays allowed to the end of the data.**
The gate becomes direction-only and purely structural. `cap_days=16` is left
alone, so the control path is byte-identical and the patch is done by
wrapping v7 at runtime rather than editing the repo file.

## Result

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| control n | 500 | 279 | 454 | 253 |
| control net | **+325.8R** | +70.1R | **+359.0R** | +60.2R |
| control R/trade | +0.652 | +0.251 | +0.791 | +0.238 |
| control PF | 2.38 | 1.59 | 2.62 | 1.58 |
| control DD | 17.8 | 37.3 | 14.8 | 22.1 |
| **no-expiry n** | **728** | **403** | **676** | **364** |
| no-expiry net | +204.7R | **+171.8R** | +218.2R | **+141.4R** |
| no-expiry R/trade | +0.281 | **+0.426** | +0.323 | **+0.389** |
| no-expiry PF | 1.79 | **1.89** | 1.86 | **1.85** |
| no-expiry DD | 26.6 | **35.3** | 30.9 | 31.5 |
| **dNet** | **−121.1R** | **+101.7R** | **−140.8R** | **+81.2R** |

## What this settles

**The expiry does real work, and it is not decoration.** Removing it costs
**121.1R** in champion IS and **140.8R** in utcsat IS, and win rate falls
from 30.0% to 28.2%. So P3's "the 1h layer supplies direction" needs
qualifying: **it also knows when to stop supplying it**, and that half is
worth about 130R in IS.

**But the direction itself is the durable part.** With no expiry at all the
book is not a collapse — it is **~1.7× the trades, PF never below 1.79, and
profitable in all four cells.** The 15m layer works against a gate that never
closes.

**And the era split is the same one everything else shows.** The expiry
**costs 121–141R in IS and earns 81–102R in OOS**, where the no-expiry book
is better on net, better on PF (1.89 vs 1.59), better on R/trade (0.426 vs
0.251), and **better on drawdown (35.3 vs 37.3)**.

## The honest reading

**The window expiry is IS-fitted.** It is a brake that suits the era the
book was developed in and costs more than it returns in the era it has not
been tuned on. That is not a discovery about markets — it is a discovery
about the book, and it belongs beside P49's cap finding:

| | IS | OOS |
|---|---|---|
| turn the 16-day cap **off** (P49) | +75.3R | +55.1R |
| remove the expiry **entirely** (here) | −121.1R | +101.7R |

The cap and the expiry are the same mechanism at different strengths. The
cap is the weak version and it helps in both eras; the expiry is the strong
version and it helps only in IS.

**Neither clears M = 193.4R, and the OOS gain is a single era with 403
trades.** So this is a documented direction, not an adoption — the same
status as the cap, and for the same reason: the case rests on a
train/test asymmetry rather than on a magnitude.

## What it would take to decide it

The OOS leg is the one that matters and it is the one that was not tuned.
A family-wise pass on `data/forward/bybit/` — which the queue has been
holding precisely for a decision like this — is the right instrument, and
M now exists to score it.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
