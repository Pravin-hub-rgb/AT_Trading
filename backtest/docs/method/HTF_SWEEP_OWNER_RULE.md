# HTF sweep — the owner's rule applied to the plane almost nobody swept

Date: 2026-10-09. Harness: `exp_htf_sweep.py`. Pins: `exp_register_htf15.py`.

The owner's rule, which is now the score used throughout:

> "kabhi negative nahi hona chahiye yaar"

That is a per-cell robustness criterion, not a return criterion, so it is what
this ranks on.

---

## what the HTF plane actually is, since it came up unclear

The engine is called as

```python
sim(c1h, HTF_SWINGS, c15, LTF_SWINGS, fine_ltf=fine)
```

- **LTF = 15 minutes.** Every trade signal is formed here.
- **HTF = 1 hour.** This is the context plane. `swings_htf` feeds exactly four
  things in the engine: the leg ratio (`seg start_px / end_px`), the
  bias-momentum breaks (`exp_bias_momentum_min`, which the sig book runs at 0.8
  and the champ book leaves off), the bias-flip series, and `_sw_ts_dir_mag` —
  which is what classifies each trade as `flip` or `decisive`.

So the HTF knob is **the 1h swing series**, currently built at `min_bars=10`
(1601 swings). A longer leg means fewer, larger HTF windows.

**The plateau is real but short.** Swing counts: `min_bars` 3 → 1620, 5 → 1620
(identical), 8 → 1617, 10 → 1601, 14 → 1505, 20 → 1316, 30 → 1056, 40 → 868. So
3–5 is a genuine no-op plateau; from 8 onward the series really does change, and
the sweep is measuring something.

---

## the sweep

**12 half-year cells** (IS 2023-01→2026-09 = 8 cells, 2021-22 = 4). Both eras are
held data — see `OOS_IS_NOT_A_HOLDOUT.md` — so nothing here is forward.

### `fsent_champ_long` — current setting `min_bars=10`

| htf mb | n | net | dd IS | dd OOS | **negative cells** |
|---:|---:|---:|---:|---:|---|
| 3 | 843 | +766.8 | 13.8 | 11.9 | **0** |
| 5 | 843 | +766.8 | 13.8 | 11.9 | **0** |
| 8 | 843 | +766.8 | 13.8 | 11.9 | **0** |
| **10 (current)** | 839 | +773.0 | 13.4 | 11.9 | **1** — 2025-H1 |
| 14 | 802 | +796.5 | 17.7 | 14.9 | **0** |
| 20 | 819 | +733.2 | 15.1 | 19.0 | **0** |
| **30** | 802 | **+847.3** | 15.3 | 18.5 | **0** |
| 40 | 768 | +637.2 | 13.8 | 14.2 | **0** |

### `fsent_sig_multi` — current setting `min_bars=10`

| htf mb | n | net | dd IS | dd OOS | **negative cells** |
|---:|---:|---:|---:|---:|---|
| 3 | 525 | +684.8 | 13.4 | 8.9 | **0** |
| 8 | 523 | +686.0 | 13.4 | 8.9 | **0** |
| **10 (current)** | 523 | **+704.4** | 13.4 | **7.6** | **0** |
| 14 | 501 | +674.0 | 13.5 | 10.4 | **0** |
| 20 | 496 | +639.0 | 10.9 | 5.7 | **1** — 2026-H2 |
| 30 | 489 | +632.0 | 12.6 | 8.3 | **1** — 2026-H2 |

**`sig_multi` is already clean at its current setting.** Raising its HTF leg only
costs net and eventually breaks the rule.

---

## the best number is a trap, and it is the reason the neighbourhood was checked

`min_bars=30` posts **+847.3R with zero negative cells** — the best number in the
sweep. It is also a **spike**:

| mb | 24 | 26 | 28 | **30** | 32 | 34 | 36 |
|---|---:|---:|---:|---:|---:|---:|---:|
| net | +645.4 | +742.5 | +659.6 | **+847.3** | +696.3 | +562.5 | +567.6 |
| negatives | 2 | 1 | 2 | **0** | 0 | 0 | 1 |

**A 200R peak with a 60R trough either side is not an edge.** That is the grid-peak
failure P69 warns about, and it would have been adopted on a single number.

## the real finding is a plateau

| mb | 12 | **13** | **14** | **15** | 16 | 18 |
|---|---:|---:|---:|---:|---:|---:|
| net | +783.5 | **+787.6** | **+796.5** | **+822.4** | +746.1 | +708.7 |
| dd IS | 13.4 | 13.4 | 17.7 | 17.3 | 18.0 | 18.6 |
| negatives | **1** | **0** | **0** | **0** | **0** | 1 |

