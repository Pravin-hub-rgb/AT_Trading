# P67: volatility IS a real signal — it just is not a timeframe switch

> Run 2026-09-29. Harness `exp_vol_regime.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The owner's hypothesis is half right, and the wrong half is worth more
> than the right half.**

## The owner's hypothesis

P66 found 30m roughly doubles the champion in OOS (+141.9R against +70.1R,
every quality measure better simultaneously) and costs 188–239R in IS. The
owner's explanation is price- and volatility-shaped: OOS is 2021–2022, when
BTC spent most of its time in a lower, calmer band than the 2023–2026 IS
era. If that is the separator, the switch should be on volatility —
**low vol wants 30m, high vol wants 15m.**

**Worth testing precisely because it is not P55 again.** P55 failed to build
an adaptive gate, but it failed on swing *geometry* — travel/ATR over
trailing K swings — whose IS and OOS distributions were indistinguishable.
Volatility needs no identification of anything latent; it is directly
observable at decision time.

## Method

Trailing **ATR% over 96 × 15m bars (24 hours)**, divided by the close at
that point, using **only bars at or before each trade's own `entry_ts`**.
Computed outside the engine so it cannot collide with an engine-local name.
Split at **each book's own tertiles** — self-referencing, so no threshold is
imported from another era or fitted to the answer.

## T1 — the pre-registered test fails

| lane / era | LOW vol: 30m − 15m | HIGH vol: 30m − 15m |
|---|---|---|
| champion IS | **−0.243** (15m better) | **−0.475** (15m better) |
| champion OOS | **+0.340** (30m better) | **+0.133** (30m better) |
| utcsat IS | **−0.636** (15m better) | **−0.473** (15m better) |
| utcsat OOS | **+0.047** (30m better) | **+0.066** (30m better) |

**The hypothesis needed the two columns to point in OPPOSITE directions.
They point the same way in every lane — the sign tracks the ERA, not the
volatility regime.** IS favours 15m in both terciles; OOS favours 30m in both.

**So there is no volatility switch, and the 30m/15m split is an era
artefact.** This is P55's wall again from a completely different direction,
and the second time a plausible, causal, decision-time feature has failed to
reproduce an era-dependent result that looked obviously mechanical.

## T2 — the part that IS real, and bigger than the timeframe question

Volatility does not select a timeframe. **It selects whether the book works
at all.**

| book | era | regime | n | net | R/t | PF | WR |
|---|---|---|---|---|---|---|---|
| **15m** | champ IS | **LOW** | 165 | **+263.6R** | **+1.597** | **3.61** | 33.9% |
| 15m | champ IS | HIGH | 165 | +96.5R | +0.585 | 1.88 | 28.5% |
| **15m** | champ **OOS** | **LOW** | 92 | **+82.6R** | **+0.898** | **2.39** | 27.2% |
| 15m | champ **OOS** | **HIGH** | 93 | **−22.8R** | **−0.246** | **0.64** | 20.4% |
| **15m** | utcsat IS | **LOW** | 149 | **+291.8R** | **+1.958** | **4.29** | 35.6% |
| 15m | utcsat IS | HIGH | 150 | +76.0R | +0.506 | 1.75 | 27.3% |
| **15m** | utcsat **OOS** | **LOW** | 83 | **+70.8R** | **+0.853** | **2.33** | 28.9% |
| 15m | utcsat **OOS** | **HIGH** | 84 | **−12.9R** | **−0.154** | **0.77** | 23.8% |

**The champion's OOS high-volatility tercile LOSES MONEY at PF 0.64 and
0.77.** Not "wins less" — negative, profit factor below 1. The
low-volatility tercile runs PF 2.33–4.29.

**And this holds in IS too, same direction, just with the profitable half
still profitable.** IS LOW is 3–4x better than IS HIGH. **So the effect is
not an era artefact — it is present and consistent in all four cells**,
which is more than anything else in this round has managed.


## Why this is still not a gate

It passes the consistency test that killed `cand_4h1h` (4-4 IS coin flip)
and it beats P66's split on every axis. **It is not adopted, for one
reason: it is a filter, and every filter in this programme has failed the
same way.**

The split point is a **tertile of the trade distribution**, not a
volatility level stable across regimes. To trade on it, the live threshold
must be either (a) a tertile recomputed continuously, which changes meaning
as the sample changes, or (b) an absolute ATR% level, which **has not been
searched and searching for one now would be fitting a threshold to an
answer already seen.** The 15m book's tertile bounds differ between eras —
IS low-bound 151.8 against OOS 140.2, IS high-bound 258.1 against OOS 234.2
— which is precisely P55's problem restated in volatility units: **the eras'
volatility distributions overlap enough that a level chosen on one does not
transfer cleanly to the other.**

**What would settle it:** the same family-wise forward pass, which per P63
can rule but never confirm. A volatility floor could be tested and killed on
40–70 forward trades, and it is a far better use of that slice than anything
currently queued for it.

## The owner's other suggestions — decay and delay

Neither is answerable in this harness. Both are named rather than dropped:

- **Decay** — `decay < 0.75` is the strongest consistent candidate in the
  programme (4/4 positive) but still only ~0.13 × M. Applying it
  *conditionally on volatility* is a new interaction and a new fit, and it
  should not be built by stacking two marginal ideas and testing the product.
- **Delay** — delaying entry changes each trade's R, so it cannot be
  approximated by filtering the trade list. It needs an engine change, and
  the engine has no entry-delay channel today (the same missing size channel
  that closed P9).

## Stated limitations

- **Tertile splits leave ~83–165 trades per cell** — enough to see PF 0.64,
  not enough to call it.
- **Both lanes are the same data.** Their agreement is not independent.
- **ATR% is absolute, not normalised for the price level.** The owner raised
  price as well as volatility, and only volatility was tested here. A
  price-normalised or vol-of-vol feature is untested.
- **No threshold was searched, and none should be** until a forward slice
  exists to test one honestly.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.

**The champion's entire edge lives in the calm third of its own
distribution.** Roughly a third of trades produce +263.6R and +82.6R; the
noisy third produces +96.5R and −22.8R.
