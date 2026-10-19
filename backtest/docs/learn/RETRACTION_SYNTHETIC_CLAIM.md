# RETRACTION: the "synthetic data" finding was wrong

Written after being proved wrong, not before. If you are reading this to
understand why earlier reports claim the candles were fabricated, here is the
correction.

---

## What was claimed

Across several commits I asserted that the 1-minute candle data in this repo was
synthetic, reconstructed from 15-minute bars, and that therefore:

- every backtest result was optimistic and unsafe
- the UI's 1m chart was fake
- the 1m data should be deleted and replaced
- the slippage gap risk could not be measured because of that fabrication

The evidence offered was a single property of the files:

```
open == previous close, in 1,945,713 of 1,945,713 rows
```

That was presented as proof of reconstruction.

---

## Why it was wrong

Bybit's continuous-contract klines construct each candle's open from the
previous candle's close. That is how the exchange publishes a continuous series,
and it is why 99.7% of bars show zero gap. A structural property of the feed was
read as an anomaly in the data.

It was never verified against the source.

---

## What was done to check it

A fresh 3,048,696-row download of BTCUSDT 1m from Bybit, 2021-01-01 onward, and
a byte-level comparison against what was already in the repo:

```
btc_data/is/BTCUSDT_1m.csv   (2023-01-01 -> 2026-09-13,  1,945,714 rows)
  timestamps   IDENTICAL
  open         maxdiff 0.0000
  high         maxdiff 0.0000
  low          maxdiff 0.0000
  close        maxdiff 0.0000

btc_data/oos/BTCUSDT_1m.csv  (2021-01-01 -> 2022-12-31, 1,050,870 rows)
  all four OHLC columns      maxdiff 0.0000
```

The existing files were real Bybit downloads. Every backtest, every T1-T4 result,
every book in the shortlist, and the 1m chart in the UI had been run on real
market data all along.

The forward file differs from the fresh download in exactly one row - the final
candle, which was still forming when it was written:

```
rows with different close: 1 / 37,473
2026-10-09 10:35:00   fresh 82290.8   stored 82287.6
```

That is a live candle, not a reconstruction.

---

## The mistake in method

Three distinct failures, worth naming because they will recur:

1. **A single heuristic was treated as proof.** `open == prev_close` is a
   normal property of continuous contract klines. One flag was enough to declare
   fraud across three files and four years of data.

2. **The conclusion was never checked against the source.** Bybit was
   reachable. One API call and one comparison would have settled it. Instead the
   finding was escalated, acted on, and written into documentation - including a
   report titled as though the question were closed.

3. **The owner was told the data was unusable without being offered the cheap
   test.** The owner had already been suspicious of the numbers. Confirming a
   suspicion by asserting it is the failure mode, not the fix.

An independent audit earlier in this work had flagged that code here produced
"plausible but wrong" results repeatedly. The same pattern applied to the
reasoning, not just the code.

---

## What survives from that work

The slippage finding stands, and it now rests on better ground. It was never
about synthetic data:

```
Stop-gap risk cannot be measured from candles. At the 1.26% median stop these
books use, 4,793 stops produced ZERO gap-through fills on real Bybit data,
because no minute bar ever opens beyond where the previous one closed.

That is a property of candle granularity, not of the market. BTC gaps inside a
minute constantly. Resolving it needs tick data or live fill acknowledgements.
```

So the engine's `fill = min(stop, open)` (`unified.py:1760`) resolves to `stop`
essentially every time. The gap branch is correct, and almost never taken. Every
reported net R in this repo assumes a clean stop fill, and that assumption
cannot be falsified from anything held here.

What did not survive: the claim that this made every result untrustworthy. The
results stand, subject to that one unfalsifiable assumption, which is a smaller
and better-characterised problem than "the data is fake".

---

## Data actually changed

One thing from that work was worth keeping. The forward window was extended
from 2026-10-09 to 2026-10-19 using the fresh download:

```
data/forward/bybit/BTCUSDT_1m.csv    37,473 -> 51,778 rows  (+9.9 days)
data/forward/bybit/BTCUSDT_15m.csv    2,498 ->  3,453 rows
data/forward/bybit/BTCUSDT_1h.csv       625 ->    864 rows
```

That is the only edit to any data file in this repository's history caused by
that investigation.

---

## Reproducibility check

Because the data was questioned, the whole battery was re-run against the
verified files. 338 metrics across 13 books and 2 eras, compared value by value
against the previous run:

```
DIFFERENCES: 0
BIT-IDENTICAL
```

The pipeline is deterministic and the earlier numbers are reproducible.