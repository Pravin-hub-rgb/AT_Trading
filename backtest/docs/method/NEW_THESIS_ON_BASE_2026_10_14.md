# The three new theses on the bare base — 2026-10-14

Owner ask: stop refining, take the base with no filters at all (HTF + LTF only),
and put a new hypothesis on it.

All three theses were run. All three are negative. The diagnostic they produced
is more useful than a win would have been, so it is recorded here in full.

## The base

`backtest/docs/pipeline/BASELINE.md` publishes `champion_single_sw10` as the
base. It cannot be used:

- it is **retired** — `registry/retired.py:82`, bar 1, out of sample negative;
- its pins no longer reproduce — pinned IS 395 / +48.63R, measured IS 341 /
  −14.32R. They predate the current engine;
- `champion_multi_sw10`, the other candidate, sets `pivot_rule="origin"`, which
  `kingsweep.py:232` marks **look-ahead**.

So the base was rebuilt from the engine signature itself —
`simulate_htf_ltf_streak_halt` called with its own defaults and nothing added:
`mode="chop"`, `cooldown_bars=0`, `max_consecutive_losses=0`, `max_positions=0`,
no partial exit, no `exp_` filter. Measured fresh in `base_book.py`.

| | trades | net R | R/trade | win % |
|---|---:|---:|---:|---:|
| IS | 503 | +105.18 | 0.2091 | 22.1% |
| OOS | 278 | **−33.68** | −0.1212 | 21.6% |

**The bare base loses out of sample at a 22% hit rate.** That is the honest
starting point, and it is a much weaker book than any of the 94 shipping ones.

### The engine's own default is a look-ahead

`unified.py:304-310` — `exp_causal_sl=0` is the default, and it anchors the stop
to the swing's true origin, "only knowable once the leg has completed". The base
sets `exp_causal_sl=1`. Measured both:

| | IS | OOS |
|---|---:|---:|
| `exp_causal_sl=0` (engine default, look-ahead) | +93.83R | −25.09R |
| `exp_causal_sl=1` (the base, causal) | +105.18R | **−33.68R** |

Removing the look-ahead costs 8.59R out of sample. Any future base quoted at
−25.09R is quoting the cheat.

## T1 — the concurrent-slot thesis: FAILED

**Hypothesis.** The base peaks at six concurrent positions. The k-th position is
a structurally different bet from the first, so the book may not be six
independent bets at all.

**Measured.** Reconstructed slot from each trade's own entry/exit timestamps.
No future information enters the classification.

| slot | IS n | IS R/trade | OOS n | OOS R/trade |
|---|---:|---:|---:|---:|
| 1 | 352 | 0.0690 | 194 | −0.0087 |
| 2 | 98 | 0.4673 | 56 | −0.4092 |
| 3 | 33 | 1.2921 | 22 | −0.1491 |
| 4 | 15 | −0.5827 | 3 | −0.7846 |
| 5 | 4 | −0.4163 | 2 | −1.1372 |
| 6+ | 1 | 2.8619 | 1 | −1.1748 |

**The effect reverses between eras.** In sample the later slots are *better*
(gap −0.4667 R/trade in favour of slot 1); out of sample they are *worse* (gap
+0.3722 in favour of slot 1). Slot 3's IS 1.2921 rests on 33 trades and becomes
−0.1491 out of sample. There is no sequence effect. The base's problem is not
where a trade sits in the queue.

### A real bug the first sweep exposed

The first run swept `max_positions` over 1,2,3,4,5,6,8 and got **byte-identical
results — 356 trades, +58.11R — for every value above 1.**

That is not a flat curve. `unified.py:357-363`: `max_positions` is a **1/0
serial gate**, not an N-cap. `1` means serial, `0` means unlimited, because it
uses a single `busy_until` timestamp and cannot express "at most N open". The
real cap is a different knob, `exp_max_concurrent`.

The genuine N-cap curve:

| cap | IS n | IS net | IS R/trade | OOS n | OOS net |
|---|---:|---:|---:|---:|---:|
| 1 | 356 | +58.11 | 0.1632 | 195 | −1.25 |
| 2 | 470 | +51.14 | 0.1088 | 256 | −26.77 |
| 3 | 492 | +110.44 | 0.2245 | 275 | −31.15 |
| 4 | 502 | +102.32 | 0.2038 | 276 | −31.42 |
| 5 | 503 | +105.18 | 0.2091 | 277 | −32.51 |
| none | 503 | +105.18 | 0.2091 | 278 | −33.68 |

Cap 3 is the only setting that lifts R-per-trade in both eras, by **+0.0154 IS
and +0.0079 OOS**. That is under 1% — the same class of noise `garch` turned
out to be, and it is not a result. The base essentially never exceeds four
concurrent positions.

