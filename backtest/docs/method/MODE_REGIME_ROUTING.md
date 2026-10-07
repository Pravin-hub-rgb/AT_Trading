# Regime routing: what `chop` is buying, and why `atr_high` stays

Date: 2026-10-07. Engine post-C17. Harnesses: `exp_mode_regime.py`,
`exp_mode_decide.py`, `exp_mode_autopsy.py`. Book: `fsent_champ_long`.

## The question

`fsent_champ_long` runs `mode="atr_high"`. It takes HTF **decisive** windows when
15m ATR% clears a threshold and **flip** windows below it. It never reads
`chop_thresh`. The knob sits in the config carrying `58.0`, and
`exp_knob_binds.py` correctly reports it INERT — for this book.

INERT is not an answer to "what is it worth". It only says this book does not
use it. Two things follow, and this file is about both:

1. What is the indicator measuring, and does the book already route on it?
2. If routing on it is better, would we know? Would we be fooling ourselves?

## What the two indicators are

| | reads | scale | says about direction? |
|---|---|---|---|
| `chop_thresh` | CHOP index, 1h, lb=14: `100*log10(sum TR / range) / log10(14)` | ~0-100 | **Yes.** High = travelled efficiently (trend). Low = oscillated in a range. |
| `atr_high_thresh` | ATR% of price, 15m, 14 bars | % of price | **No.** Says how big the bars are. |

`chop` is a Choppiness Efficiency Ratio. `atr_pct` is bar size. They are not
proxies for each other, and the intuition that they might be is wrong in an
instructive way: a violent two-way market has **high** `atr_pct` and **low**
`chop`, while a slow grind up has **low** `atr_pct` and **high** `chop`. The two
move in opposite directions on exactly the bars that matter.

Both are sampled causally. `chop` comes from the last 1h candle **closed** by
`ts+900` (C14), never the running 1h candle.

## Part 1 — how often do they disagree

`exp_mode_regime.py`, all 15m bars, thresholds as booked (`atr_high_thresh=0.65`,
`chop_thresh=58.0`):

| | IS bars | OOS bars |
|---|---:|---:|
| chop_low / atr_low | 51.4% | 61.9% |
| chop_low / atr_HIGH | 6.1% | 20.1% |
| chop_HIGH / atr_low | 18.5% | 15.4% |
| chop_HIGH / atr_HIGH | 0.4% | 2.6% |
| **agree** | **75.4%** | **64.5%** |

They disagree on a quarter to a third of bars, and almost all of it is the
`chop_low / atr_HIGH` cell — big bars, inefficient travel. That is a real
population, not a rounding error, so the routing choice is a real choice.

Note also how rare the "both high" cell is: 0.4% IS, 2.6% OOS. Volatile *and*
efficient is uncommon, which is why it barely appears below.

## Part 2 — what the book earns in each cell

Same book, trades bucketed by both readings. This is the useful half, because
the book, entry logic, swing and risk knobs are all held fixed.

**IS** (528 trades, +533.4R)

| cell | n | net R | share | win % | mean R |
|---|---:|---:|---:|---:|---:|
| chop_low / atr_low | 425 | +387.9 | 72.7% | 39.8% | +0.91 |
| **chop_HIGH / atr_low** | **75** | **+132.0** | **24.7%** | **45.3%** | **+1.76** |
| chop_low / atr_HIGH | 24 | +12.6 | 2.4% | 29.2% | +0.52 |
| chop_HIGH / atr_HIGH | 4 | +0.9 | 0.2% | 25.0% | +0.23 |

**OOS** (311 trades, +239.6R)

| cell | n | net R | share | win % | mean R |
|---|---:|---:|---:|---:|---:|
| **chop_HIGH / atr_low** | **42** | **+109.5** | **45.7%** | **42.9%** | **+2.61** |
| chop_low / atr_low | 195 | +97.4 | 40.6% | 36.4% | +0.50 |
| chop_low / atr_HIGH | 70 | +30.8 | 12.8% | 34.3% | +0.44 |
| chop_HIGH / atr_HIGH | 4 | +2.0 | 0.8% | 50.0% | +0.49 |

**This is the finding.** The cell where the indicators disagree, in the
direction `chop` says efficient and `atr` says quiet, is the book's best cell in
**both** eras — +1.76R mean IS, +2.61R mean OOS, against +0.50R for the
baseline cell. And the book routes it to **flip**, because that branch is chosen
on `atr_high` alone and both disagreement cells read as "low vol" to it.

So the router currently treats its best cell and its worst disagreement cell
identically. That is a routing gap, not a missing feature.

