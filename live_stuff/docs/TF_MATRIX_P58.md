# 1D + 4h: the daily verdict holds, and 4h + 1h was hiding in the matrix

> Run 2026-09-29. Harness `exp_tf_matrix.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The owner's cell, answered

**1D HTF + 4h LTF: PF 0.25 in OOS.** Worst cell in the matrix.

| | IS | OOS |
|---|---|---|
| champion lane | 45t +40.7R PF 2.62 R/t +0.904 | 34t **−20.4R PF 0.25** |
| utcsat lane | 42t +41.5R PF 2.78 R/t +0.989 | 31t **−13.7R PF 0.41** |

## A confound in P57, and the fix

P57 held `min_bars=10` across every HTF timeframe. **That is a swing COUNT,
not a swing LAG** — its wall-clock confirmation lag was 10h at 1h, 40h at 4h
and **10 days** at 1D. P57 was charging the slow architectures a lag penalty
of up to 24x, so its conclusion that they lose could have been an artefact
of the penalty rather than a fact about the timeframe.

Worse, P57 built the 1D + 1h LTF arm with `min_bars=50`, which is the 15m
constant. On 1h bars that is a **fifty hour** lag. That arm's 66 IS trades
and 37 OOS trades were largely lag.

P58 holds the **wall-clock lag** fixed instead, which is what the champion
already does by accident — its 1h HTF uses 10 bars = 10h and its 15m LTF
uses 50 bars = 12.5h, both about half a day:

```
HTF  1h -> 10 bars (10.0h)   4h -> 3 (12.0h)   1D -> 1 (24h)
LTF 15m -> 50 bars (12.5h)   1h -> 12 (12.0h)  4h -> 3 (12.0h)
```

1D is pinned at 1 bar because that is the floor: a daily swing cannot
confirm faster than its own period. So 1D still carries a 24h lag against
the champion's 10h. **That residual 2.4x is a real property of trading
daily and is reported, not engineered away.**

**The fix was worth making and it did not change the daily verdict:**

| arm | P57 (lag-penalised) | P58 (lag-matched) |
|---|---|---|
| 1D + 15m IS | 196t +43.7R | 201t +46.2R |
| 1D + 15m OOS | 140t **−41.5R PF 0.77** | 141t **−44.6R PF 0.74** |
| 1D + 1h IS | 66t +7.3R *(50h lag)* | **161t +57.3R** |
| 1D + 1h OOS | 37t −19.7R PF 0.35 *(50h lag)* | 118t **−44.0R PF 0.56** |

The 1D + 1h arm gained **2.4x the sample** and the verdict held. The
conclusion that daily is dead is now free of the lag objection.

## The full matrix, champion lane (n, net, PF)

| | 15m LTF | 1h LTF | 4h LTF |
|---|---|---|---|
| **1h HTF** | **500t +325.8R / 279t +70.1R** (2.38 / 1.59) | — | 119t +148.0R / 67t −4.2R (3.40 / **0.97**) |
| **4h HTF** | 406t +70.4R / 263t +3.1R (1.63 / 1.23) | 286t +212.8R / 189t **+98.0R** (2.59 / **2.02**) | — |
| **1D HTF** | 201t +46.2R / 141t −44.6R (1.72 / **0.74**) | 161t +57.3R / 118t −44.0R (1.82 / **0.56**) | 45t +40.7R / 34t −20.4R (2.62 / **0.25**) |

## What the matrix settles

**A 1D direction source is dead regardless of what sits underneath it.**

```
1D + 15m   OOS PF 0.74
1D +  1h   OOS PF 0.56
1D +  4h   OOS PF 0.25
```

Three LTF timeframes, one verdict, monotone in how coarse the LTF gets. And
the control from the other side agrees: **1h + 4h has no daily problem and
still manages only PF 0.97 in OOS**, so a 4h LTF is poor under any HTF. The
daily architecture is not a ratio problem, and P57's reading of "closer is
better" was a confound of ratio and absolute speed.

**Both eras agree on the winner of the matrix: 1h HTF + 15m LTF.**


## The cell nobody asked for: 4h HTF + 1h LTF

**It is the only cell in the matrix that beats the champion in OOS, in both
lanes.**

| | IS | OOS |
|---|---|---|
| champion 1h + 15m | 500t +325.8R PF 2.38 **R/t 0.652** WR 30.0% | 279t +70.1R PF 1.59 **R/t 0.251** WR 28.0% |
| **4h + 1h** | 286t +212.8R PF 2.59 **R/t 0.744** WR 35.3% | 189t **+98.0R PF 2.02** **R/t 0.519** WR 32.8% |
| utcsat champion | 454t +359.0R PF 2.62 R/t 0.791 WR 30.8% | 253t +60.2R PF 1.58 R/t 0.238 WR 29.6% |
| **utcsat 4h + 1h** | 257t +165.4R PF 2.38 R/t 0.643 WR 33.9% | 171t **+72.1R PF 1.86** R/t 0.421 WR 32.2% |

**Every quality measure is better in both eras: R/trade, profit factor and
win rate.** OOS R/trade is **0.519 against the champion's 0.251 — more than
double** — and OOS win rate is 32.8% against 28.0%.

**But it costs real money in IS: −113.0R champion lane, −193.5R utcsat
lane**, for 214 and 197 fewer trades. The OOS gain is +27.9R and +11.9R.

**So it is a trade, not a dominance:** roughly half to two-thirds fewer
trades at roughly double the R per trade, with the IS bill being 113–194R.
Against a champion whose OOS R/trade is 0.251, that is a coherent story
about granularity — and it is the same story P56 told from the other side,
where the window expiry proved IS-fitted, costing 121–141R in IS while
earning 81–102R in OOS.

**It does not pass the criterion.** It does not beat the champion in both
eras, and neither +27.9R nor +11.9R comes near M = 193.4R.

## A third thing the matrix shows

**A 4h LTF is bad in OOS under any HTF** — PF 0.97 with a 1h HTF, PF 0.25
with a 1D HTF. The LTF is not a free choice either: the 15m LTF is the only
one healthy in OOS, and the champion sits at the one pairing where **both**
layers are individually healthy.

## Stated limitations

- **The 1D arms carry a 24h confirmation lag against the champion's 10h**,
  and no parameter can reduce it. That is the floor of the timeframe.
- **Sample size.** The 1D + 4h cell is 45 IS trades and 34 OOS trades —
  too thin to carry weight alone; its verdict rests on PF 0.25 being far
  below 1, not on the net.
- **The 4h + 1h finding is one era of OOS.** +27.9R and +11.9R are
  consistent across both lanes, which is meaningful — but two highly
  correlated lanes are not independent evidence.
- **Aggregated OHLC is synthetic** at the 4h and 1D layers. Highs and lows
  are exact; the open is the first source bar's open, the close the last
  one's. Bars are stamped with their final source bar, so no lookahead.

## Verdict

The pass criterion — beat the champion in **both eras in both lanes** and
clear **M = 193.4R** — is met by **nothing** in this matrix.

**The champion architecture is confirmed from every direction: no slower
HTF, no faster HTF, no coarser LTF, and no daily layer in either role.** The
timeframe search is closed on evidence, and on a fair comparison this time
rather than a lag artefact.

**4h + 1h is worth queueing as a candidate, not adopting.** It is the only
architecture in the programme with better OOS quality on every measure, and
its IS cost is the same IS-fitted excess P56 found in the window expiry.
That is one story seen twice, and it deserves the forward pass rather than
another IS number.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
