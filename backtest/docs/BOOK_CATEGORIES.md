# BOOK CATEGORIES — position first, then family

**Where this belongs.** Not in `pipeline/`. `pipeline/` is the procedure for
running a *new* experiment. This page is a map of the books that already exist,
so that "which one do we ship" can be asked against a structure rather than
against 220 registry rows.

**The first question about any book is not "which knobs does it have", it is
"which plane is it on".** Everything else nests inside that.

## The two axes, and they are independent

A lot of confusion in this repo came from using the word "single" for two
different things. They are separate axes and both are real.

### Axis 1 — PLANE (architecture). Set by `exp_mltf`.

| plane | what runs | books |
|---|---|---:|
| **SINGLE** | the 1h book only. One swing chain, one set of trades. | 60 |
| **MULTI** | the 1h book *plus* the 15m cascade inside each bias window. | 160 |

**A MULTI book is a different machine, not a filtered SINGLE book.** The bias
window stops being a filter and becomes a container: the 1h trade is not the
trade, it is the *permission*, and the 15m cascade supplies the trades. Numbers
from the two planes have different denominators and are never comparable.

### Axis 2 — POSITION GATE. Set by `max_positions`.

| gate | meaning | books |
|---|---|---:|
| `max_positions=1` | **signal plane** — exactly one position at a time | **4** |
| `max_positions=0` | unlimited concurrent positions | 216 |

### The cross-tab, which is the whole point

| | signal (1 position) | multi (unlimited) |
|---|---:|---:|
| **SINGLE** | 3 | 57 |
| **MULTI** | **0** | 160 |

> **There is no MULTI book on the signal plane. Not one.** Every multi-timeframe
> book in this repo can hold unlimited concurrent positions.

That is not an oversight, it is the thing to decide next. A multi book is a
stacking machine — its edge may *be* the stacking. If it is, it cannot be
deployed on an account that cannot carry concurrent losers, and a signal-plane
multi book is a different research question, not a configuration change.

`max_positions=1` on a MULTI book is not a one-flag experiment: serialising
throws trades away, so every knob that stacks well may stop working.

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