# The four validation techniques, run on 107 and 110

2026-10-16, branch `research/four-validation-techniques`. Source: the four
techniques in `4 backtesting techniques behind winning strategies.md`.

Scope is 107 and 110 only. The portfolio is 54 pinned books; these two are the
ones going live and the open question is which, so a verdict on any other book
changes nothing. Every number below is on the current engine with
`exp_no_opposite=1` in force.

---

## Summary

| technique | 107 | 110 | better |
|---|---|---|---|
| T1 parameter sensitivity | flat, no cliffs | **cliff, and IS/OOS invert** | **107** |
| T2 walk forward | re-optimising matches or beats registered, 3 of 3 | **re-optimising loses, 3 of 3** | **107** |
| T3 stress (slippage) | break-even ≈ 105 bps | break-even ≈ 130–160 bps | **110** |
| T4 survivability | survives every ordering | survives every ordering | tie |

**110 wins the test it was already winning. 107 wins the two that were empty.**

---

## T1 — parameter sensitivity

The doc's failure shape is a cliff: one neighbouring value collapses. A 1-D
sweep cannot detect a cliff that only exists in the interaction between two
parameters, so both axes are drawn together.

### 107 — `cooldown_bars` × `exp_persist`

| IS net R | p=5 | p=6 | p=7 | p=8 | p=9 |
|---|---:|---:|---:|---:|---:|
| cd 2 | 537 | 536 | 536 | 532 | 532 |
| cd 4 | 537 | 536 | 536 | 532 | 532 |
| cd 6 | 538 | 538 | 538 | 534 | 534 |
| cd 8 (reg) | 539 | 538 | 538 | 534 | 534 |
| cd 10 | 543 | 543 | 543 | 539 | 539 |
| cd 12 | 544 | 544 | 544 | 540 | 540 |
| cd 16 | 546 | 546 | 546 | 542 | 542 |

IS range **+532 to +546** across 35 cells — fourteen R, under 3% of the mean.
OOS range **+245 to +280**. The registered cell is mid-range, not a spike.

**This is the doc's picture: a cluster of profitable values, very slowly
degrading.** There is no cliff, no spike, no direction. 107 does not care what
these two knobs are set to.

### 110 — `exp_trail_skip_n` × `exp_persist`

`exp_persist` is flat here too, so the whole story is on `skip_n`. Read the two
eras side by side at persist=7:

| skip_n | IS net | IS DD | IS streak | OOS net | OOS DD | OOS streak |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | +503 | 26.3 | 22 | +257 | 10.3 | 11 |
| 2 | +525 | 23.5 | 16 | +241 | 11.0 | 6 |
| 3 | +584 | 22.8 | 16 | +292 | 12.6 | 10 |
| 4 | +640 | 26.1 | 16 | +310 | 13.8 | 10 |
| 5 | +626 | 25.4 | 16 | +302 | 14.9 | 9 |
| **6 (registered)** | **+644** | **23.9** | **13** | **+336** | **14.9** | **9** |
| 7 | +616 | 30.5 | 16 | **+343** | 14.9 | 9 |
| 8 | +589 | 29.9 | 16 | +302 | 17.2 | 10 |
| 10 | +534 | 30.5 | 23 | +279 | 18.2 | 12 |
| 12 | +680 | 30.8 | 24 | +260 | 19.3 | 12 |
| 16 | **+733** | 30.9 | 22 | **+163** | **27.2** | **21** |

Two things are wrong, and they are different things.

**There is a cliff at 2 → 3.** +525 to +584 on IS, +241 to +292 on OOS, +51R
and +51R in consecutive steps. A real edge should not care whether the trail
skips two events or three.

**Worse, the two eras invert at the top.** From `skip_n=10` upward, IS keeps
improving — +534, +680, **+733 at 16, the best number anywhere in this table** —
while OOS falls off a cliff: +279, +260, **+163 at 16, the worst**. The IS
optimum is the OOS worst case. `skip_n=16` carries a 22-trade losing streak on
IS and a 21-trade streak on OOS, with a 27.2R drawdown on OOS where the
registered value draws down 14.9R.

This is the doc's overfitting test doing its job. Anyone who had selected
`skip_n` on IS alone would have picked 16 and taken the worst configuration
available.

