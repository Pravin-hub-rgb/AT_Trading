# REAL STOP SLIPPAGE, MEASURED

Measured from `data\forward\bybit\BTCUSDT_1m.csv` - 51778 real Bybit BTCUSDT minute bars, 2026-09-13 10:03 to 2026-10-19 09:00.

A stop-market at price S fills at the open of whichever minute first
trades through S, so the slippage is observable rather than assumed. If
that bar opens beyond S the fill is the open and the slippage is
(S-open)/S. If the bar opens on the good side and only the low reaches
S, the fill is essentially S. Taker cost is charged separately at
5.5 bps because the exit leaves the book either way.

| stop distance | hits | gap-through rate | p50 gap | p95 gap | p99 gap | worst |
|---|---:|---:|---:|---:|---:|---:|
| 0.50 | 19743 | 0.000 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps |
| 1.26 | 4793 | 0.000 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps |
| 1.95 | 1251 | 0.000 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps |
| 3.00 | 0 | 0.000 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps |
| 5.00 | 0 | 0.000 | 0.0 bps | 0.0 bps | 0.0 bps | 0.0 bps |

## The finding that matters

Zero gap-throughs, across every stop distance, on real Bybit data.
That is NOT the market being calm and it is NOT synthetic data - the
whole feed was verified byte-for-byte against a fresh download. It is
that Bybit's continuous-contract klines set each candle's open to the
previous close, so a minute can never open somewhere the previous one
did not already trade.

The consequence for the engine: `fill = min(stop, open)` in
`unified.py:1760` will resolve to `stop` essentially every time,
because `open` is never already past the stop. The gap branch exists,
is correct, and is almost never taken.

So stop-gap risk cannot be measured from candles at all. It needs tick
data or live fill acknowledgements. Until then every reported net R
assumes a clean stop fill, and that assumption is unfalsifiable from
anything in this repository.

## Why distance changes the answer

A wider stop is not a bigger number, it is a rarer event. At 0.5% the
stop sits inside ordinary noise; at 3% the stop is only reached when
something has already gone wrong. Charging every book one slippage
figure therefore measures a number that belongs to none of them.

## Caveats

- 51778 minutes of one symbol in one regime. A month with a large
  liquidation cascade would produce a heavier tail than this shows.
- Minute bars cannot resolve sub-minute order-book depth, so the gap
  figures are a lower bound on the true fill cost.
- Measured on long-side stops. Short-side gaps are the mirror image
  and over this window were not separately tallied.
- Forward fills from the live bot are the only way to confirm this.
  This is real market data, not real order acknowledgements.
