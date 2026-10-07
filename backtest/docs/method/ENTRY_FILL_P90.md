# P90 — THE LIVE BOT'S HEADLINE NUMBER IS BETTER ON LIVE FILLS, NOT


<!-- C17-NOTICE -->
> **C17 NOTICE (2026-10-07).** The figures in this document were measured before
> the C17 gate fix, which removed a lookahead from the HTF window gate and
> invalidated 214 of 215 registry pins. They are kept as the dated record they
> were, and they are **not** what the engine produces today - do not quote them
> as current. Current numbers: `python exp_pinverify.py` (re-derives every pin),
> `docs/method/C17_WINDOW_END_CAUSALITY.md` (what changed and why),
> `docs/multi/MULTI_RANKINGS.md` and `docs/signal/SIGNAL_RANKINGS.md`
> (regenerated from a post-C17 measurement).
------------------------------------------------------------------------------
# WORSE. And the falsifier fired, so the first result is retracted and the
# second is reported with its mechanism unproven.

> ## SUPERSEDED 2026-09-30 by [`method/P90_FILL_P109.md`](method/P90_FILL_P109.md). Read that instead.
>
> **Every result below about fill improvement is retracted.** P109 established that
> the P90 arm was anti-causal: it entered at the open of the signal candle itself,
> which is a price the bot had to trade through to reach the close. Re-run as the
> true next open, `open[i+1]`, **0 of 500 trades differ and the delta is +0.0R**,
> because on contiguous candles `close[i] == open[i+1]`. There is nothing between
> the two prices, so the "the book improves on live fills" claim below has nothing
> underneath it. The +174.8R and +174.8R-family figures in the corrected-result
> section are anti-causal artefacts and are retracted with the rest.
>
> **Also retracted, 2026-10-01: "500t/+325.8R as SHIPPED" is wrong.** That figure is
> the PRE-C16 origin book, and it is lookahead — the stop sits at a price only known
> after the swing completed. The books are:
>
> | book | pivot | IS | OOS | status |
> |---|---|---|---|---|
> | `champion_multi_sw10` | origin | 500t / +325.78R | 279t / +70.15R | pre-C16 baseline, LOOKAHEAD, not live-placeable |
> | `champion_multi_sw10_leg` | leg | 499t / +239.12R | 279t / +70.15R | causal, this is what the dropdown ships |
> | v18 live engine | leg | 352t / +146.55R | — | what `live_loop.py` actually runs |
>
> Nothing in this document was re-measured after C16. Do not quote any headline
> figure from it; take the numbers from the table above.
>
> Run 2026-09-29. Harness `exp_entry_fill.py`.
> **From `method/NEXT_ROUND_BRIEF.md`, Big Pickle's P90.** Nothing adopted.
> Champion as measured then: 500t/+325.8R IS, 279t/+70.1R OOS — the pre-C16 book.

## The concern, and it is confirmed in the shipped code

```
v7_timecap.py:65   entry = float(candles[i]["close"])
```

`i` is the index of the bar the signal fired **on**. The break mark carries
that bar's own close and the fill is that same close — **so the entry price
sits at the extreme of the very bar whose close revealed the breakout.**

**The asymmetry is worth naming, because it bounds how bad this could be.**
The exit side already fills honestly:

```
v7_timecap.py:167  fill = min(sl_cur_f, float(c["open"]))
v7_timecap.py:182  fill = max(sl_cur_f, float(c["open"]))
```

**Exits use the next bar's open. Only the entry uses the signal bar's
close.** So the book is not uniformly optimistic — it is optimistic in one
specific place, and that place is exactly the one a live system cannot copy.

## Attempt 1 was wrong, and its own falsifier caught it

The first run reported **+6038.8R** in IS. That is not a large result, it is
an arithmetic explosion, and the harness's mechanism check said so before
the number could be believed:

```
mechanism: corr(dR per trade, ATR% of that bar) = -0.044   -> NO CORRELATION
```

The bug: the re-fill **recomputed each trade's R from scratch** —
`(exit - new_entry) / new_risk` — when the engine's `r_multiple` already
contains the original ratio. The two diverge violently as the new risk
shrinks, so the sum inflates without bound.

The correction is a **delta**:

```
new_R = old_R + (new_gain - old_gain) / new_risk
```

with exit and stop held. This leaves the control arm exactly equal to the
shipped number, which is the invariant now asserted.

## The corrected result — the book IMPROVES on live fills

> **RETRACTED 2026-09-30, see the banner at the top.** This whole table is void.
> The arm entered at `open[i]`, the open of the signal candle itself, which is
> ahead of the `close[i]` the engine actually fills at — anti-causal. Re-run as the
> true next open `open[i+1]`: **0 of 500 trades differ, delta +0.0R.** The dNet
> column below, +174.8R and +144.0R, does not exist.

