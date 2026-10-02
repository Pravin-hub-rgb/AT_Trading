# P94 — THE OUTLIVE COHORT PASSES EVERY QUALITY GATE AND STILL FAILS M.
# The most interesting result of the round, and it is not a yes.

> Run 2026-09-29. Harness `exp_outlive_strategy.py`. **NOT ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> **The owner's question — "can this be a new strategy?" — gets the answer:
> the cohort is the best thing found anywhere in this round, and it is still
> not adoptable, and the reason is size.**

## The question

P93 found that trades outliving their parent 1h window average **+4.4 to
+5.1 R** against a book average of **+0.65 IS / +0.25 OOS**, with inside-window
trades negative in 4 of 4 cells and a block permutation at p ≈ 1.0.

**P93 measured that cohort INSIDE the full book.** Whether a book of *only*
that cohort beats the champion was never measured, and those are different
objects — the removed trades were occupying the slot and the cooldown.

## Result — 4 of 4 cells pass every quality gate

| lane / era | champion | **outlive-only** | R/t | PF | period split | **b (period-adjusted)** |
|---|---|---|---|---|---|---|
| champion **IS** | 500t +325.8R | **103t +506.2R** | +4.915 | 19.78 | **8-0** | **+5.0943** |
| champion **OOS** | 279t +70.1R | **43t +188.7R** | +4.389 | 24.02 | **4-0** | **+4.9043** |
| utcsat **IS** | 454t +359.0R | **100t +509.8R** | +5.098 | 22.85 | **8-0** | **+5.2470** |
| utcsat **OOS** | 253t +60.2R | **34t +150.9R** | +4.439 | 23.53 | **4-0** | **+4.9563** |

**Every cell:**
- beats the champion on net,
- **wins every half-year it shares — 8-0, 4-0, 8-0, 4-0, twenty-four of twenty-four**,
- **and shows b of +4.90 to +5.25 after a half-year fixed effect.**

**For comparison: the best candidate this round was P69/P87's ATR ceiling at
b = +0.82 to +1.30, with one cell failing. This is four to six times that,
in all four cells, with a perfect partition.**

## And it still fails, on magnitude alone

| lane / era | dNet vs champion | **as a fraction of M** |
|---|---|---|
| champion IS | +180.5R | **0.93×** |
| champion OOS | +118.6R | **0.61×** |
| utcsat IS | +150.9R | **0.78×** |
| utcsat OOS | +90.7R | **0.47×** |

**Not one cell clears M = 193.4R. The best reaches 93% of it.**

## Why the power trap matters more than usual here

The pre-registration named it: **a 34 to 103 trade book may be unable to
clear M on arithmetic alone.** And the arithmetic is stark —

**The outlive cohort is 13–22% of the trades and 142–269% of the R.** In
OOS it is 34 trades carrying 250.7% of a +60.2R book. **A book that small
cannot produce a 193.4R swing unless its per-trade edge is far larger than
+4.9R, and +4.9R is already seven to twenty times the champion's own.**

**So the honest reading is: the constraint is TRADE COUNT, not edge quality.
To reach M this cohort would need roughly 2–4× more of itself, and the
window structure does not obviously offer more.**

## What this is, and what it is not

**It is not a new strategy to adopt.** Four gates, one failure, and the
failure is the one that cannot be argued away.

**It is the strongest STRUCTURE found in the entire round**, and it is
worth stating plainly because nothing else came close.

*Qualification added 2026-10-01:* "structure" here means the outlive cohort passes
every quality gate on `r_multiple`. It does **not** mean there is an entry-time
signal that identifies the cohort before the fact. `BARS_TO_WEND_P115.md` showed
the only proposed identifying feature was the label itself. A reader who lands
here and skips P95 should read this as a quality-gate finding, not a filter.

| | champion | outlive cohort |
|---|---|---|
| trades | 500 | **103** (20.6%) |
| net | +325.8R | **+506.2R** |
| R/trade | +0.652 | **+4.915** |
| PF | 2.38 | **19.78** |
| period split | — | **8-0, and 4-0 OOS** |
| b after period control | — | **+5.09** |

**Five times the net on a fifth of the trades, with a 19.78 profit factor,
winning every single half-year.**

**What it is not is obtainable.** P93 already showed the exit rule on this
cohort fails — and for a reason this run makes precise: **the cohort is not
a filter you can switch on, it is the book the champion already runs,
described.** Turning it into a strategy means holding no position whenever
its window closes, and P93 measured that the trades which *would* have been
cut are the ones making the money.

## The one thing this suggests, named but not proposed

**If 20% of trades are 7–20× better than the rest, the question is not how
to filter — it is why the champion takes the other 80%.**

That is a different experiment, it touches the slot and cooldown policy
rather than an entry rule, and it is **not** proposed here. But it is the
first time in this round that a finding points at *more* trades rather
than fewer, and every previous finding pointed the other way.

## Stated limitations

- **Both lanes are the same data.** Four clean cells across two correlated
  lanes is a pattern, not independence.
- **The cohort is selected on `exit_ts > window_end`, which is only known
  after the trade ran.** **As a description it is clean; as a rule it is
  circular** — a live system cannot know in advance which trades will
  outlive their window. **This is the deepest objection to the whole line
  and it is not dismissed here.** It is why nothing is adopted even though
  every measurable gate passed except magnitude.
- **The window intervals come from the engine's own output**, matched by
  timestamp with a linear scan; a boundary entry could be attributed to
  either neighbour.
- **The OOS cohort is 34–43 trades**, thin enough that its R/trade estimate
  is unstable even though its partition result is unanimous.
- **The partition comparison is between the champion's half-year mean and
  the outlive half-year mean within it** — a ratio of means over 8 or 4
  cells, not a per-cell test.

## Status

**NOT ADOPTED.** Fails M in 4 of 4 cells, and the selection is circular as a
rule even where it passes.

**Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.**

**Recorded as the round's strongest structure and its clearest near-miss.**
