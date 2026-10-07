# The best cell is real, and trading it alone is too small to ship

Date: 2026-10-07. Engine post-C17. Harnesses: `exp_best_cell_lens.py`,
`exp_best_cell_mode.py`, `exp_mltf_decompose.py`, `exp_cell_gate_mode.py`.
Book: `fsent_champ_long`.

Continues `MODE_REGIME_ROUTING.md`, which found the gap. This file asks the
follow-up: the book does its best work in one joint regime cell — would trading
*only* that cell be a book?

## The short answer

The cell is genuinely good and genuinely too small. Both halves of that are
measured below, and neither is estimated.

## What the cell is

`chop_HIGH / atr_low` — the 1h travelled efficiently (CHOP index above 58.0)
while 15m bars are quiet (ATR% below 0.65). Thresholds are the book's own,
unchanged. **No threshold anywhere in this file was fitted.**

| | n | net | mean R | max DD | vs book |
|---|---:|---:|---:|---:|---|
| IS cell | 75 | +132.0 | **+1.76** | **7.6** | book: 528 / +1.01 / 13.4 |
| OOS cell | 42 | +109.5 | **+2.61** | **4.7** | book: 311 / +0.77 / 11.9 |

It is 14% of trades and 24.7% / 45.7% of the net. Better mean R *and* less than
half the drawdown, in both eras.

## And it passes the bar that closed everything else

Every routing arm in `MODE_REGIME_ROUTING.md` failed one test: a gain that
vanishes when its largest trade is removed. ch=55 was two trades at 21R each;
ch=50 was one trade supplying 46R.

This cell does not fail it:

| era | n | net | largest | without top | without top 3 |
|---|---:|---:|---:|---:|---:|
| IS | 75 | +132.0 | +48.6 | **+83.4** | +41.3 |
| OOS | 42 | +109.5 | +26.1 | **+83.4** | +45.6 |

That is the first candidate in this thread with a distributed edge. It is
recorded as such, and it is also not what got shipped.

## Two engine modes added, and why the first one was wrong

`mode="chop_hi_atr_lo"` and `mode="chop_hi_atr_lo_gate"` now exist in
`unified.py`. Neither is used by any book. The first version was implemented as

    use = "decisive" if (ch > chop_thresh and atrp < atr_high_thresh) else "flip"

and `exp_best_cell_mode.py` step 1 reported `MISMATCH - mode is not the rule we
measured`: 528 IS trades of which 75 were in the cell.

**That check earned its keep.** Every branch in the router is "decisive else
flip", so a rule written that shape always admits the flip branch and can never
be a subset of one cell. The code did not implement the measurement. Had the
check been treated as decoration and the net R read as a result, the write-up
would have claimed a mode that did not exist.

`exp_mltf_decompose.py` then ruled out the innocent explanation. `exp_knob_binds`
had established `exp_mltf` is inert at `max_positions=0` and live at
`max_positions=1`, so it was a plausible culprit for the rest of the set. It is
not: on/off gives identical counts at every setting this book uses (528/528 IS,
311/294 OOS). The layer below the regime filter is not the story.

The gate version is a different shape — skip anything outside the cell:

    if not (ch > chop_thresh and atrp < atr_high_thresh): continue
    use = "decisive"

and it targets correctly: **135 of 144 IS trades and 55 of 58 OOS trades are in
the measured cell (93.8% / 94.8%)**. The residue is `exp_persist` hysteresis,
which holds a routed decision across bars by design.

## What the gate produces as a whole book

| | n | net | mean R | max DD |
|---|---:|---:|---:|---:|
| IS | 144 | +116.0 | +0.81 | 25.2 |
| OOS | 58 | +37.6 | +0.65 | 11.0 |

Two things go wrong, and they are different in kind.

**Size.** 58 OOS trades. The same gate yields 144 in IS. That is a 2.5x era gap
driven by sample length, and a book that trades 58 times out of sample cannot be
sized from it. Registering this would ship a 40-trade record.

**Drawdown.** Gating makes IS DD *worse*: 25.2R against the full book's 13.4R.
Taking only the best cell does not lower risk, because the cell's own drawdowns
are clustered in time while the rest of the book was interleaved between them.
Concentration raises peak-to-trough even as it raises mean R. This is the same
quantity the halt governance note in `EQUITY_LENS_EXT_AND_NOHALT.md` is about,
and it points the same way.

The outlier bar passes (+67.4R IS, +18.1R OOS without the top trade), but
without the top *three* OOS goes negative at −9.6R. On 58 trades that is not a
thin margin, it is no margin.

## Verdict

**Not registered. No pins changed. Shipping config untouched.**

The cell stays a finding, not a book. What it is good for is the opposite of what
was tried: not a replacement for the book, but a candidate **filter on** it, or
a sleeve with a sizing rule attached. Both need their own measurement, and both
inherit the same caveat — the per-cell result is day-1 analysis on the shipping
book, and the day it is promoted it becomes an in-sample claim.

The engine modes are left in place, unused and inert at every default, because
they are the measured rule and the next person should not have to re-derive it.
`fsent_champ_long` pins re-derive to 528 / +533.37 under the edited engine, so
adding them changed nothing that already shipped.