**`min_bars` 13–15 is a plateau where the negative half-year disappears AND the
net rises** from +773.0R to between +787.6R and +822.4R. At 12 the negative cell
is still there; at 18 it comes back. That is a region, not a point.

**`min_bars=15` is the registered one** — the highest net inside the plateau and
the only point where both drawdowns are contained.

---

## registered: `fsent_champ_long_htf15`

| | trades | net | dd | WR |
|---|---:|---:|---:|---:|
| IS | 520 | **+567.57** | 17.28 | 41.2% |
| OOS (2021-22) | 280 | **+254.88** | 16.86 | 37.1% |
| parent IS | 528 | +533.37 | 13.42 | 40.0% |
| parent OOS | 311 | +239.59 | 11.88 | 37.0% |

**+34.2R in sample and +15.3R out, on 8 and 31 fewer trades, with the negative
half-year gone.**

`exp_fastcheck` reproduces every pinned field on both eras.

### period control

| era | raw gap | b | t | MDE | month bootstrap | calendar explains |
|---|---:|---:|---:|---:|---:|---:|
| IS | +0.2850 | +0.5681 | +1.073 | 1.0372 | +0.4358 | 98% |
| OOS | +0.1084 | +0.3723 | +0.907 | 0.8050 | +0.3428 | 98% |

**`b` is positive in both eras with 97–98% of the raw gap surviving, so this is
not a regime proxy.** But **both cells are underpowered against their own MDEs** —
the magnitude is not established. That is stated in the registry entry rather than
left for a later reader to discover.

---

## what it costs

Drawdown rises: **13.42R → 17.28R in sample, 11.88R → 16.86R out.** Inside the
owner's 29R budget, and out-of-sample still well below `atr_low`'s 28.9R. But it is
a real cost and it is the reason this is a candidate rather than a swap.

---

## a registration detail that is easy to get wrong

**The HTF swing length is not an engine parameter.** It is the registry's `swing`
FIELD, which selects a precomputed series the harness feeds into engine slot 2. So
this book needed a new series, not a params edit:

| file | what was added | why |
|---|---|---|
| `run_experiment.get_data` | `htf15` series + cache key | covers IS |
| `run_experiment.get_swings` | `htf15` key | the selector had to learn it |
| `exp_signal_metrics.load_era` | `htf15` series | covers OOS |
| `exp_equity_quality.load_scope` | `htf15` series | `exp_fastcheck`'s OOS path |
| `exp_fastcheck.measure` | explicit key lookup | it had a hardcoded `sw10 if … else sw20` that would have silently ignored anything else |

**The first version of this got it wrong twice and the gates caught both.**

The `exp_fastcheck` selector was `data["sw10"] if cfg["swing"] == "sw10" else
data["sw20"]` — so `htf15` silently resolved to `sw20`. The book came out
521t/+561.36 against a pinned 520/+567.57. That is a **silent wrong answer**, not a
crash: the lookup had a catch-all else, so an unknown swing key was quietly
treated as sw20 rather than raising.

And after fixing that, the OOS leg raised `KeyError('htf15')` while IS passed —
because the series had been added to the IS loaders only. `exp_equity_quality` has
a comment from 2026-10-02 recording this exact failure for `sw20` across 19 books.
**The lesson was already written down and I walked into it anyway**, which is why
the table above lists all four loaders.

---

## verdict

**`fsent_champ_long_htf15` is the first arm found that fixes the shipping book's
one negative half-year without costing return.** That is exactly what the owner's
rule asks for and nothing else in the registry does it.

It is registered as a candidate, not adopted, because:

1. both period-control cells are underpowered, so the size of the gain is not
   established even though its direction is
2. drawdown rises 13.42R → 17.28R in sample
3. the OOS window is 2021-22 and is **not** a holdout
4. it has not been sibling-tested against the sig family at the same HTF length

**`sig_multi` does not need this.** It is already at zero negative cells on
`min_bars=10` with the lowest out-of-sample drawdown in the repo at 7.6R, and every
attempt to widen its HTF leg cost net without improving the rule.

## what is left

The natural next question is whether the htf15 series helps `sig_multi` and the
other fsent books **as a shared HTF plane rather than a per-book setting**. If a
longer 1h leg is generally better for regime stability, that is a repo-wide
finding rather than a candidate. That has not been run and nothing here claims it.