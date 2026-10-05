# P93 — THE PARENT WINDOW'S DEATH AS AN EXIT. The rule would cost the book
# most of its money, and the finding is unusually clean.

> Run 2026-09-29. Harness `exp_parent_death.py`.
> **From `method/NEXT_ROUND_BRIEF.md`, Big Pickle's P92.** **NO ARM WRITTEN.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.

## The proposal

> *"The reference event for a position is the death of the higher-timeframe
> thesis that opened it."*
>
> *"Exit is the ratcheted 15m swing-pivot stop and nothing else — the 3R
> target at v18:592 is computed, stored, never checked. 85 trades outlive
> the 1h window that authorised them."*

The brief required descriptive measurement first, and an arm only if the
giveup is **negative** (the rule would add money) in at least 3 of 4 cells.

## Result — the opposite of the expectation, in all four cells

| lane / era | trades | outlive window | share | **outlive mean R** | outlive total | inside mean R |
|---|---|---|---|---|---|---|
| champion IS | 499 | 103 | 20.6% | **+4.915** | **+506.2R** | −0.157 |
| champion OOS | 251 | 43 | 17.1% | **+4.389** | **+188.7R** | −0.379 |
| utcsat IS | 453 | 100 | 22.1% | **+5.098** | **+509.8R** | −0.126 |
| utcsat OOS | 224 | 34 | 15.2% | **+4.439** | **+150.9R** | −0.286 |

**Cells where outlive-mean R is negative: 0 of 4. The brief required ≥3.
NO ARM WRITTEN.**

## The finding is sharper than the proposal's framing

**The trades that outlive their parent window are the BEST trades in the
book, not the worst.** Mean +4.4 to +5.1 R each, against a book average of
+0.65 (IS) and +0.25 (OOS) — **roughly seven to twenty times the average.**

**And the trades that close INSIDE their window have negative mean R in
every cell** — −0.157, −0.379, −0.126, −0.286.

> **The 1h window is where trades go to die, not where they rip. A position
> that is still open when its window closes is, almost by construction, one
> that is working.**

**The concentration is the tail, as everywhere else in this book:**

| cell | outlive >+10R | share | worth |
|---|---|---|---|
| champion IS | 12 of 103 | 11.7% | **+317.5R** |
| champion OOS | 5 of 43 | 11.6% | +92.9R |
| utcsat IS | 13 of 100 | 13.0% | +334.2R |
| utcsat OOS | 3 of 34 | 8.8% | +69.2R |

**About 12% of outliving trades carry 63% of their value** (+317.5R of
+506.2R in champion IS). **The rule would not merely shave the book — it
would remove the 12% of trades that fund it.**

## The permutation agrees, and says the feature is real

```
champion IS    mean R of outlive trades +4.915   block-permutation p = 1.0000
champion OOS   +4.389                                    p = 0.9995
utcsat   IS     +5.098                                    p = 1.0000
utcsat   OOS    +4.439                                    p = 0.8800
```

**p ≈ 1.0 means no block-permutation of this feature across trades produces
anything close to +4.9 R.** **The outlive cohort is not a coincidence, it is
a real and strongly identified population.**

**Which is exactly why the exit rule is wrong.** The feature is
*predictive*, so gating on it does not remove losers — it removes the
winners. A gate whose cohort is 7–20× the book's average is a gate that
should be used to **add** trades, not to cut them, and that is a different
experiment with a different risk.

## What this connects to

**P92 measured that the book's drawdowns are short and sharp — median 23
days underwater.** This explains why: **the trades that carry the book are
the ones that run past their window**, and a window's expiry is a much
shorter leash than the ratcheted swing stop. **The existing exit is
already the looser one, and the looser one is the profitable one.**

**And it is the same shape as FS_ENTRY's finding, which P77 already
recorded: everything open at the first-seal moment was worth holding.**
Two independent exit events — the LTF's own FS and the parent's death —
both point the same way, from opposite directions.

## Stated limitations

- **The trade counts differ slightly from the pins** (499 vs 500, 251 vs
  279 in OOS). The OOS drop is larger: 279 → 251 means **28 OOS trades
  could not be matched to a window** and were excluded from this table. That
  exclusion is not random — unmatchable trades are those whose entry falls
  in no recorded window — and it is the one weakness in the cohort split.
  It is reported rather than papered over.
- **The window intervals come from the engine's own output**, and are
  matched by timestamp with a linear scan, so a trade whose entry sits on a
  boundary could be attributed to either neighbour.
- **Both lanes are the same data.**
- **This is a descriptive result.** No arm was written and none should be
  without re-registration, because the rule removes trades into the exit
  family `CLOSED_DO_NOT_REPEAT` already covers, and it would need the
  gray-vs-skip comparison the wick work showed is not optional.
- **Block-permutation p is computed on the feature with each trade's own R
  held fixed**, per `FS_TIME_DECISION`'s method — not on an aggregate, which
  is the P82 mistake avoided deliberately.

## Status

**Nothing adopted. No arm written. The brief's threshold was not met by a
wide margin — 0 of 4 against a requirement of 3.**

Champion unchanged 500t/+325.8R IS, 279t/+70.1R OOS.
