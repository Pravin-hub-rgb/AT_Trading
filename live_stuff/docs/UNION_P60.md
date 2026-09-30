# P60: the union fails in four cells out of four, and the bound was wrong

> Run 2026-09-29. Harness `exp_union.py`. Nothing adopted.
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> `cand_4h1h` survives as a candidate; the **union route is closed**.

## What was tried

P59 showed the two books barely overlap — only 4–7% of trades are common,
and neither book's exclusive trades are bad. That made a union the obvious
next step: both books are profitable in both eras, so why not take both?

**Rules were fixed before running**, not chosen by looking at the output:
one position at a time; **SKIP** on conflict rather than GRAY; champion
first on an exact timestamp tie; exits and `r_multiple` unchanged.

## Result — all four cells lose

All figures **net of costs**, on the same basis as the pins.

| arm | n | net | R/trade | PF | DD | WR |
|---|---|---|---|---|---|---|
| champion 1h+15m **IS** | 500 | **+325.8R** | +0.652 | 2.38 | 17.8 | 30.0% |
| cand_4h1h **IS** | 286 | +212.8R | +0.744 | 2.59 | 26.0 | 35.3% |
| **UNION IS** | 427 | **+228.8R** | +0.536 | 2.18 | 19.2 | 30.2% |
| champion 1h+15m **OOS** | 279 | **+70.1R** | +0.251 | 1.59 | 37.3 | 28.0% |
| cand_4h1h **OOS** | 189 | +98.0R | +0.519 | 2.02 | 26.4 | 32.8% |
| **UNION OOS** | 262 | **+6.2R** | +0.024 | **1.21** | 20.1 | 25.2% |

| cell | union vs champion | signals skipped |
|---|---|---|
| champion IS | **−97.0R** | 359 of 786 (46%) |
| champion OOS | **−64.0R** | 206 of 468 (44%) |
| utcsat IS | **−163.2R** | 314 of 711 (44%) |
| utcsat OOS | **−31.5R** | 182 of 424 (43%) |

**Four out of four. The union is worse than the champion in every lane and
every era, and it is worth roughly nothing in OOS at PF 1.21.**

## The bound I published was wrong, by a lot

P59 recorded a deduplicated sum of both books as **+664.0R IS / +225.8R
OOS**, explicitly labelled a bound and not a measurement. The measurement
came back at **+228.8R IS / +6.2R OOS**.

**The bound was 2.9x too high in IS and 36x too high in OOS.**

The reason is the whole point: **the single-slot constraint is not a tax on
a union, it is the thing that destroys it.** 43–46% of all signals get
skipped, and a skipped signal is not merely lost profit — it is a book whose
internal gating was never shared with the other one. The bound assumed every
distinct bet could be taken. Almost half cannot.

## Two things this run caught about itself

**1. A gross-vs-net error, caught before anything was reported.** The first
version summed bare `r_multiple` and so compared a **gross** union against a
**net** champion: the union appeared to be +445.2R against +325.8R. That
119.4R gap was nothing but fees, slippage and funding. Every number above is
now on the pins' own basis, via the same `_trade_costs` and `fund` that
`net_r` uses. The error made the union look 216R better than it is.

**2. The union is not a valid simulation of a production union**, and this
was stated in the harness before it ran. Both books were simulated with
their own cooldown and their own `busy_until`, so a suppressed champion
signal might have changed the champion's own later gating. That caveat
stands. What matters is that **the optimistic version — the one that
overstates the union — still loses in all four cells.** A more faithful
simulation could differ, but the direction of the evidence does not favour
it: the only thing the true simulation adds is *more* suppression, and
suppression is what is already killing this book.

## The union reproduces the P57 1D trap exactly

Look at the OOS column: the union's drawdown is **20.1R against the
champion's 37.3R** — a 46% improvement — and its return is **+6.2R
against +70.1R**, down 91%.

**Better risk profile, destroyed return.** That is the same signature as the
1D architecture in P57, which had the best win rate and the lowest drawdown
in IS and was negative in OOS. It is now the fourth appearance of the
IS-fitted pattern after the P56 window expiry, the P58 granularity finding
and the P59 layer-agreement signal. **A candidate that improves the
measured risk profile while destroying the return is fitted to the era it
was measured in** — and this one is fitted to nothing at all, which is what
makes it so clean an example.

## What survives

**`cand_4h1h` remains a registered candidate**, on its own merits: better
OOS quality on every measure (R/trade 0.519 vs 0.251, PF 2.02 vs 1.59, WR
32.8% vs 28.0%), still failing M = 193.4R, still one era.

**The union route is closed.** Not because merging is hard, but because the
measurement says the two books cannot share a slot profitably: they are
individually good and jointly worse, which is the most useful kind of
negative result there is — it is decisive rather than inconclusive.

## Stated limitations

- **The merge is chronological, not a shared-state re-simulation.** Stated
  before the run. It is the cheapest honest test, and it loses.
- **R3 (champion first on an exact tie) is arbitrary.** Fixed in advance
  and not re-picked. If it mattered, the honest follow-up would be to
  report how many exact ties there even were.
- **Costs are charged per taken trade using the same schedule as the
  champion**, which is right for a like-for-like comparison but does not
  model any funding or fee difference between the two books' hold times.
- **The 19-trade layer-agreement signal from P59 is untouched by this run**
  and remains too thin, and too IS-specific, to gate on.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
