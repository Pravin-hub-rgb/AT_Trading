# The best cell is real. Trading it is not a book, not a sleeve, not a filter.

Date: 2026-10-07. Engine post-C17. Harnesses: `exp_cell_filter.py`,
`exp_cell_sleeve.py`, `exp_cell_shape.py`. Continues `CELL_GATE_NOT_A_BOOK.md`,
which gated the cell and found 58 OOS trades and worse IS drawdown.

Four things were tried against that. All four are recorded here, including the
two that were implemented wrongly before being fixed, because the failures are
the reusable part.

## The finding that started all of this

`chop_HIGH / atr_low` — efficient 1h travel inside quiet 15m bars — is where
`fsent_champ_long` does its best work. +1.76R mean IS, +2.61R mean OOS against
+1.01 / +0.77 for the whole book, at max DD 7.6R / 4.7R against 13.4R / 11.9R.
It is 14% of trades and 24.7% / 45.7% of the net.

It is also the only candidate in this whole thread that **survives the outlier
bar**: profitable in both eras with its single largest trade removed (+83.4R
both) and with its top three removed (+41.3R / +45.6R). Every routing arm built
on it failed that test.

## 1. The cell as a filter — the union shape is a trap

`exp_cell_filter.py`, `mode="atr_high_or_chop_hi_atr_lo"`. Keep the shipping arm,
add the cell as extra permission. Persist grid 0–7, both eras.

**The first implementation measured −392R IS and −194R OOS.** It was written:

```python
if not (atrp > t or (ch > c and atrp < t)): continue
use = "decisive"
```

which looks like a union and is not one. `continue` drops the signal entirely, so
every flip-branch trade the book depends on was removed — 467 trades in IS. The
correct shape falls through to the ordinary router instead:

```python
if atrp > t or (ch > c and atrp < t): use = "decisive"
else: use = "flip"
```

Structural result, no winner:

| persist | IS net | Δ IS | OOS net | Δ OOS | |
|---|---:|---:|---:|---:|---|
| 0 | 452.3 | −81.1 | 196.1 | −43.5 | worse |
| 2 | 366.0 | −167.4 | 267.8 | +28.2 | era-split |
| 4 | 458.3 | −75.1 | 246.4 | +6.8 | era-split |
| 5 | 519.4 | −14.0 | 268.4 | +28.8 | **era-split** |
| 7 | 533.5 | +0.1 | 217.3 | −22.3 | era-split |

persist=5 is the closest thing to a candidate: +28.8R out of sample. It costs
−14.0R in sample to get it, which is the era-split pattern this repo has now seen
eight times. **Not adopted.** The added trades are worth −19.0R out of sample at
persist=7 and only turn positive at a persist value that costs in-sample R.

## 2. The cell as a sized sleeve — 0.65 correlation, so sizing is not free

`exp_cell_sleeve.py`. Arithmetic on the two already-measured curves, blending
monthly R at weights 0.00 → 1.00. Nothing re-simulated.

**The number that matters is the correlation:**

| era | cell vs whole book, monthly R |
|---|---:|
| IS | +0.688 |
| OOS | **+0.649** |

Both eras around +0.65-0.69. The cell draws down *with* the rest of the book
rather than against it, so it is not a diversifier. That is what makes sleeve
sizing unattractive here: it is not a diversifier. The
OOS blend curve shows max DD falling from 8.1R at w=0 to 4.3R at w=0.75 — but net
falls from +239.6R to +88.1R over the same range, so the drawdown improvement is
bought by giving up return, not by diversification. At w=1.00 it turns back up to
10.6R as the cell's own clustering takes over.

This table is a sensitivity analysis, not a candidate. w=0.00 and w=1.00 are both
the whole book, because the blend never removes a trade. Reading w=0.5 as "a book"
would repeat exactly the error from item 1.

## 3. persist on the gate — the grid is flat because it cannot bind

`exp_cell_shape.py`. Persist 0–7 on `chop_hi_atr_lo_gate`:

| persist | IS | OOS |
|---|---|---|
| 0–7, all identical | 144 / +116.0 / 25.2 | 58 / +37.6 / 11.0 |

Eight identical rows. That is not a measurement to trust at face value, and the
reason is structural: **the gate `continue`s on every signal outside the cell, so
`use` is never assigned for those signals and the v19 hysteresis state
(`_rg_s` / `_rg_c`) never advances.** The stickiness `exp_persist` controls exists
only on signals that survive the gate, and on a cell covering 14% of bars there is
almost nothing for it to stick to.

**`exp_persist` is structurally inert on any gate-shaped mode.** That is a
property of the mode shape, not of this threshold. Sweeping persist on a gate is
not a question this engine can answer, and a future gate should assign
`use="flip"` rather than skipping if it wants persist to be reachable.

## 4. Drawdown shape — the clustering explanation, measured

The previous write-up asserted that gating worsened IS drawdown because the cell's
drawdowns cluster in time. Measured, per era:

| | IS book | IS gated | OOS book | OOS gated |
|---|---:|---:|---:|---:|
| n | 528 | 144 | 311 | 58 |
| net | +533.4 | +116.0 | +239.6 | +37.6 |
| max_dd | 13.4 | **25.2** WORSE | 11.9 | 11.0 better |
| dd_dur | 22 | **34** WORSE | 29 | **14** better |
| ulcer | 16.79 | **642.09** WORSE | 14.23 | 14.99 WORSE |
| **max_streak** | 11 | **12** WORSE | 15 | **13** better |
| pf | 3.09 | 2.03 | 2.69 | 1.89 |
| top5_share_pct | 80.2 | **134.9** | 81.1 | 100.4 |
| trimmed | 0.298 | **−0.204** | 0.236 | 0.047 |

Two things here, and the second is the important one.

**IS is worse on every axis, including the one the halt exists for.** Longest
losing run 11 → 12. `top5_share_pct` 134.9 means the top five trades are *more*
than the cell's entire net — the cell is more concentrated than the book, exactly
as the clustering story says. `trimmed` goes negative, so the cell's edge is
carried by its largest trades even though it survives the outlier bar.

**OOS is better on depth, duration and streak.** max_dd 11.9 → 11.0, dd_dur 29 →
14, max_streak 15 → 13. The eras disagree, which is itself the answer: the cell's
drawdown profile is not stable across eras, and a rule whose risk profile flips
sign between eras is not a risk improvement.

## Verdict

**Nothing adopted. No book registered. No pins changed. Shipping config
untouched.** The three engine modes added for this line stay in place unused and
inert at every default.

What is established:

- The cell is **real** — best mean R in both eras, least drawdown of any
  candidate, and the only thing here that survives its outlier bar.
- It is **not a book** (58 OOS trades), **not a sleeve** (0.65 correlated with the
  book, so sizing buys no diversification), and **not a filter** (every persist
  setting loses in one era).
- Its **drawdown profile flips sign between eras**, which is the reason none of
  the three uses works. A cell that is safer out of sample and more dangerous in
  sample is not a risk tool.
- `exp_persist` is **structurally inert on gate-shaped modes** — a reusable engine
  fact that cost this experiment a full sweep to find.

The honest next step, if there is one, is not another threshold and not another
weight. It is asking whether the cell's IS concentration and OOS calm can be
reconciled by a rule that is not "take the cell" — and the answer to that is
probably a longer OOS sample than this repo has, which is a data problem rather
than a code one.