**In fairness to the registered value:** 6 sits inside the plateau at 4–8, not
at the IS peak, and its OOS result is within 7R of the best cell. It was not
chosen badly. But it sits on a surface with a cliff in it, and the plateaus do
not line up between the two eras.

---

## T2 — walk forward, re-optimising

Both books are fixed, so there is nothing to re-optimise unless a neighbourhood
is searched — which is the point. Each fold searches the grid on the training
windows only, then scores the winner on the window after it, blind.

**107** — three folds, all positive:

| fold | train picked | blind test | registered on same window |
|---|---|---:|---:|
| 1 | cd 16, p 6 | +94.0R (dd 10.2) | +91.0R (dd 10.2) |
| 2 | cd 16, p 6 | +99.3R (dd 13.2) | +98.4R (dd 13.2) |
| 3 | cd 16, p 6 | +194.2R (dd 11.6) | +191.4R (dd 11.6) |

The re-optimised pick beats the registered value in every fold, by a little,
because the surface is flat and it hardly matters which cell you are on.
**Out-of-sample performance is lower than training, which the doc says is
normal, and it is nowhere near negative.**

**110** — three folds, all worse than not optimising:

| fold | train picked | blind test | registered on same window |
|---|---|---:|---:|
| 1 | **skip_n 16**, p 8 | +34.6R (dd 14.0) | **+94.1R** (dd 11.0) |
| 2 | **skip_n 16**, p 8 | +106.0R (dd 28.3) | +106.8R (dd 23.9) |
| 3 | **skip_n 16**, p 8 | +212.2R (dd 10.5) | +219.5R (dd 11.3) |

Re-optimising picked the same cell every time and it was the wrong cell every
time. Fold 1 loses **59R** against simply not tuning, and carries a worse
drawdown. This is the doc's "where most backtests lie to you" in its clearest
form: the search finds `skip_n=16` because it maximises the training window,
and that value does not transfer.

Note what this does and does not say. It does not say 110 is a bad strategy —
its registered value did fine on the same windows. It says **110's edge is
fragile to the process of choosing its own parameters**, which is precisely the
risk the doc is asking about.

---

## T3 — stress

The doc asks what happens as slippage goes 0.01% → 10%. That question had no
answer before this: the engine had no cost or slippage parameter, because
`net_r` applies fees to a trade *after* it is booked. Scaling costs changes
arithmetic, not which trades exist. `exp_stop_slip_bps` (commit `0e280d7`) is
the engine-level knob that makes it answerable — adverse-only, on the exit fill,
at all four stop and trail fill sites.

### Stop-fill slippage

| slippage | 107 IS net | 107 IS DD | 110 IS net | 110 IS DD | 107 OOS net | 110 OOS net |
|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | +538.4 | 28.4 | +644.0 | 23.9 | +272.9 | +336.2 |
| 10 bps | +488.8 | 32.9 | +599.2 | 27.1 | +249.6 | +318.7 |
| 50 bps | +279.6 | 72.7 | +467.0 | 39.6 | +163.1 | +250.2 |
| 100 bps | +32.9 | 123.3 | +261.7 | 63.5 | +58.7 | +150.1 |
| 250 bps | −682.3 | 720.7 | −267.1 | 328.5 | −225.4 | −66.3 |
| 1000 bps | −3842.1 | 3850.7 | −2324.4 | 2340.1 | −1565.4 | −711.3 |

**Break-even slippage: 107 ≈ 105 bps, 110 ≈ 130–160 bps.** 110 tolerates
roughly 30–50% more execution friction before the edge is gone. This is 110's
one genuine win, and it is worth noting the reason — 110's trades run longer and
exit on trail rather than stop, so there is more room between the entry and the
adverse fill.

**Trade count falls as slippage rises** — 107 IS goes 525 trades to 354 at 1000
bps. That is the effect post-hoc cost stress structurally cannot produce:
worse exits push a stop past the `ext_stop_r` admissibility test at entry, so
some trades never qualify. A 33% change in the book from an execution assumption
that only affects the exit price.

### Cost multiples

Fees scaled 1× / 2× / 3×, applied post-hoc. This one is legitimately post-hoc,
because a fee does not change which trades exist:

