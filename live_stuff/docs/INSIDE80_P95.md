# P95 — THE CIRCULARITY HAS AN ENTRY-TIME ANSWER: bars_to_window_end,
# AUC 0.84–0.87 in all four cells.

> Run 2026-09-29. Harness `exp_inside80.py`. **Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The question

P94 found that 13–22% of the champion's trades — those outliving their
parent window — carry 142–269% of the R, at 7–20× the book average,
winning 24 of 24 shared half-years. It failed on M and it was **circular**:
`exit_ts > window_end` is only known after the trade ran.

So: **do the other 80% have anything about them that was knowable at
entry?** If yes, the cohort becomes usable without the circularity.

## Result — one feature separates, in every cell, and it is causal

| lane / era | feature | **AUC** | mean OUT | mean IN | reads |
|---|---|---|---|---|---|
| champion IS | atr_pct | 0.516 | 0.316 | 0.305 | no separation |
| champion IS | dist_ma | 0.476 | 0.133 | 0.483 | no separation |
| champion IS | **bars_to_wend** | **0.847** | **458.8** | **76.6** | **separates** |
| champion IS | room | 0.395 | 3.485 | 4.266 | separates |
| champion OOS | **bars_to_wend** | **0.859** | **442.7** | **81.3** | **separates** |
| utcsat IS | **bars_to_wend** | **0.843** | **457.2** | **76.1** | **separates** |
| utcsat OOS | **bars_to_wend** | **0.867** | **442.1** | **69.0** | **separates** |

**AUC 0.5 is no separation. `bars_to_wend` sits at 0.843–0.867 in all four
cells and nowhere else.**

**The mechanism is plain: a trade entered with 459 bars of window left
(about 76 days) has room to run; a trade entered with 77 bars left (about
13 days) is boxed in by its own thesis's expiry within two weeks.**

**And this is knowable the moment the position opens.** It is a countdown on
the window that authorised the trade, measured at entry, using only bars at
or before `entry_ts`. **That is exactly what P94's cohort could not do.**

## Why this does NOT make the cohort adoptable

**AUC is separation, not a gate.** Building a rule on `bars_to_wend` means
choosing a threshold, and every number here is reported without one —
**no threshold is fitted and none is selected, so these are descriptions.**
That is deliberate: 0.85 AUC across four cells is strong, and the temptation
to sweep a cut on it is exactly the P69 grid-peak trap.

**The M problem is untouched.** The cohort still fails magnitude at
0.47–0.93× M (P94), and a threshold that admits trades with a long
countdown still admits roughly the same 13–22% of the book. **A filter that
keeps 20% of trades cannot manufacture a 193.4R swing from a +70.1R OOS
book.**

**And the direction is ambiguous in a way that matters.** `room` — the
entry's distance to its stop in ATR units — *also* separates, at AUC 0.37–0.42,
i.e. inverted: **the good trades start CLOSER to their stop** (3.5 ATR versus
4.3). That is a coherent second mechanism, and two coherent mechanisms
pointing at different trades is the signature of a story rather than a rule.

## What this actually establishes

**The champion's 80% are not entry mistakes.** P94's cohort is not a set of
signals the champion should have declined — it is the subset that happened
to be given enough room. **A trade opened with 13 days of window left is
structurally unable to outlive it**, however good the signal was.

**So the answer to "why does the champion take the other 80%" is:**

> **Because the window expires. Not because the entry was wrong — because
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
distance — P86's conditioned feature — does not either. **What separates them
is time, not price behaviour.** That is worth recording because the whole
round was spent looking for a price-based separator.

## Stated limitations

- **Both lanes are the same data.**
- **AUC is computed on the same data it describes**, so it is a description
  of this book and not an out-of-sample estimate. Nothing is fitted and
  nothing is selected, which is the only reason it is reported at all.
- **`bars_to_wend` is mechanically related to the label** — a trade cannot
  outlive a window that is nearly closed. **Some of the 0.85 is arithmetic
  rather than predictive**, and this run does not separate how much. That
  is the honest limit on the number, and it is why no threshold is proposed.
- **Window intervals come from the engine's own output**, matched by
  timestamp with a linear scan.
- **`room` is the only other separating feature and it separates the other
  way**, so the two are not telling one story.

## Status

**Nothing adopted.** The finding is descriptive and it changes the
explanation of the book, not its behaviour.

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.

**Recorded: the champion's weaker 80% are window-limited, not
entry-mistakes — and no price-based feature separates them, only the
countdown.**
