# What the tight-stop half is actually seeing

> Run 2026-09-29. Harness `exp_stop_decomp.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Follows `RISK_CONCURRENCY.md` (P2 / log 121).

P45 found the book splits hard by stop distance — 251 tight-stop trades
make +300.0R of +325.8R — and the obvious reading is price action. This
file asks what that split is actually measuring, because there is a
competing explanation that had not been ruled out.

---

## H1 — it is mostly volatility. Confirmed.

| corr(stop%, ATR) | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| | **0.53** | **0.69** | **0.52** | **0.71** |

**A swing low is simply further from entry in a high-ATR regime.** The
tight/wide split is mostly "low volatility vs high volatility" — and the
volatility state is already known to the engine. That was the suspicion, and
it holds.

## H2 — ATR-normalising it does not rescue it

| stop/ATR > 2.0 | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| dNet | −267.2R | **+35.5R** | −260.0R | **+31.7R** |

The raw form is the better of the two. The normalised form is era-flipped —
+35R OOS against −267R IS. Removing the volatility wrapper did not produce
an edge, it produced a different book with the same problem.

## H3 — the real price-action bucket, and it works, and it still fails

**Leg position**: where the entry sits inside its own swing leg, as a
fraction. Scale-free by construction, so it cannot be a volatility proxy.

```
legpos = (entry - leg_low) / (leg_high - leg_low)      long
```

**IS — the gradient is real, and the two lanes agree almost exactly:**

| bucket | champ IS | utcsat IS |
|---|---|---|
| legpos ≤ 0.2 | 75t **+150.5R PF 4.51** | 72t **+148.7R PF 4.58** |
| legpos ≤ 0.4 | 108t +142.1R PF 3.73 | 102t +141.1R PF 3.84 |
| legpos 0.4–0.6 | 113t −13.1R PF 1.20 | 102t −4.6R PF 1.31 |
| legpos 0.6–0.8 | 110t −20.6R PF 1.05 | 93t −7.1R PF 1.17 |
| legpos > 0.8 | 94t +67.0R PF 2.34 | 85t +80.8R PF 2.76 |

**PF 4.5 → 1.05 → 2.34 across two different lanes.** That is a genuine,
scale-free price-action ordering, and it is the best thing in this whole
thread.

**OOS — the gradient reverses:**

| bucket | champ OOS | utcsat OOS |
|---|---|---|
| legpos ≤ 0.2 | 40t +6.1R PF 1.37 | 37t +10.2R PF 1.54 |
| legpos ≤ 0.4 | 53t +5.2R PF 1.33 | 46t +0.8R PF 1.20 |
| **legpos 0.4–0.6** | 69t **+48.2R PF 2.62 WR 40.6%** | 63t **+43.9R PF 2.63 WR 42.9%** |
| legpos > 0.8 | 52t −6.0R PF 0.98 | 47t −5.0R PF 1.01 |

**IS loves 0.0–0.2. OOS loves 0.4–0.6.** The sign of the ordering flips.

### The verdict line

**Thresholds clearing M = 193.4R: 0/11 in all four cells.**

**Every single bucket has a negative dNet.** The concentration is real, the
price-action explanation is real, and neither one is extractable — because
the complement pays.

## The pattern across this whole thread

Four independent features, four concentration findings, one shape:

| feature | concentration | eras agree? | extractable? |
|---|---|---|---|
| decay (P37/P38) | real, stale legs good | yes, and OOS better | no — small |
| window age (W1) | real, p75 cohort beats book 4/4 | yes | no — inside null |
| stop width (P45) | real, PF 3.2 vs 1.4 | yes | no — 4/4 negative |
| leg position (H3) | real, PF 4.5 vs 1.05 | **no — reverses** | no — 0/11 vs M |

**Every one of them concentrates P&L. Not one of them moves net upward.**
In a book where the median trade is roughly break-even, the profitable
subset is large and overlapping; cutting it removes winners faster than
losers.

**This is the shape the graveyard keeps producing, and it is now measured
four times rather than one.**

## What would actually use this

Not a filter. A **size** — size up when legpos ≤ 0.2, size down in the
middle band. The blocker is the one the queue already recorded: the engine
has no size channel (`v18_streak_halt.py` has zero hits for
equity/size/notional). P1's nesting is a similar situation — the finding is
real and there is nowhere to put it.

**A caveat on that, honestly:** the era reversal in H3 means even a size
rule would be fitted to the IS ordering and would be reading the wrong
bucket OOS. It would need the OOS ordering to agree before it is worth
building the channel for.

## Note on a bug this file had

The first run's `swing_no` lookup silently returned nothing and every trade
fell into the default leg-position bucket, so H3 printed one row containing
the whole book and looked like a null. The harness now prints a
`!! swing_no lookup MISSED` warning if the join is incomplete, and the
numbers above are from the fixed run. Recorded because the silent version
would have been easy to quote.
