# P88 — THE FAMILY FAILS, AND THE FAILURE IS THE FINDING. The ceiling
# identifies worse trades in every era; it only pays in the era where
# worse means losing.

> Run 2026-09-29. Harness `exp_ceiling_family.py`. **NOT ADOPTED. FAMILY
> CLOSED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## What was run

P87 established that the ATR% ceiling's effect **survives a half-year fixed
effect** — only 1–9% of the gap was removed — and a month-cluster bootstrap,
in three of four cells. That is the first result this round that is not an
era-split and therefore the first a live system could act on.

**But 0.40% was a peak of P69's four-point grid and P69 never tested the
family.** This runs all four ceilings under P87's **unmodified**
instrument, with the criterion fixed before the run:

> **Every ceiling must beat the champion in net in BOTH eras in BOTH lanes,
> survive the half-year partition, AND show b significant after period
> control on all three instruments** — cluster-robust t, month-cluster
> bootstrap and half-year-cluster bootstrap. All three must agree; the
> flattering one is not selectable.

## Result

```
ceiling   champ IS   champ OOS   utcsat IS   utcsat OOS
0.30%       fail       fail        fail        fail
0.40%       fail       PASS        fail        PASS
0.50%       fail       PASS        fail        PASS
0.60%       fail       fail        fail        fail

FAMILY: FAILS
```

**IS fails at every ceiling on both lanes. OOS passes at 0.40% and 0.50% on
both lanes. The pattern is perfectly clean.**

### And the b coefficient is positive in all sixteen cells

| ceiling | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| 0.30% | +0.3021 | +1.4140 | — | +1.7014 |
| 0.40% | **+0.8165** | **+1.2965** | — | **+1.2972** |
| 0.50% | +0.4628 | +0.9099 | +0.6728 | +0.7735 |
| 0.60% | +0.3664 | +0.5555 | +0.5108 | +0.4608 |

**Every one of the sixteen cells is positive.** The ceiling identifies worse
trades in **every era, on both lanes, at every level.**

## Why IS fails anyway — and it is not a power problem this time

**In IS the dropped cohort is still profitable.** Champion IS nets +325.8R
and the ceiling *reduces* it at every level: **−128.4R, −6.0R, −6.1R,
−2.7R** on the champion lane, and −2.2R / −2.8R at 0.50/0.60 on utcsat.

**In OOS the dropped cohort is negative**: −41.6R and −37.1R at 0.40%, and
removing it *adds* +41.6R and +37.1R.

> **The ceiling ranks trades correctly everywhere. It pays only where the
> trades it rejects are actually losing money.**

**That is a complete and general statement, and it is why P87's champion-IS
t of +1.66 was a power problem rather than a contradictory result.** The
ranking effect is real in IS too — b is +0.8165 at 0.40% — but ranking
profitable trades below other profitable trades earns nothing.

## What this closes and what it hands over

**The ceiling family is closed.** Not because the feature is noise — it is
the only feature found this round whose information **survives period
control** — but because a filter that improves the ranking and destroys the
return in the era it was fitted in is not adoptable, and the era where it
does pay is the era that was never fitted.

**This is the ninth appearance of the era-split pattern** (P56 expiry, P58
granularity, P59 agreement, P60 union, P61 stability, P66 30m, P77 FS
hybrid, P84/P86 trend filter, P88 ceiling) **and the cleanest one yet**,
because it is not a magnitude difference on a fitted threshold. It is a
complete sign flip on a pre-registered four-point grid, with the ranking
coefficient positive in all sixteen cells underneath it.

**The one thing this round produced that a live bot could use, and the one
reason to keep it on a list:**

> **A trailing-volatility ceiling reliably identifies the worse half of the
> book. Whether acting on that is worth anything depends entirely on
> whether the worse half is actually losing money — and in the era this book
> was built in, it is not.**

**That is a risk-management input, not a filter.** An owner deciding whether
to stand aside in violent conditions is making a risk decision, and this is
the measurement feeding it — not an argument to deploy it.

## Stated limitations

- **Both lanes are the same data.** Four clean cells across two correlated
  lanes is a pattern, not independence.
- **The half-year fixed effect has 8 and 4 levels**, and the cluster-robust
  t is approximate on 45 and 24 month-clusters.
- **Requiring all three instruments to agree** is the strictest reading and
  it is why IS fails: at 0.50% on utcsat IS the month bootstrap is p = 0.0503
  and the t is +1.22, while at 0.40% the same cell has a negative dNet. **A
  laxer criterion would pass some cells, and choosing it after seeing this
  table is exactly what the family-wise rule exists to prevent.**
- **The forward slice can rule this out and cannot confirm it** (P63). If
  the owner's live data shows the era where the dropped cohort is negative,
  this feature is worth revisiting — with the level chosen from the grid on
  *that* data, not from this one.

## Status

**NOT ADOPTED. FAMILY CLOSED ON EVIDENCE.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS. Nothing in production
touched.
