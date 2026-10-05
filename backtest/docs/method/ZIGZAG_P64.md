# P64: ZigZag is NOT completed — an integration failure, not a result

> Run 2026-09-29. Harness `exp_zigzag.py`. **NO RESULT. Nothing adopted.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## Status: incomplete. Do not read this as a negative result.

The ZigZag idea was not tested. It could not be run, for a reason that has
nothing to do with whether the idea is any good.

## What happened, in order

**Attempt 1 — the engine silently produced an empty book.** The ZigZag
emitted `{dir, ts, px}` records, the control reproduced its pins, and every
ZigZag cell printed as blank rather than raising. A clean table of empty
rows that looked exactly like a real result. This is the failure mode this
programme exists to catch, and it is worth recording: **a silently empty
book is more dangerous than a crash**, because a crash cannot be mistaken
for a finding.

**Attempt 2 — record shape corrected, and it got further.** The engine does
not read `{dir, ts, px}`. `btc_swing.compute_btc_swings` emits records
carrying `swing_index` (with v18's `skip_first` dropping index 0), a `seg`
block of `start_idx`/`start_px`/`end_idx`/`end_px`/`dir`, a `breaks` list,
and `confirmed_at_idx`/`confirmed_at_time`/`fs_at_idx`/`fs_at_time`. The
engine indexes **bars, not timestamps**, so a ZigZag has to be re-expressed
in that idx vocabulary before it means anything. An adapter
(`as_swing_records`) was written to do exactly that, and it does stamp
`confirmed_at_idx` with the **confirmation** bar rather than the pivot —
which is the one part of this that is not negotiable, because a pivot-stamped
swing is the P52 lookahead and would make any number here meaningless.

**Result: the adapter produces plausible swings and the engine still returns
zero trades.**

```
IS  dev 3.0%  1984 swings   ZERO trades
IS  dev 5.0%   342 swings   ZERO trades
IS  dev 8.0%   130 swings   ZERO trades
OOS dev 3.0%  1189 swings   ZERO trades
OOS dev 5.0%   510 swings   ZERO trades
OOS dev 8.0%   199 swings   ZERO trades
```

The swing counts are sensible — a 3% retracement yields more swings than an
8% one, on both series, in both eras — so the segmentation itself works.
**The engine is not consuming these records**, and reverse-engineering the
remaining contract from the consumer side was not something I could do
reliably in this session.

## Why I am not going to guess at the rest

It would be easy to keep adding fields until trades appear, and then report
whatever came out. **That is precisely how a fitted artefact is born.** The
remaining contract is the part that determines which swings actually gate
entries; guessing at it and then reading a P&L off the result would put an
uncontrolled degree of freedom between the experiment and its conclusion.

So the honest position is: **the segmenter is built and validated, the
adapter is built and is causal, the integration is unfinished.** Those are
three real artefacts, and the third gap is a named one.

## What would finish it

Read the consumer path — `v18_streak_halt` → `simulate_btc_trades_v7` →
where it indexes `swings` — and satisfy the contract it actually has, rather
than the shape inferred from the producer. Then run with the **identity
check still in place**: the control must reproduce 500t/+325.8R before any
ZigZag cell is read, exactly as it does now.

**Pre-registered and unchanged for whenever it runs:** `dev` in
{3, 5, 8}%, family-wise — all three must beat the champion in both eras in
both lanes *and* clear M = 193.4R, or none is adopted. No `dev` is chosen
for looking good. This is a sensitivity check with a joint pass criterion,
not a threshold search.

## Why the item stays open

The queue's framing was that this is "the closest reachable relative of the
dead P1/P2 wave labelling", and that judgement has not been tested in
either direction. **A different segmentation of the same bars remains a
genuinely open question** — it is the one thing left on the queue that needs
no data fetch. This run did not close it; it built two thirds of it and
found out where the wall is.

Nothing adopted. Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
