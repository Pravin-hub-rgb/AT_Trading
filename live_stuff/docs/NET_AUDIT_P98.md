# P98 — THE NET-R AUDIT. Four defects, one root cause.

> Run 2026-09-30. Harness `exp_net_audit.py`. **NOTHING ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Identity gate: 340t/+225.3R shipped vs patched-off → **IDENTICAL**.

---

## ROOT CAUSE

**No per-trade NET helper existed in the repo.**

`net_r(tr)` sums a whole book. But every defect below needs net **per
trade** — P89 is per-trade statistics, the outlive cohort is *selected* per
trade, and the drawdown path is ordered by per-trade exit time. So gross
`r_multiple` got used for per-trade work while the *comparisons* were stated
against net champion pins.

**Gross-vs-net had already been caught twice this round (P60, P83). This is
the third occurrence, and it had spread across nine experiments.**

## THE HELPER, VERIFIED NOT ASSUMED

```python
def net_per_trade(tr):
    """Per-trade NET R, allocating fees/slippage and funding per trade.
    Mirrors net_r exactly, but returns the vector instead of the sum."""
```

| lane / era | drift vs `net_r` |
|---|---|
| champion IS | 1.5e-12 |
| champion OOS | 1.4e-14 |
| utcsat IS | 5.7e-14 |
| utcsat OOS | 2.1e-14 |

**The run aborts if any drift exceeds 1e-6.** A helper that does not
reconcile to the book total is not a helper, it is a second opinion.

---

## THE COST BASE, STATED ONCE

| | n | gross | **net** | cost | cost as % of gross |
|---|---|---|---|---|---|
| champion IS | 500 | +445.2R | **+325.8R** | 119.4R | 26.8% |
| champion OOS | 279 | +105.7R | **+70.1R** | 35.6R | 33.7% |
| utcsat IS | 454 | +466.5R | **+359.0R** | 107.5R | 23.0% |
| utcsat OOS | 253 | +92.6R | **+60.2R** | 32.4R | 35.0% |

**A quarter to a third of every book is cost.** This is the number that was
missing from nine experiments.

---

## D1 — SIDE ASYMMETRY, recomputed on net

| lane / era | side | n | gross | **net** | R/t (net) | PF (net) | cost |
|---|---|---|---|---|---|---|---|
| champion **IS** | long | 273 | +339.5R | **+274.3R** | +1.005 | 2.28 | 65.2R (19.2%) |
| | short | 227 | +105.7R | **+51.5R** | +0.227 | **1.27** | 54.2R (**51.3%**) |
| champion **OOS** | long | 162 | +22.1R | **+1.4R** | +0.009 | **1.01** | 20.7R (**93.6%**) |
| | short | 117 | +83.6R | **+68.7R** | +0.587 | 1.79 | 14.9R (17.8%) |
| utcsat **IS** | long | 252 | +367.4R | **+307.7R** | +1.221 | 2.59 | 59.7R (16.2%) |
| | short | 202 | +99.1R | **+51.3R** | +0.254 | 1.30 | 47.8R (48.3%) |
| utcsat **OOS** | long | 148 | +21.2R | **+2.2R** | +0.015 | 1.02 | 19.0R (**89.4%**) |
| | short | 105 | +71.4R | **+58.0R** | +0.552 | 1.72 | 13.5R (18.8%) |

### This *inverts* P89, and it is the biggest correction in the audit.

P89 reported **shorts stronger than longs, and recommended protecting the
long side.** On net, in **both lanes, in both eras**, the reverse:

| | P89 recorded | **net, verified** |
|---|---|---|
| champ IS short PF | better than long | **1.27 vs 2.28 — much worse** |
| champ OOS long PF | — | **1.01 — the book does not pay** |
| shorts cost | — | **48–51% of gross in IS, 18% in OOS** |
| longs cost | — | 16–19% in IS, **89–94% in OOS** |

**The OOS long side is +22.1R gross and +1.4R net. Costs eat 93.6% of it.**

The mechanism is the one P91 found and D1 now prices: **shorts run wider
stops, so `r_multiple` looks healthy while the price return is negative** —
and wider stops mean a larger `entry_price / risk` ratio, which is exactly
what `fund()` charges on. Longs in OOS ran tight stops and tiny R, so
per-trade cost is a larger share of a smaller number.

**P89's recommendation is withdrawn.** Any risk policy built on it would
---

## D2 — DRAWDOWN, depth bug fixed

**The bug:** the original stored `dd = peak - eq` — the *amount* — and then
continued the peak search with `peak - dd`, **subtracting the drawdown from
the peak a second time.** The peak walked monotonically downward, so
drawdown depth compounded. The fix keeps `peak` as a running maximum and
never lets `dd` touch it.