## T2 — the 4h layer: FAILED, and it reverses

**Hypothesis.** Everything in this repo lives on two planes, 1h and 15m. A 4h
layer is a genuinely new input — the only one left — and it should lift the 22%
hit rate without touching entry or exit.

**Built.** 4h candles by bucketing the 1h series on `floor(ts / 14400)`, so
bars align to absolute 4h boundaries. Swings via `_compute_swings` on
`FlowCandle` objects (`firstswing.process_bar` does `c.date` and raises on a
dict). A 4h swing is read only from its `confirmed_at_idx` mapped to its own
candle timestamp — never from the leg it describes.

| | IS R/trade | OOS R/trade |
|---|---:|---:|
| base | 0.2091 | −0.1212 |
| take only 4h-**agreeing** | −0.1439 (n=237) | −0.0578 (n=149) |
| take only 4h-**disagreeing** | **+0.5236** (n=266) | −0.1943 (n=129) |

**In sample the 4h direction is exactly backwards; out of sample it is right
again.** Neither arm survives both eras. A full sign flip on the one axis that
had never been touched is the clearest possible statement that this was noise
all along.

Two arms of the sweep are also **not independent evidence**: `min_bars=4` and
`min_bars=6` produce identical results to four decimals, because the direction
of the last *confirmed* 4h swing does not change with leg length.

### A silent bug worth recording

The first run reported 503 of 503 trades "disagreeing" and 0 agreeing. Trades
carry `dir` as `'long'`/`'short'`; swings carry it as `'up'`/`'down'`. Comparing
them as strings produced a confident, complete, meaningless result. It now
asserts the swing vocabulary instead of assuming it.

## T3 — the exit thesis: FAILED, but it diagnosed the book

**Hypothesis.** The base wins 22% of the time, so it must be paid for by
asymmetry. If losers sit for a long time before dying, cutting them recovers R
for free.

**The shape says the opposite.**

| | winners median bars | losers median bars | winner avg R | loser avg R | payoff | break-even WR | actual WR |
|---|---:|---:|---:|---:|---:|---:|---:|
| IS | 235 | 32 | +4.627 | −1.042 | 4.44:1 | 18.4% | 22.1% |
| OOS | 221 | 29 | +3.079 | −1.002 | 3.07:1 | **24.6%** | **21.6%** |

**Losers die about seven times faster than winners run.** Median 32 bars against
235. There is no time to cut them — by bar 32 most have already resolved.

Every cut rule tested made things worse in **both** eras, 15 combinations of
`K ∈ {2,4,8,16,32}` × `cut ∈ {−0.25,−0.5,−0.75}R`, worst case −0.4017 R/trade on
OOS. Cutting catches trades that would have recovered.

### What the shape actually says

This is the finding worth keeping.

- **In sample the book is comfortably profitable.** Payoff 4.44:1 needs an 18.4%
  hit rate to break even. It gets 22.1%.
- **Out of sample both terms decay together.** Payoff falls 4.44 → 3.07, which
  raises the required hit rate to 24.6%, and the hit rate itself falls 22.1 →
  21.6%. It misses by about three points.

So the base is not broken by one missing filter. It is a **thinner edge out of
sample, thinner on both sides at once**. Any addition that lifts the win rate
while leaving payoff alone would have to clear 24.6% to break even out of
sample — a higher bar than in-sample, which is the opposite of how a filter is
normally justified.

## Summary

| thesis | verdict |
|---|---|
| T1 concurrent slot | no slot effect; effect reverses between eras |
| T1 N-cap | best case +0.015 IS / +0.008 OOS R/trade, under 1%, noise |
| T2 4h layer | full sign flip between eras |
| T3 exit cut | losers already die fast; all 15 cut rules worse in both eras |

**Nothing registered. Nothing promoted. No book config touched.**

The three axes are now closed rather than untried, which is worth something: the
owner asked for new hypotheses and got three honest negatives instead of another
refinement.

Two side findings that are not theses but are real:

- the engine's shipped default `exp_causal_sl=0` is **look-ahead**, worth 8.59R
  out of sample on this base;
- `max_positions` is a **serial 1/0 gate**, not an N-cap. Anyone sweeping it as
  if it were a cap gets six identical rows and may read the flatness as a
  result.

## What is left

The base is weak, and T3 says why: out of sample the payoff ratio and the hit
rate decay together. That is not a filter-shaped problem. The remaining
untested surface is capital, not signals — how much is risked per position and
whether size should respond to the 1h window's own quality. That is also the one
axis where a *negative* out-of-sample result costs nothing, because position
sizing cannot manufacture trades that the edge did not produce.