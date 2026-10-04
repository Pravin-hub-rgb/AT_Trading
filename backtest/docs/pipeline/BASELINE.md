# BASELINE — what "no filters" actually means here

Every comparison in this repo is against something. That something has to be the
*pure* book, or the comparison is against an accident.

## The two book types

**Signal and multi are separate books, not two settings of one book.** A multi
book holds several positions at once and stays that way; it is never converted
into a signal book. A signal book is built to hold exactly one position
(`max_positions=1`) and carries its own filters, its own research and its own
theory. A **cascade** book (`exp_mltf`) is the architecture where the 15m
cascade runs inside each HTF window; the position gate does not bite there, which
is why every signal book today is 1h-only.

Numbers from the two book types have different denominators and are never
compared to each other.

**Everything else** is a knob on the same engine. So the baseline is: HTF
produces bias windows, LTF takes the trades, and *nothing else is added*.

## The base knobs are not optional

`experiment_registry.BP` is what every book inherits before its own `params`:

```
mode                   b2_vs_flip_chop
cooldown_bars          10
max_consecutive_losses 3
ext_stop_r             1.5
sl_buf_atr             0.01
htf_rr                 3.0
window_end             exit
chop_thresh            58.0
atr_high_thresh        0.65
atr_low_thresh         0.35
```

These ten are the engine's own behaviour, not filters. `mode` in particular is
not a knob at all — it decides how the chop and ATR bands pick between the flip
and b2 HTF interval sets, and the book does not work without it.

**A book that overrides all ten is a different book, not a filtered version of
the baseline.** Most books here override `mode`, `ext_stop_r` and `sl_buf_atr`.
That is why "the champion" is a family of four books differing in two knobs, and
why comparing a champion variant to "the baseline" is not a one-knob comparison.

## Stop source is not a knob either

`pivot_rule` selects where the initial stop goes. It has three values:

| value | meaning | status |
|---|---|---|
| `leg` | the running extreme up to and including the entry bar | **default, causal** |
| `leg_no_entry` | same, excluding the entry bar | **causal** |
| `origin` | the swing's declared start — only knowable once the leg completes | **look-ahead, research baseline only** |

Only two books in the registry still carry `origin`, kept alive deliberately so
the comparison reproduces. They are not shipping candidates and nothing should be
measured on them. `exp_origin_lookahead.py` enforces this and fails if a new book
appears with a forbidden source.

## Two baselines, not one

**A signal book cannot be compared against a multi-position book.** They are
different objects. This page defines both, because getting it wrong produces a
plausible-looking comparison that is off by a hundred R.

### The multi-position baseline

`champion_single_sw10` with zero filters: HTF plus LTF, one swing chain, no
`exp_` filters at all.

| | trades | net | DD | WR | peak concurrent |
|---|---:|---:|---:|---:|---:|
| IS | 503 | +170.91 | 50.5 | 28.0% | **6** |
| OOS | 295 | +78.57 | 38.1 | 27.8% | 5 |

Note the peak: **six positions at once.** The word "single" in that book name
means *one swing chain*, not one position. That distinction is the single easiest
thing to get wrong in this repo.

### The signal baseline — the one a signal book is measured against

The same book with `max_positions=1`. One position, peak concurrency 1:

| | trades | net | DD | WR | peak concurrent |
|---|---:|---:|---:|---:|---:|
| IS | 396 | **+37.80** | 51.8 | 24.0% | 1 |
| OOS | 231 | **−16.26** | 41.7 | 23.4% | 1 |

> **Out of sample this is a losing book.** A signal book does not exist as a
> business until something is added to it. Directional FS entry is not an
> improvement on a working signal book; it is the reason a signal book works at
> all.

That is why the "pure baseline" question has two answers and picking the wrong
one flatters the result: `fsent_sig_wk_pause_short` measures IS +206.9 /
OOS +128.8, which is +50R against the multi-position baseline and **+145R against
the one that matters.**

## What a baseline is not

- **Not the best book.** It is the floor. Every filter is measured against it.
- **Not a book with the filters removed.** Most books were *built* by adding
  knobs; there is no book in the registry that is the champion minus its
  filters, and constructing one is how curve fitting starts.
- **Not the champion.** `champion_*` is a family of books that each already
  carry a specific stop source, `ext_stop_r`, `sl_buf_atr` and a window
  definition. "Pure" means the base above, not "the champion without its
  filters".

## Comparing honestly

When a knob is measured, the control is the **same plane with the same base
knobs**, changing only the knob under test. Not the top of the board. A knob
that beats the top of the board by a wide margin is either a real effect or a
look-ahead, and the difference is decided by the causality question in
[`README.md`](README.md) section 4, not by the size of the gap.