| lane / era | **max DD** | P92 recorded | episodes | days median | worst episode |
|---|---|---|---|---|---|
| champion IS | **30.5R** | ~~445.2R~~ | 26 | 19 | 30.5R / 219d |
| champion OOS | **54.9R** | ~~105.3R~~ | 9 | 8 | 54.9R / 386d |
| utcsat IS | **22.8R** | ~~466.5R~~ | 27 | 19 | 22.8R / 147d |
| utcsat OOS | **32.7R** | ~~92.6R~~ | 8 | — | — |

### Two things follow, and they disagree

**1. P92's depths were wrong by an order of magnitude.** 445.2R → **30.5R**.
P92's *duration* figures survive (median 19–21 days, not the 422 days the
pre-bug run showed), but **its depths were an artefact of the
double-subtraction.**

**2. P83's 37.3R does not reconcile either.** On a correct algorithm the
champion's IS max drawdown is **30.5R**, not 37.3R. P83 likely used a
different path convention or a gross basis. **The number in every
downstream doc is now stale.**

**OOS max DD (54.9R) is *worse* than IS (30.5R)** — the opposite of what
"in-sample is deeper" intuition suggests, and worth knowing before sizing.

---

## D3 — THE OUTLIVE COHORT, on net vs net

P94 compared a **gross** cohort sum against a **net** champion book. Rebuilt
properly, matching each trade to its parent interval from the engine's
`intervals` (the trade record carries no `window_end_ts`).

| lane / era | cohort | n | gross | **net** | R/t (net) | PF (net) |
|---|---|---|---|---|---|---|
| champion IS | **outlive** | 103 | +506.2R | **+481.6R** | +4.676 | 15.05 |
| | inside | 396 | −62.3R | **−156.9R** | −0.396 | 0.58 |
| champion OOS | **outlive** | 43 | +188.7R | **+183.2R** | +4.261 | 19.38 |
| | inside | 208 | −78.8R | **−105.3R** | −0.506 | 0.40 |
| utcsat IS | **outlive** | 100 | +509.8R | **+486.1R** | +4.861 | 17.40 |
| | inside | 353 | −44.6R | **−128.3R** | −0.363 | 0.62 |
| utcsat OOS | **outlive** | 34 | +150.9R | **+146.4R** | +4.306 | 18.77 |
| | inside | 219 | −57.9R | **−88.2R** | −0.403 | 0.60 |

**The cohort survives net.** Costs take only ~5% off it (+506.2 → +481.6),
because these are few, large-R trades — cost scales with trade count, not
with R. **P94's central structural finding stands.**

### But the M comparison was inflated:

| | P94 (gross cohort vs net book) | **net vs net** |
|---|---|---|
| champion IS | +180.5R = **0.93× M** | **+155.9R = 0.81× M** |
| champion OOS | +118.6R = 0.61× M | **+113.1R = 0.58× M** |
| utcsat IS | +150.9R = 0.78× M | **+127.2R = 0.66× M** |
| utcsat OOS | +90.7R = 0.47× M | **+73.0R = 0.38× M** |

**Best cell drops from 93% of M to 81%.** Still fails, further than recorded.

**And the circularity is untouched.** The cohort is selected on
`exit_ts > window_end` — a **post-outcome** event. A live system cannot know
in advance which trades will outlive their window. Recomputing on net does
not fix that, and **nothing here is adoptable.**

### The INSIDE cohort is the real headline

**396 trades costing −156.9R net in IS. −105.3R in OOS.** PF 0.58 and 0.40 —
not marginal trades, but a losing sub-book **the champion takes 79% of the
time.**

That is a sharper version of the round's closing question. It is not "the
20% is good." It is **"the other 80% is a −157R drag, and nobody knows why
the champion books it."**

---

## D4 — LABELLING ONLY, no recomputation

| doc | status |
|---|---|
| **P90** next-open **+500.6R** | **RETRACTED** in P91 (R-denominator artefact). Stays retracted. Not recomputed. |
| **P91** absolute return | **OMITS COSTS.** Cost-free descriptive measurement, **not an account curve.** Never quote as deployable return. |

P91's absolute figures and P98's cost base are complementary, not
contradictory: P91 shows shorts lose on *price*, P98 shows longs barely
survive *costs*. **Both must be quoted together.**

---

## STATUS

**Nothing adopted. No production file edited.** Champion unchanged:
500t/+325.8R IS, 279t/+70.1R OOS.

**Three recorded results are corrected:** P89's side recommendation is
withdrawn and inverted; P92's depths were an order of magnitude too large;
P83's 37.3R maximum drawdown does not reconcile (30.5R on a correct
algorithm). **One recorded result survives intact** — P94's cohort is
genuinely strong, just not adoptable, and now fails M by more than stated.

have cut the wrong side.
