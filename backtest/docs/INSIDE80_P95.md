# P95 â€” RETRACTED 2026-10-01 by [`BARS_TO_WEND_P115.md`](BARS_TO_WEND_P115.md).
# ~~THE CIRCULARITY HAS AN ENTRY-TIME ANSWER: bars_to_window_end, AUC 0.84â€“0.87 in
# all four cells.~~ There is no entry-time answer. The AUC was the label.
#
# P95's label was `exit_ts > window_end`, which is `hold > bars_to_wend`. The
# feature and the label shared a variable. Measured against labels that do not,
# bars_to_wend is at 0.470â€“0.537 across all four cells, both pivot rules, both
# books. Identity.

> Run 2026-09-29. Harness `exp_inside80.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The question

P94 found that 13â€“22% of the champion's trades â€” those outliving their
parent window â€” carry 142â€“269% of the R, at 7â€“20Ã— the book average,
winning 24 of 24 shared half-years. It failed on M and it was **circular**:
`exit_ts > window_end` is only known after the trade ran.

So: **do the other 80% have anything about them that was knowable at
entry?** If yes, the cohort becomes usable without the circularity.

## Result â€” RETRACTED. No feature separates. It was not causal.

**P115 re-measured every row below against labels that do not contain
`bars_to_wend`. Every "separates" verdict in this table is withdrawn.** The
bars_to_wend rows read identity (0.470â€“0.537). The `room` row was not retested and
its verdict is therefore unknown, not "separates".

| lane / era | feature | **AUC** | mean OUT | mean IN | reads |
|---|---|---|---|---|---|
| champion IS | atr_pct | 0.516 | 0.316 | 0.305 | no separation |
| champion IS | dist_ma | 0.476 | 0.133 | 0.483 | no separation |
| champion IS | **bars_to_wend** | **0.847** | **458.8** | **76.6** | **identity (P115)** |
| champion IS | room | 0.395 | 3.485 | 4.266 | not retested (P115) |
| champion OOS | **bars_to_wend** | **0.859** | **442.7** | **81.3** | **identity (P115)** |
| utcsat IS | **bars_to_wend** | **0.843** | **457.2** | **76.1** | **identity (P115)** |
| utcsat OOS | **bars_to_wend** | **0.867** | **442.1** | **69.0** | **identity (P115)** |

**~~AUC 0.5 is no separation. `bars_to_wend` sits at 0.843â€“0.867 in all four
cells and nowhere else.~~ WITHDRAWN: that is the label, not the feature.

**RETRACTED (P115): the countdown was the label, not the feature. The original
mechanism argument is preserved below and is wrong.

The mechanism was plain: a trade entered with 459 bars of window left (~4.8 days, not 76 — unit error) has room to run; a trade entered with 77 bars left (~0.8 days, not 13 — unit error) is boxed in by its own thesis's expiry within two weeks.**

**And this is knowable the moment the position opens.** It is a countdown on
the window that authorised the trade, measured at entry, using only bars at
or before `entry_ts`. **That is exactly what P94's cohort could not do.**

## Why this does NOT make the cohort adoptable

**AUC is separation, not a gate.** Building a rule on `bars_to_wend` means
choosing a threshold, and every number here is reported without one â€”
**no threshold is fitted and none is selected, so these are descriptions.**
That is deliberate: 0.85 AUC across four cells is strong, and the temptation
to sweep a cut on it is exactly the P69 grid-peak trap.

**The M problem is untouched.** The cohort still fails magnitude at
0.47â€“0.93Ã— M (P94), and a threshold that admits trades with a long
countdown still admits roughly the same 13â€“22% of the book. **A filter that
keeps 20% of trades cannot manufacture a 193.4R swing from a +70.1R OOS
book.**

**And the direction is ambiguous in a way that matters.** `room` â€” the
entry's distance to its stop in ATR units â€” P115 did not retest it; P95 read AUC 0.37â€“0.42,
i.e. inverted: **the good trades start CLOSER to their stop** (3.5 ATR versus
4.3). That is a coherent second mechanism, and two coherent mechanisms
P115 did not retest `room`; its verdict here is therefore unknown, not "separates".
The bars_to_wend rows in the table above were retested and read identity.
pointing at different trades is the signature of a story rather than a rule.

## What this actually establishes

**The champion's 80% are not entry mistakes.** P94's cohort is not a set of
signals the champion should have declined â€” it is the subset that happened
to be given enough room. **A trade opened with 13 days of window left is
structurally unable to outlive it**, however good the signal was.

**So the answer to "why does the champion take the other 80%" is:**

> **Because the window expires. Not because the entry was wrong â€” because
> the position's own higher-timeframe thesis runs out before a 4.9R move has
> room to develop.**

**And that reframes P94's circularity objection honestly.** The cohort was
not random and not cherry-picked; it was **the trades the window gave
enough time to**, which is knowable at entry. What is *not* established is
that selecting on it helps, because selection removes trades and this
programme's record on removal is thirty-one failures.

## Volatility and MA contribute nothing

```
atr_pct    0.516 / 0.570 / 0.550 / 0.565   -> no separation, four of four
dist_ma    0.476 / 0.543 / 0.464 / 0.506   -> no separation, four of four
```

**The P69/P87 volatility ceiling, the only feature that ever survived
period control, does not separate these cohorts at all.** And the MA
distance â€” P86's conditioned feature â€” does not either. **What P95 believed separated them (retracted)
is time, not price behaviour.** That is worth recording because the whole
round was spent looking for a price-based separator.

## Stated limitations

- **Both lanes are the same data.**
- **AUC is computed on the same data it describes**, so it is a description
  of this book and not an out-of-sample estimate. Nothing is fitted and
  nothing is selected, which is the only reason it is reported at all.
- **`bars_to_wend` is mechanically related to the label** â€” a trade cannot
  outlive a window that is nearly closed. **Some of the 0.85 is arithmetic
  rather than predictive**, and this run does not separate how much. That
  is the honest limit on the number, and it is why no threshold is proposed.
- **Window intervals come from the engine's own output**, matched by
  timestamp with a linear scan.
- **`room` is the only other feature P95 called separating, and it separated the other
  way**, so the two are not telling one story.

## Status

**Nothing adopted.** The finding is descriptive and it changes the
explanation of the book, not its behaviour.

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.

**Recorded: the champion's weaker 80% are window-limited, not
RETRACTED 2026-10-01 by BARS_TO_WEND_P115.md: the countdown was the label, not
the feature, and bars_to_wend reads identity against labels that do not contain
it. P94's outlive-cohort finding stands on its own r_multiple evidence and is
unaffected; only the feature claim dies.
entry-mistakes â€” and P95 found no price-based feature separating them, only the
countdown.**
