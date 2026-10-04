# BOOK CATEGORIES — position first, then family

**Where this belongs.** Not in `pipeline/`. `pipeline/` is the procedure for
running a *new* experiment. This page is a map of the books that already exist,
so that "which one do we ship" can be asked against a structure rather than
against 220 registry rows.

**The first question about any book is not "which knobs does it have", it is
"which plane is it on".** Everything else nests inside that.

## The primary axis is POSITION

The owner's word for this was "single": **one position at a time**. That is the
axis that decides what a book is for.

| book type | positions | `max_positions` | books |
|---|---|---:|---:|
| **SIGNAL** | exactly one | 1 | **4** |
| **MULTI** | several at once | 0 | 216 |

> **These are two different books, not two settings of one book.** A multi book
> stays multi forever and is never converted into a signal book. A signal book
> is built for one position and carries its own filters, its own research and its
> own theory.

**The deployment plan follows that split.** Ship a signal book first, because an
account without capital for concurrent losers cannot run a multi book. Raise
capital from it, and only then deploy the multi books, which were always going to
be multi.

### The second axis is architecture, not position

`exp_mltf` selects whether the 15m cascade runs inside each HTF bias window or
only the 1h book trades. That is a separate question from how many positions a
book holds.

| architecture | `exp_mltf` | books |
|---|---|---:|
| cascade | True | 160 |
| 1h only | absent | 60 |

The two axes are independent, and the cross-tab is:

| | SIGNAL (1 position) | MULTI (unlimited) |
|---|---:|---:|
| **cascade** | **0** | 160 |
| **1h only** | 3 | 57 |

All four signal books are 1h-only, which is what makes them buildable today: the
position gate bites on the 1h-only architecture and is inert on a cascade book
(measured: 0/1/2/3 give byte-identical books at peak concurrency 6). That is a
property of the engine, not a finding about cascade books — and it does not
need fixing, because cascade books are going to stay multi anyway.

### The signal books already exist and work

They are not a plan, they are measured and pinned:

| book | IS | OOS |
|---|---|---|
| `fsent_sig_sw10_short` | 369 / +174.30 / DD 16.62 | 239 / +100.94 / DD 11.82 |
| `fsent_sig_sw10_long` | 355 / +116.40 / DD 21.07 | 230 / +80.50 / DD 13.53 |
| `fsent_sig_sw20_short` | 343 / +146.90 / DD 32.46 | 203 / +95.00 / DD 10.23 |
| `fsent_single_sw20_short_wr` | 515 / +492.60 / DD 14.15 | 283 / +179.80 / DD 8.48 |

All of them hold exactly one position at a time. What is still open is *which*
one to ship, and what filters to build on top of it — that is the next question,
not the existence of the book type.

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