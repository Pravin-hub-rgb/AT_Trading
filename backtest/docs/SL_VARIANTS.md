# SL VARIANTS — 0/4 work. And the B1 numbers are an artefact, not a result

The user asked for two things: entry at B1 instead of B2, and SL variants.
They came back very different. One produced a clean negative, the other
produced numbers I am explicitly **not** claiming.

## Part 2 first — SL variants, path-true, these are real

Real engine runs on the engine's own knobs, so a different stop changes which
trades survive and when they exit. Delta vs the champion's own
`sl_buf_atr=0.01`.

| arm | is/champion | is/utcsat | oos/champion | oos/utcsat |
|---|---|---|---|---|
| **baseline buf 0.01** | +325.8 | +358.9 | +70.2 | +60.2 |
| buf 0.10 | **−32.6** | +2.2 | **−10.1** | **−9.6** |
| buf 0.25 | **−68.6** | **−41.0** | +9.9 | **−0.9** |
| causal SL | **−77.8** | **−63.2** | +9.9 | +12.6 |
| pivot trail | **−156.0** | **−149.5** | **−72.7** | **−49.0** |

**0 of 4 variants work.**

- **Wider SL buffer is strictly worse.** Every step out from 0.01 loses money
  in 3 of 4 cells, and calmar falls with it (is/champion 3.20 → 2.90 → 2.51).
  The champion's 0.01 buffer is not a leftover default; it is load-bearing.
- **Causal SL is era-flipped** — IS −77.8 / −63.2, OOS +9.9 / +12.6. This is
  the fifth IS-only/OOS-only candidate in this line of work.
- **Pivot trail is catastrophic** and is the clearest signal in the table:
  oos/champion goes **+70.2R → −2.5R** with PF collapsing 1.34 → 0.99, and it
  loses in all four cells. It also adds trades (279 → 295), i.e. it makes
  more entries and they are worse — the same pattern as the trade-expansion
  study.

**The champion's existing stop configuration survives every variant tried
against it.**

## Part 1 — B1 entry: the numbers are an ARTEFACT, do not use them

The run printed things like "B1 + 1.0 ATR stop → net +1426.3R" against a base
of +358.9R. That is not a 4× improvement. It is a broken comparison, and I
am reporting it only to say so.

Why it is invalid:

1. **The R denominator does not match the engine's.** The engine's risk is
   `|B2_entry − sl|`. I divided by `|B1 − swing_low|` and by ATR. A different
   denominator is a different unit — that alone makes the numbers
   uncomparable to the base book.
2. **The exit is the engine's B2-era trailing exit.** Holding a trail fixed
   while moving the entry earlier is not a simulation; a real earlier entry
   would be stopped out far more often, and none of that is captured.
3. **The median R gives it away.** "B1 + swing-low SL" shows a median of
   **−0.179**R. A strategy with an actual stop cannot produce that — a
   stop-out is −1R by definition. The number shows the stop is doing nothing
   and the trade is being priced against a trail exit, so the "SL" in the
   label is not the SL being tested.

A first pass was worse still (avg +19.4R, net +9700R) because B1 fills often
land within a hair of the swing extreme, making the denominator collapse. A
degenerate-risk guard (exclude stops closer than 0.25 × ATR, counted not
hidden) fixed that arithmetic but not the three structural problems above.

**There is no engine kwarg for "enter at B1".** `exp_b1_b2_mode` is a blocking
filter on the B2 trigger (`block_immediate`, `block_0_1`, `block_age<N>`), not
a different trigger. Doing this properly means patching the engine's signal
selection to fire on B1 and re-running the whole path — including its stops,
trail, cooldown and streak. **That was not done here**, so the honest answer
on B1 is *unknown*, not *great*.

## Two traps hit in this one run

Both are the same failure class, and the second was already known from the
previous study — which makes the repeat worth recording:

1. Degenerate risk denominator (B1 fill on top of the swing extreme).
2. Reading a differently-normalised R as a book-level improvement.

Both produce spectacular, entirely fake numbers. The guard for the first
existed a study earlier and still had to be re-applied here.

## Status

**NOT ADOPTED.** Nothing changed. `sl_buf_atr` stays at 0.01; `exp_causal_sl`
and `exp_pivot_trail` remain off.

If the B1 question matters, the next step is an engine patch (entry trigger
= B1) with a full path-true run, not arithmetic on an existing book. That is
a real piece of work and it is not what this harness did.

## Files
- `backtest/tests/exp_b1_sl_variants.py` → `_b1_sl_variants.json`
