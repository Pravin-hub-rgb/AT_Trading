# P86 — ATR-NORMALISED TREND DISTANCE. Same failure, same reason, now
# measured twice.

> Run 2026-09-29. Harness `exp_atr_trend.py`. **NOT ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## What was run, and why only one form

P84 tested a raw trailing MA at four windows and failed all of them — but
MA400 won **7 of 8 IS half-years**, the best conditional result in that
run. **Testing more MA variants now would be searching after seeing four
windows**, which is exactly what the family-wise criterion exists to stop.

So **one** form, fixed in advance, chosen for a reason rather than a grid:
a raw MA compares price to an absolute average, so its behaviour changes
with the price level — the objection P68/P69 raised to absolute price and
volatility, and the reason relative price died in 4 of 4 cells.
**Measuring distance in ATRs rather than dollars removes that dependence.**

```
dist = (close - MA_200) / ATR_200        at each trade's own entry_ts
  keep LONG  only if dist >= +D
  keep SHORT only if dist <= -D
D in {0.5, 1.0, 2.0} ATRs, pre-registered, family-wise
```

## Result — every D, every cell, negative

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| D=0.5 | −76.7R (6-2) | −44.1R (2-2) | −109.9R (5-3) | −63.0R (2-2) |
| D=1.0 | −97.7R (5-3) | −36.9R (2-2) | −133.2R (5-3) | −55.9R (2-2) |
| D=2.0 | −102.6R (**7-1**) | −30.7R (2-2) | −132.0R (5-3) | −51.8R (2-2) |

**Family-wise: nothing passes.** No cell positive, none clears M, and the
period split is mixed or negative everywhere except champion IS at D=2.0.

## The finding, which is now measured twice and is the useful output

**The filter does exactly what it was designed to do to the long side, and
destroys more on the short side:**

| champion OOS | long | short |
|---|---|---|
| control | 162t **+1.8R** PF 1.22 | 117t **+68.4R** PF 2.10 |
| P84 MA200 | 102t +18.4R PF 1.48 | — |
| **P86 D=1.0** | 91t **+24.9R** PF 1.64 | 64t **+8.4R** PF 1.39 |

**The long side is rescued — +1.8R becomes +24.9R, PF 1.22 → 1.64, and the
normalisation makes it work better than the raw MA did.** The short side
falls from +68.4R to +8.4R. **Protecting the side that was worth +1.8R costs
the side that was worth +68.4R.**

| | champion IS |
|---|---|
| control | long 273t **+272.6R** PF 3.01 · short 227t +53.2R PF 1.69 |
| D=1.0 | long 157t +196.3R PF 3.54 · short 135t +31.8R PF 1.67 |

**In IS too: the long side improves on PF (3.01 → 3.54) while losing
76R of net.** The filter is genuinely finding better trades and genuinely
removing more value than it adds.

## Why this is now a conclusion rather than a puzzle

P84 said it from a raw MA and P86 confirms it on an ATR-normalised
distance — **two different parameterisations, the same shape.** The
mechanism is not a tuning artefact:

> **A trend filter cannot be applied to one side only. In a trending
> market most of *any* side's signals sit against the average, so the
> condition that blocks the bad longs blocks the good shorts.** The champion
> earns on longs in IS and shorts in OOS, and no single trend condition
> protects one without taxing the other.

**And that is the real finding about the champion's fragility**: it is not
that the long side is broken in isolation. It is that **the book has no
single directional bias it can defend**, because its edge migrates between
sides across eras — which is the era-split pattern for the eighth time,
now measured on a filter designed to fix it.

## What was NOT done, deliberately

- **No MA-window sweep, no second normaliser, no D refinement.** P84 saw
  four windows and P86 saw three D values; adding a fifth form is search.
- **No long-only arm was run**, and that is the honest gap: a filter
  applied to longs alone is the obvious next thing, and it is not run here
  because P84 already shows the information — the long side is +1.8R in OOS
  and +272.6R in IS, so removing longs in a downtrend is a risk decision
  about live behaviour, not a backtest finding, and sizing it requires the
  position-sizing answer this repo cannot give (P9).

## Stated limitations

- **Both lanes are the same data.**
- **D=2.0 wins 7 of 8 IS half-years and still loses 102.6R** — the
  partition column is the weakest gate in this programme (P82) and should
  not be read as support.
- **MA=200 hours was chosen to match P84's best window**, which is
  informed by a previous result. It was fixed before this run, but it is
  not independent of P84 and is not claimed to be.

## Status

**NOT ADOPTED. The trend-filter family is closed** — two
parameterisations, both family-wise failures, with the mechanism now
identified rather than merely observed.

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
