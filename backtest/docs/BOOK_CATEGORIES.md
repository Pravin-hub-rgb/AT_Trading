# BOOK CATEGORIES — position first, then family

**Where this belongs.** Not in `pipeline/`. `pipeline/` is the procedure for
running a *new* experiment. This page is a map of the books that already exist,
so that "which one do we ship" can be asked against a structure rather than
against 220 registry rows.

**The first question about any book is not "which knobs does it have", it is
"which plane is it on".** Everything else nests inside that.

## The primary axis is POSITION

The owner's word for this was "single": **one position at a time**. That is
`max_positions`, and it is the axis that decides whether a book can be deployed
at all.

| position gate | `max_positions` | books |
|---|---|---:|
| **SIGNAL** — exactly one position | 1 | **4** |
| **MULTI** — unlimited concurrent | 0 | 216 |

**A book that stacks positions cannot be deployed on an account that cannot
carry concurrent losers.** That is a capital constraint, not a preference, and
it is the question the live decision turns on.

### There is a second axis, and it is not the same thing

`exp_mltf` selects the architecture: whether the 15m cascade runs inside each
HTF bias window, or only the 1h book trades.

| architecture | `exp_mltf` | books |
|---|---|---:|
| cascade | True | 160 |
| 1h only | absent | 60 |

The two are independent, and the cross-tab is the important part:

| | SIGNAL (1 position) | MULTI (unlimited) |
|---|---:|---:|
| **cascade** | **0** | 160 |
| **1h only** | 3 | 57 |

> **No cascade book exists on the signal plane. Not one, out of 160.**

## And the gate does not work on cascade books

Measured on `champion_multi_sw10_leg`, sample:

| `max_positions` | trades | net R | peak concurrent |
|---:|---:|---:|---:|
| 0 | 499 | +239.12 | **6** |
| 1 | 499 | +239.12 | **6** |
| 2 | 499 | +239.12 | **6** |
| 3 | 499 | +239.12 | **6** |

**The position gate is inert on cascade books.** It only bites on the 1h-only
architecture, where the same sweep gives 396 trades at peak concurrency 1. It is
also all-or-nothing — 1, 2 and 3 produce identical books, so there is no partial
concurrency control.

**So the plan of "signal first, multi later" is blocked at the engine, not at
the research.** Building a signal book today means building it on the 1h-only
architecture. Making a cascade book signal-capable needs the gate wired into the
cascade path, which is an engine change.

Whether a cascade book's edge *is* the stacking is exactly what that change
would answer. Right now the question cannot be asked.

## Inside a plane, the filter families

From [`FAMILIES.md`](FAMILIES.md). Counts are books carrying at least one knob
from that family.

| family | SINGLE | MULTI |
|---|---:|---:|
| Risk | 48 | 157 |
| Time | 45 | 49 |
| Regime | 13 | 160 |
| StopSource | — | 105 |
| PriceAction | 4 | 27 |
| Trigger | 6 | 19 |
| Exit | 4 | 18 |
| Sizing | 10 | 11 |
| **LOOKAHEAD (closed)** | 4 | 6 |

### What that table says

**Risk and Time carry the SINGLE plane.** Nearly every single book has a risk
knob and nearly every single book has a time knob. That is what a book looks
like when it has been filtered until it is a different machine — and it is why
"which single do we ship" is currently unanswerable. See
[`BASELINE.md`](BASELINE.md) for what a pure baseline is.

**MULTI carries Regime on all 160.** `exp_persist` and the chop/ATR thresholds
are not filters on a multi book, they are how the cascade picks between the
flip and b2 interval sets. Uniformity there is structural, not fitted.

**StopSource appears only in MULTI (105).** `pivot_rule` is a stop source, not
a knob, and it is what separates the research-only `origin` books from
everything causal. See `CLOSED_DO_NOT_REPEAT.md`.

**PriceAction is small and now closed.** Four single books and 27 multi books
carry it, and the family produced every look-ahead leak in this repo. It is the
first family to check and the first to delete.

## How to ask the question properly

| question | answer with |
|---|---|
| which books can I actually deploy? | plane × gate — and today that is 3 single signal books |
| is this book over-filtered? | count its families; more than three is a smell |
| is this knob a filter or structural? | its family — Regime and StopSource are structural |
| did I re-add a knob a book already has? | the family, not the knob name |

`experiment_registry.py` can be queried with `shortlisted()`; a plane/family
view is not wired in yet and should be, so that "which of my books are
deployable" is one call rather than an argument with the registry file.