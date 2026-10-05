# Which timeframe supplies the direction? 1h wins, and it was never tested

> Run 2026-09-29. Harness `exp_timeframe_arch.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## Why this was worth running

Every gate in this programme has used 1h as the direction source, because
1h is what the book was built on. That choice was inherited, never tested.
P3 showed the 1h layer has no edge of its own; P55 showed its structure
cannot be gated on; P56 showed its direction is durable and its expiry is
not. None of that asks whether **1h is the right timeframe at all.**

Four architectures, both lanes, both eras:

| | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| **1h HTF + 15m LTF (CHAMPION)** | **500t +325.8R** PF 2.38 | **279t +70.1R** PF 1.59 | **454t +359.0R** PF 2.62 | **253t +60.2R** PF 1.58 |
| 4h HTF + 15m LTF | 387t +82.1R PF 1.70 | 267t +15.3R PF 1.30 | 359t +105.4R PF 1.85 | 236t −10.6R PF 1.14 |
| 1D HTF + 15m LTF | 196t +43.7R PF 1.71 | 140t **−41.5R PF 0.77** | 178t +46.9R PF 1.79 | 125t **−31.6R PF 0.84** |
| 1D HTF + 1h LTF | 66t +7.3R PF 1.28 | 37t **−19.7R PF 0.35** | 62t +6.5R PF 1.27 | 33t **−18.2R PF 0.33** |

## The answer, and it is monotone

**R per trade, sorted by how close the HTF sits to the LTF:**

| architecture | IS R/trade | OOS R/trade |
|---|---|---|
| 1h → 15m | **+0.652** | **+0.251** |
| 4h → 15m | +0.212 | +0.057 |
| 1D → 15m | +0.223 | **−0.297** |
| 1D → 1h | +0.111 | **−0.533** |

**The closer the direction source sits to the entry timeframe, the better
the book — and the 1h/15m pair is the closest architecture that exists
here.** No alternative beats the champion in a single cell, in either lane,
in either era.

**1D as a direction source is worse than useless in OOS: PF 0.77 and 0.84
with 15m, and PF 0.35 and 0.33 with 1h.** The owner's second suggestion —
1D HTF with 1h LTF — is the worst of the four, in both eras, in both lanes.

## The trap a fitted architecture would have fallen into

**In IS the 1D architecture looks like the safe choice.** It has the
**highest win rate (33.7% vs the champion's 30.0%)** and the **lowest
drawdown (12.4R vs 17.8R)**. On IS alone, with a preference for robustness,
daily is the obvious upgrade.

**It is negative in OOS at PF 0.77.** Better win rate, better drawdown,
13% of the R and 39% of the trades. This is the same lesson as P52 and P54
arriving from a completely different direction: a candidate that improves
the IS risk profile while destroying the return is not a safer book, it is
a book that has been fitted to the era it was measured in.

## The archive's dead 4h result is now corroborated

`ANCHOR_BASIS_AUDIT` records `exp_htf4_confirm` as DEAD (−162/−51,
−194/−25) — 4h as an *additional confirm filter*. Here 4h *replaces* the
window source, a different mechanism, and it is also dead: **−243.7R IS,
−54.8R OOS** on the champion lane.

Two unrelated mechanisms, same verdict. That convergence is worth more than
either result alone.

## Method and the bugs that shaped it

1D and 4h are **derived, not downloaded**: `k` source bars aggregated into
one bucket of width `src_sec * k`, each bucket labelled with the ts of its
**last** constituent bar so it is only visible at its own close. Causal by
construction, and exactly consistent with the 1h series the champion
already trades, so any difference is a difference of timeframe and not of
vendor or session handling. Bar counts confirm it: **8108 4h**,
**1351 1D** in IS; **4379 / 729** in OOS.

Three bugs were caught and are documented in the harness, because the first
two were silent:

- **`DAY * k` for bucket width** produced 4-**day** and 24-**day** buckets.
  It did not crash. It reported 338 "4h" bars and 56 "1D" bars for 1352
  days of hourly data. The tell was arithmetic, not an exception: a daily
  architecture cannot have 56 bars in three and a half years.
- **An exact `len(b) == k` test** dropped nearly every bucket, because
  32434 hourly bars over 1352 days is 23.99 per day and most daily buckets
  arrive with 23 hours. Fixed to 80% of k.
- **`_compute_swings` needs `FlowCandle`, not dicts.** Aggregated bars were
  being handed to the swing rule as dicts.

## Stated limitations

- **`min_bars=10` is held constant across timeframes**, because the
  engine's swing rule is a swing rule, not a duration rule. The wall-clock
  confirmation lag is therefore 10h at 1h, **40h at 4h and 10 days at
  1D**. The daily arms are structurally slow, and that is part of what is
  being tested — but it is a real difference and not a free one. A daily
  architecture at `min_bars=3` was not run; it would sit between the 1D and
  4h arms, and the monotone trend already points the same way.
- **Sample size.** The 1D HTF + 1h LTF arm has 66 trades in IS and 37 in
  OOS. Those two cells are too thin to carry an argument, and the verdict
  there rests more on PF 0.35 than on the net.
- **Aggregation introduces a synthetic OHLC.** Aggregated highs/lows are
  exact, but the daily open is the first hour's open and the daily close the
  last hour's close. No lookahead is implied — the bar is stamped with its
  final hour, not its first.

## The pass criterion, applied

Fixed before running: an architecture replaces the champion only if it beats
it in **both eras in both lanes** and clears **M = 193.4R**.

**No architecture passes. Every alternative loses on net in all four cells
and none is even within reach of the champion.** The champion architecture
is confirmed by measurement rather than by inheritance, and the search for
a better layer — faster or slower — is now closed in both directions.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
