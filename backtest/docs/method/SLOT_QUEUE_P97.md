# P97 — A CORRECT SLOT QUEUE. The champion has no free slot to give.

> Run 2026-09-30. Harness `exp_slot_queue.py`. **NOTHING ADOPTED.**
> Champion unchanged: 500t/+325.8R IS, 279t/+70.1R OOS.
> Identity gate: 340t/+225.3R shipped vs patched-off → **IDENTICAL**.

---

## WHAT P97 DID TO P96

P96 measured the broken guard and repaired it by appending `" 23:59:59"`
to the date string — that blocks to the end of the **exit DAY**, which is
coarser than the design. I flagged P96's −188.1R as possibly an
overstatement.

**It is not. `(b) day-granularity` and `(c) INDEX` guard return byte-identical
books in all four cells** — 230t/−13.3R OOS, 395t/+137.7R IS. Same for
`utcsat`. **P96's number stands.**

## The right fix was already in the repo

| file | discipline | correct? |
|---|---|---|
| `v8_break_entry.py` | `busy_until = exit_idx`; `if i <= busy_until` | ✅ integers |
| `v7_timecap.py` | `busy_until_ts = candles[exit_idx]["date"]` vs datetime string | ❌ **same bug** |
| `v8_3r_trail.py` | same | ❌ |
| `v9_conditional_cap.py` | same | ❌ |
| `btc_engine.py:693` | same | ❌ |
| `v18_streak_halt.py:743` | same | ❌ **the champion** |

**The string form is a regression, not a missing feature.**

And `exp_max_concurrent` — the explicit slot counter — is written
correctly: `int(t["exit_ts"]) > int(candles_ltf[i]["ts"])`, epoch on both
sides. **The slot-queue machinery was built and correct. It defaulted to
`0` (off), while the broken string guard pretended to enforce one
position.**

---

## RESULTS

| arm | champ IS | champ OOS | utcsat IS | utcsat OOS |
|---|---|---|---|---|
| **(a) shipped** | **500t +325.8R** mc6 | **279t +70.1R** mc5 | 454t +359.0R mc6 | 253t +60.2R mc3 |
| (d) placebo | 503t +325.1R mc6 | 294t +91.2R mc5 | 503t +325.1R mc6 | 294t +91.2R mc5 |
| (b) day-granularity | 395t +137.7R mc1 | 230t −13.3R mc1 | 395t +137.7R mc1 | 230t −13.3R mc1 |
| **(c) INDEX guard** | **395t +137.7R** mc1 | **230t −13.3R** mc1 | **395t +137.7R** mc1 | **230t −13.3R** mc1 |

`dNet` for (c) vs shipped: **−188.1R / −83.4R / −221.2R / −73.5R.**


### THE SWEEP — the actual result

`exp_max_concurrent` = 1…8, on the correct INDEX guard:

| cap | IS | OOS |
|---|---|---|
| **1** | 395t +137.7R mc1 | 230t −13.3R mc1 |
| 2 | 395t +137.7R mc1 | 230t −13.3R mc1 |
| 3 | *identical* | *identical* |
| 4 | *identical* | *identical* |
| 5 | *identical* | *identical* |
| 6 | *identical* | *identical* |
| 8 | *identical* | 230t −13.3R mc1 |

> **Seven caps. One book. The guard already binds at 1, so a larger queue
> has nothing to admit.**

**This kills the slot-queue idea — and it is the first time in this round
that an idea died for a structural reason rather than an empirical one.**

### WHY: MTF/LTF occupies the account continuously

The champion's `exp_mltf` / `exp_persist` machinery opens a position, and
the next entry belongs to the **same** open position's re-entry sequence.
That trade holds the only slot for the whole sequence. When it closes, the
slot frees — and the *next* candidate is by construction the one queued
behind it, which then takes the slot again.

**There is no contention because there is only ever one candidate per free
slot.** Concurrency in the shipped book comes *entirely* from the guard
failing to fire mid-sequence, never from two sequences racing.

**So "freeing a slot" is not a lever.** The wick result the owner was
probing — skip → −39.0R, gray → +28.1R — **cannot be harvested by a slot
queue**, because the queue it would exploit does not exist. This is
arithmetic, not a prior.

---

## The E2 test is a FALSE PASS

`fix/method/backtest_checklist_v18.md` records
**"Test E2: No Overlapping Trades — 0 overlapping pairs — ✅ PASS."**

Two independent defects, both verified in source:

```python
# backend/debug/test_cat_e.py
for a,b in zip(tr,tr[1:]):                       # defect 1: ADJACENT pairs only
    if b["entry_idx"] <= a["exit_idx"]: viol+=1
tr = simulate(..., mode="b2_vs_flip_chop")        # defect 2: not the champion
```

| | champ IS | utcsat IS |
|---|---|---|
| trades | 500 | 454 |
| **max concurrent** | **6** | **6** |
| overlapping pairs, **ALL** | **152** of 102,831 | **167** of 102,831 |
| overlapping pairs, **CONSECUTIVE only** | 93 | 101 |

`zip(tr, tr[1:])` tests N−1 adjacent pairs. A concurrency-6 book overlaps
mostly **non-adjacently** — trade 1 vs trades 2,3,4,5,6 — and only the 1–2
pair is ever examined. And the run used a **330-trade** config.

**E2 certifies a book we do not ship, using a method that cannot detect the
thing it claims to test, on the one book where the thing is true.**

This is the eleventh silent bug this round. The rule already in the docs
covers it: *a "PASS" that contradicts an independently measured number is a
bug until proven otherwise.*

---

## WHAT THIS CHANGES

**Serialised, the champion is +137.7R IS / −13.3R OOS, PF 1.10.** Not merely
smaller — out-of-sample it is a losing book.

1. **The shipped 500t is not a position policy.** It is the shape a broken
   guard leaves behind. Quote +325.8R with this attached or not at all.
2. **A correct slot queue cannot rescue it**, because the queue is empty at
   every decision point. Anyone proposing slot policy as the next lever
   should read §THE SWEEP first.
3. **The live path needs an audit, not a patch.** `btc_engine.py:693` has
   the same defect. If the deployed bot uses that guard, **it is running
   without a position cap too** — and unlike the backtest, capital is at
   risk. `method/RISK_CONCURRENCY.md` recorded the symptom in one line and nobody
   followed it.

---

## NOT CLAIMED

- **No production file edited.** The pin is asserted, never moved.
- **Not an argument to ship the bug.** A broken guard is a bug; the pin
  stays because this is a bound, not a verdict.
- **No claim the concurrent trades are unprofitable** — only that they are
  unavailable to a bot whose guard works, or to one account's capital.
- **OOS placebo is contaminated** (+21.1R champion, +31.0R utcsat). The IS
  placebo is clean (−0.7R), and IS is the cell that exceeds M.
- **`exp_max_concurrent` was never on.** Enabling it is not an "improvement"
  to adopt — it is a bug fix, and it costs 188R. That trade is the owner's
  to make explicitly.