| arm | lane / era | shipped | next 15m open | next open + 5bp | dNet (b) |
|---|---|---|---|---|---|
| (b) | **champ IS** | +325.8R | **+500.6R** PF 5.39 | +480.6R | **+174.8R** |
| (b) | **champ OOS** | +70.1R | **+214.1R** PF 3.63 | +188.0R | **+144.0R** |
| (b) | utcsat IS | +359.0R | +516.2R PF 5.83 | +501.8R | +157.3R |

**Per side, champion lane:**

| | longs | shorts |
|---|---|---|
| IS shipped | 273t +272.6R | 227t +53.2R |
| IS re-filled | **+393.4R** | **+107.1R** |
| OOS shipped | 162t **+1.8R** | 117t +68.4R |
| OOS re-filled | **+82.6R** | +131.5R |

**Filling one bar later makes the book better in every cell, every side,
and both eras.** R/trade goes 0.652 → 1.001 in IS and 0.251 → 0.768 in OOS.

**The concern that motivated this audit is answered, and in the direction
that matters for shipping: +325.8R is not a fill artefact. If anything the
shipped figure is the pessimistic one.**

> **RETRACTED — the sentence above is void.** It rests on the void dNet table. The
> correct answer is P90_FILL_P109: entry at the true next open `open[i+1]` differs
> on **0 of 500 trades**, so the fill question is settled at **+0.0R** and this
> document's conclusion was an artefact of entering at `open[i]`.
>
> Separately, "+325.8R" is the pre-C16 origin book, not the shipped figure.

## But the falsifier still fires, so the mechanism is NOT established

```
champ IS    corr(dR, ATR%) = -0.054
champ OOS   corr(dR, ATR%) = -0.079
utcsat IS   corr(dR, ATR%) = -0.053
```

**The prediction was that the re-fill cost scales with the signal bar's
range. It does not — the correlation is essentially zero in all four cells.**

**Two readings, and this run cannot separate them:**

1. **The effect is not a cost at all.** If the next open is systematically
   *better* than the signal close, then the shipped fill was the pessimistic
   one and there is no drag to explain. Under this reading the +174.8R is
   real and the zero correlation is not a failure of the mechanism — the
   mechanism premise was wrong.
2. **The gain comes from somewhere else entirely** — position sizing
   shifting, or the stop-to-entry distance changing in a way that flatters
   the R-multiple without any real P&L improvement.

**The R-multiple is a ratio and this changes its denominator.** A later
entry can shrink `risk` while barely moving `gain`, and the R rises without
the trade being any more profitable. **That is a property of R, not of the
strategy, and it is exactly the kind of number P60 and P83 were burned by.**

**Which test would settle it, and it is not this one:** recompute in
**absolute R per unit notional** — total return in price terms summed across
trades — and compare that, not the R-multiple. If the absolute total also
rises, the fill genuinely is better. If only the R-multiple rises, the
denominator moved.

## What this does and does not license

**It does not license raising any expectation.** The number to ship is
still the one a live system can achieve, and that number has not been
established — it is either +325.8R or +500.6R and this run cannot say which.

**It does retire the fear.** "Is +325.8R partly a fill artefact?" was a
real question about shipping a bot, and the answer is **no in the direction
that matters** — a live trader filling at the next open does not lose the
edge.

## Stated limitations

- **Both lanes are the same data.**
- **The falsifier fired.** A run whose stated mechanism shows no correlation
  is reporting a number whose provenance is not established, and that is
  said here rather than buried under the size of the gain.
- **R-multiple denominators move** when the entry moves. See above — this is
  the single most important caveat in the document and it is unresolvable
  without the absolute-return test.
- **The 5bp slip arm uses the repo's existing entry-slip assumption**, not a
  fresh one.

## Status

**Nothing adopted, and nothing needs to change in production.** The shipped
figure is not overstated.

> **RETRACTED — see banner.** The claim above is void; the fill arm was
> anti-causal and P90_FILL_P109 settles it at +0.0R. "Nothing needs to change"
> happens to still hold, but not for the reason given here.

Champion as measured in this document: 500t/+325.8R IS, 279t/+70.1R OOS — the
**pre-C16 origin book**, which is lookahead. The shipping book is
`champion_multi_sw10_leg` at 499t/+239.12R IS / 279t/+70.15R OOS, and the live v18
engine runs 352t/+146.55R.

**Follow-up, one run: recompute both arms in absolute R per unit notional.
That is what would turn a suggestive +174.8R into a shippable expectancy.**
