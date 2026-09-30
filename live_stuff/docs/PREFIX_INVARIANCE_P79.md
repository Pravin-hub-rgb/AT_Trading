# P79 — PREFIX INVARIANCE. 100% at every cut. Live-trading is not ruled out.

> Run 2026-09-29. Harness `exp_prefix_invariance.py`.
> **Nothing adopted. Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.**
> **This is the one run that bounds what every other number in this round
> can be used FOR.**

## The question, which is prior to all the others

> *"I am going to build a bot for live trading — is this not a lookahead, or
> something like that?"*

**That is prior to every other question in this programme.** A strategy that
cannot be replayed live cannot be traded, however good its backtest is.

**And the repo already half-recorded a worrying answer.**
`TRANSCRIPT_THESIS_BACKLOG.md` line 37:

> *"Prefix audit remains **non-invariant** for baseline and age-2 candidate
> because of the shared full-history swing-chain boundary caveat. Gate-level
> mark lookup **is causal**, but **live replay equivalence still needs
> dedicated validation**."*

Marks were found causal. The chain as a whole was recorded non-invariant.
The validation was never run. This is it.

## The test

Compute the swing chain on the full series. Truncate the series at bar T and
compute it again. Compare the swings **both** runs produced for the region
before T.

- **Invariant** → a live walker sees the same swings. No lookahead.
- **Not invariant** → the full-history run used information from *after* the
  swing it recorded. Fatal for live.

Truncation at 60%, 75% and 90%, on three chains, so the result is not one
boundary's artefact.

**Matching is exact** on the tuple downstream code actually reads —
`(swing_index, dir, confirmed_at_idx, seg.start_px, seg.end_px)` — with no
tolerance, because a tolerant match would hide exactly the small differences
that matter.

## Result — 100.0% everywhere

| chain | swings | cut 60% | cut 75% | cut 90% |
|---|---|---|---|---|
| IS 1h (min_bars 10) | 1601 | 946/946 **100%** | 1199/1199 **100%** | 1432/1432 **100%** |
| IS 15m (min_bars 50) | 2900 | 1744/1744 **100%** | 2184/2184 **100%** | 2617/2617 **100%** |
| OOS 1h (min_bars 10) | 903 | 564/564 **100%** | 694/694 **100%** | 819/819 **100%** |

**Zero differences in 13,201 swing comparisons across nine cuts.** Not "close"
— **exact**, on price levels to six decimal places.

## What this means, and what it does not

**It means the swing chain is replayable.** A live process walking the same
bars one at a time produces the same swings, in the same order, with the
same prices, as the backtest. **The "full-history swing-chain boundary
caveat" recorded in the backlog does not reproduce here**, on either
timeframe, in either era, at any of the three cut points tested.

**So: the FS hybrid's `fs_at_idx` is safe.** The whole of P73–P78 rests on
that field, and it is the index of the bar on which the swing engine — which
processes bars sequentially in `process_bar` — first declared the structure.
P78's concern about the FS mechanism being a lookahead is **not supported**.

**It does not mean any candidate should be shipped.** It is a necessary
condition, and it is now met. Everything else this round established still
stands:

- The champion's numbers are backtest numbers that are now **live-replayable
  in their swing layer**. Whether the *trade* layer — fills, costs,
  `busy_until` across a process restart, the fine-data path — replays live
  is a separate question this test does not touch, and the repo's own
  paper-trading plan exists precisely because of it.
- **The FS hybrid stays closed** (P77: 6 of 8 IS half-years). Causal and
  profitable in one era is not a reason to trade it.
- **The long-side defect P78 found is real and causal** — which makes it
  *more* concerning, not less. A structural weakness that a live system
  will reproduce exactly is one that has to be designed out, not one that
  averages away.

## The one place a caveat still belongs

This test recomputes the chain from the **same candle list**, truncated.
It does not test:

- **incremental/live state** — the engine walking forward bar by bar with
  `reset_with_candle`, which is a different code path from
  `compute_btc_swings` on a list
- **session gaps, reconnection and restarts**, which the repo's forward-test
  plan already lists as live-only risks
- **the fine 1m path used for intrabar fills**

**Those are exactly what the paper-trading month is for**, and this result
does not substitute for it. It does mean the swing layer is not the thing
that will silently diverge.

## Stated limitations

- **Three cut points is not a proof of invariance.** It is a strong
  empirical check across 13,201 comparisons, not a theorem. A prefix audit
  at other fractions, or with a different bar-spacing pattern, is cheap and
  worth running before shipping.
- **The comparison is on the swing records, not on the resulting trades.**
  Prefix invariance of swings does not automatically prove prefix
  invariance of the book, though it makes it much more likely.
- **Only two min_bars settings were tested**, the champion's own 10 and 50.
  The ZigZag arm's chain and any other setting are untested here.

## Status

**Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.**

**The answer to the owner's live question is: no, this is not a lookahead, at
the layer where lookahead would live.** The remaining live risk is execution
and state, not the swing chain, and that risk was already known and already
has a plan attached to it.