| book | 1× | 2× | 3× |
|---|---:|---:|---:|
| 107 IS | +538.4 | +523.8 | +509.1 |
| 110 IS | +644.0 | +633.0 | +621.9 |

Both survive tripled costs with a third of a percent of net gone. Fees are not
where these books are at risk; slippage is.

### Not run: execution delay

The doc calls the delay test a killer — instant → 1 day, and *if a delay
improves results that is a good sign*. It is the one T3 item not covered here.
It needs the entry itself to move, not just the exit price, so it is a
substantially larger engine change than `exp_stop_slip_bps` and it is not
cheated by scaling anything. Left for a deliberate pass rather than done badly.

### Historical crises

The OOS era is 2021–2022, which covers the 2022 bear and the FTX collapse but
not 2020 March. There is no 2020 data in this repo, so that limb of T3 cannot
be run without acquiring it. Noted rather than claimed.

---

## T4 — survivability

2000 shuffles of each book's own trades, both eras. The doc's question is not
"is this drawdown an ordering artefact" — the existing shuffle harness already
answered that. It is **"how many orderings leave you flat or worse."**

| book | era | observed DD | its percentile | shuffled DD p50 | p95 | worst | paths >25R DD | paths >50R DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 107 | IS | 28.38 | **99.85** | 12.6 | 19.1 | 32.4 | 0.40% | 0% |
| 107 | OOS | 11.05 | 71.25 | 9.6 | 14.7 | 29.7 | 0.05% | 0% |
| 110 | IS | 23.93 | 95.85 | 15.1 | 23.1 | 34.9 | 2.80% | 0% |
| 110 | OOS | 14.90 | 66.70 | 13.3 | 21.3 | 36.0 | 1.70% | 0% |

**No book has a ruin tail.** Zero percent of 2000 orderings exceed 50R of
drawdown, and the worst ordering either book can produce is 32–36R against an
observed 24–28R. The doc's survivability warning — "many curves going up, a few
going straight down" — is not triggered. Both books are sizeable at any
position size that survives 36R.

### The 107 contradiction, resolved

107's IS drawdown of 28.38R sits at the **99.85th percentile** of its own
shuffled orderings. Read cold, that looks like the doc's red flag: one curve
drawn down far more than the rest.

It is not fragility. The other 99.6% of orderings draw down less than 25R, and
the median ordering draws down **12.6R** — less than half the observed. The
history simply happened to arrange 107's trades unluckily. Being unlucky cost
about 16R of drawdown against the median, and the worst possible ordering
would have cost about 4R more than what actually happened.

**So the two findings are not in conflict.** 107 has the only out-of-sample
result in the portfolio that is distinguishable from luck (p=0.011), and its
observed drawdown is nearly the worst its trade set can be sequenced. Those are
two different properties: one says the edge is real, the other says this
particular run of it was painful. The doc asks which matters for sizing, and
the answer here is that the shuffle p50 of 12.6R is the number to size against,
not the 28.38R in the table.

Note 110's tail is *worse* on the fraction of bad orderings (2.80% above 25R on
IS versus 0.40%), even though its observed DD is lower. Observed drawdown and
ordering risk are not the same quantity, and here they point opposite ways.

---

## What this does and does not settle

**Settles, in 107's favour:**

- 110's strongest knob has a cliff in it and its two eras disagree about which
  side is better. Re-optimising 110 loses to not optimising it, three times out
  of three. That is a fragility property of the strategy's parameter surface,
  and it is exactly what the doc says walk-forward exists to find.
- 107 is insensitive to the two most load-bearing structural knobs it has.
- The 99.85th-percentile drawdown reading on 107 is unlucky sequencing, not a
  broken edge.

**Not settled:**

- Execution delay, which needs a real entry-time change to the engine.
- 2020 March and flash crashes, which need data this repo does not have.
- Which book wins the forward test. Nothing here touches the forward window and
  nothing here should.

**One caution.** These four techniques were chosen *after* 107 and 110 were
selected from the scorecard, and both were already known to be the top two. A
validation suite assembled this way is not an independent test of the selection
— it cannot tell you whether the pair is better than the 52 books not tested,
because the reason these two were picked is exactly the thing these techniques
were not asked about. T1 and T2 are still meaningful about *these* books,
because they test whether the books survive on their own terms. They are not
evidence that the selection was right.