## Part 3 — does routing on chop actually fix it? No, and the reason matters

> **Continued in `CELL_GATE_NOT_A_BOOK.md`.** The per-cell finding below turned
> out to be real — it survives its outlier bar, unlike every routing arm built
> on it — but trading the cell *alone* yields 58 OOS trades and worse IS drawdown
> than the whole book. Read that file before acting on this one.

`exp_mode_decide.py`, only `mode` moving. Shipping is `atr_high`.

| arm | IS | OOS | verdict |
|---|---|---|---|
| `atr_high` (shipping) | 528 / +533.4 / dd 13.4 | 311 / +239.6 / dd 11.9 | — |
| `decisive_vs_flip_chop` ch=30, 40 | 664 / +657.7 / **31.1** | 359 / +190.6 / 16.6 | era-split |
| `decisive_vs_flip_chop` ch=50 | 577 / +574.6 / **28.2** | 325 / +258.2 / 11.6 | ahead both |
| `decisive_vs_flip_chop` ch=55 | 526 / +575.6 / 13.4 | 297 / +248.5 / 11.9 | ahead both |
| `decisive_vs_flip_chop` ch=58, 62, 70 | 528 / +533.4 / 13.4 | 294 / +244.4 / 11.9 | +0.0 / +4.8 |
| `chop_or_atr_low` | 640 / +645.0 / 28.9 | 313 / +182.9 / 14.6 | era-split |
| `chop_and_atr_low` | 528 / +533.4 / 13.4 | 294 / +244.4 / 11.9 | +0.0 / +4.8 |
| `soft_chop` | 525 / +529.4 / 13.4 | 297 / +248.5 / 11.9 | worse |

Six arms are "not worse in either era". Two of them are ahead on net R. Both are
outliers. `exp_mode_autopsy.py` says why.

### ch=55 buys 42R by deleting two trades

IS: **-2 trades, +42.2R**. That is 21R per trade removed. No regime indicator is
worth 21R per trade — a threshold that excludes two specific known trades is a
fit to those trades.

### ch=50 buys 41R with one trade, and doubles the drawdown

IS: 121 trades removed (+90.3R), 170 added (+134.2R). One added trade,
`1787031000` at **+46.24R** over six days, is 34% of everything added. Drop it
and the arm is **-2.4R against shipping** — the advantage vanishes.

It also takes IS max DD from 13.4R to **28.2R**. A book that buys 41R by risking
28R of drawdown instead of 13R is a different risk profile, and the halt
governance note already established that drawdown is not spent casually.

### And the OOS sides lean on one trade each

ch=50 OOS: top added trade `1658922300` at +16.1R, of +33.2R added.
ch=55 OOS: top added trade `1653868800` at +7.6R, of +12.9R added.

**`1653868800` is the same trade that made `persist=5` look free** in
`_persist_sweep.md`. It is worth being blunt about what that means: two
independent-looking "improvements" in this repo are both standing on one
specific 2.2-day long. A trade that shows up as the load-bearing element of two
separate proposals is a trade that will keep showing up, and every future knob
sweep will rediscover it and read it as signal.

## Verdict

**`mode="atr_high"` stays. `chop_thresh=58.0` stays in the config, unused.**

Not because routing on `chop` is wrong — the per-cell tables in Part 2 make it
look genuinely interesting, and the disagreement cells are real. Because every
configuration that actually converts that into R turns out to rest on one or two
trades, and two of them were already found to rest on the *same* trade.

Three things that would have to be true before revisiting:

1. **A win that survives dropping its largest trade.** The harness can enforce
   this. It does not currently gate on it, and every candidate here would fail.
2. **Drawdown held, not just net.** ch=50 doubles IS DD. The halt decision in
   `EQUITY_LENS_EXT_AND_NOHALT.md` is about exactly this quantity.
3. **Something other than a threshold to tune.** `chop_thresh` has a flat region
   from 58 to 70 and a cliff at 30-40. There is no interior optimum to find.

The cell-level finding is real and worth keeping: **the book does its best work
in `chop_HIGH / atr_low`, and routes that to flip.** If a routing rule is ever
built, that cell is where to aim it — but it has to be built to survive an
outlier check, because three separate sweeps in this repo have now been
misled by two trades.

## On deleting `chop_thresh` from this book's config

Still no, and `KNOB_BINDS_AUDIT.md` has the measurement. 13 registry books
inherit `BP`'s `mode="b2_vs_flip_chop"` and read this knob for real, carrying
+17R to +164R on the four sampled. One is named `lb30_chop55_persist2`. This book
does not use it, which says nothing about the thirteen that do.