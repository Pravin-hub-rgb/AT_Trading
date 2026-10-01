# THE +0.498 ACF IS A TAIL ARTEFACT — the ranking decided it

Date: 2026-09-28. `exp_acf_tail_check.py` → `_acf_tail_check.json` 45.2s.
Controls exact both eras.

## The question

`exp_quant_autopsy.py` reported OOS trade-R ACF(lag1) = **+0.4981** against
a ±0.1173 band — four times outside — as "the largest unexplained structure
found in this session". Then the halt hypothesis was refuted
(`HALT_FIRING_RATE.md`): the halt fires at the same rate in both eras
(10.20 vs 10.39 per 100 trades), so it cannot explain the split.

The remaining candidate was the embarrassing one: **the book is
tail-concentrated.** ACF on R *values* can be pushed to +0.5 by a few large
R in adjacent trades, with no clustering of wins or losses at all.

## The decisive test: same lag-1 statistic, three ways

| era | raw R | win/loss (0-1) | ranks of R |
|---|---|---|---|
| IS (500t, band ±0.0877) | +0.0651 inside | +0.0753 inside | +0.1191 **outside** |
| **OOS (279t, band ±0.1173)** | **+0.4981 outside** | **+0.1138 inside** | +0.2357 **outside** |

**`win/loss` collapses the OOS effect from +0.498 to +0.114 — inside the
band.** That statistic is immune to any single R value, so the +0.498 was
carried entirely by *magnitude*, not by direction.

**Ranks confirm it independently: +0.2357.** Ranks are invariant to any
monotone transform of R, so they can only differ from `raw` if magnitude
is doing the work. It is. The raw figure is inflated by roughly 4× relative
to the order-only view.

## And the monsters are visibly adjacent

OOS trades ≥ +5R: 17 of them, with **8 adjacent pairs**. Their positions:

    20, 29, 45, 140, 178, 179, 180, 181, 182, 190, 205, 208

**Positions 178-182 are five monsters in a row** (R = 13.6, 6.3, 6.4, 6.7,
6.2). IS shows the same shape at 82-84 and 90-93.

So the clustering is real — **but it is clustering of *big wins*, not of
losses.** A run of five +6R trades next to each other will produce a large
positive lag-1 correlation on R, and says nothing about whether the next
trade is more likely to win.

## What this does to the finding

The claim in `QUANT_AUTOPSY.md` — that "the book's independence assumption
is era-dependent" and that OOS is "strongly, significantly
autocorrelated" — **is withdrawn.** The correct statement is:

- The book's **win/loss sequence is close to independent in both eras**
  (+0.075 IS, +0.114 OOS, both inside band). That is the statistic that
  matters for a streak/pause rule, and it says the streak rule is not
  responding to exploitable structure.
- The **R-magnitude sequence clusters in both eras** (+0.119 IS, +0.236
  OOS on ranks) because a few monster runs sit next to each other. That is
  a property of the tail, not a signal.
- The original +0.498 was a magnitude artefact of a heavy-tailed
  distribution, which is exactly what `CLOSED_DO_NOT_REPEAT.md` line 1
  warns about: "Low win rate + tail concentration is a FEATURE."

## Consequence for the earlier work

This is the third hypothesis of the day to be refuted by its own test
(the halt firing rate, the script's CONFIRMED verdict, and now the tail
artefact). The pattern is worth stating plainly: **each time a striking
number appeared, the first job was to ask what mundane mechanism could
produce it, and each time there was one.** The discipline that caught them
was the same each time — a control, and a statistic chosen because it is
immune to the suspected artefact.

**Nothing changes in the strategy.** `max_consecutive_losses=3` keeps its
sweep-confirmed justification, and the correct reason for it is not
"exploiting clustering" — it is that skipping after 3 losses is worth
+17.3R IS against not doing it, which was measured directly.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
