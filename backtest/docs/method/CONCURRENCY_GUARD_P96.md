# P96 — IS THE CHAMPION 3–6 DEEP BY ACCIDENT?
## The deployment bound nobody had measured

Dated 2026-09-30. **Nothing adopted. No production file edited.**

`exp_concurrency_guard.py` · identity gate passed (340t/+225.3R both arms)

---

## THE BUG, verified in source before running anything

```python
# v18_streak_halt.py:743   writes a DATE
busy_until = candles_ltf[exit_idx]["date"]        #  "2026-09-30"

# v18_streak_halt.py:577   compares it against a DATETIME
if busy_until and bar_time <= busy_until: continue #  "2026-09-30 14:00:00"
```

**Python compares these as strings. A longer string is greater than its own
prefix, so `"2026-09-30 14:00:00" <= "2026-09-30"` is *always* `False`.**

**The concurrency guard has never blocked a same-day re-entry.** Not
sometimes, not in some regimes — never.

`method/RISK_CONCURRENCY.md` had already measured the consequence and closed with
one line: max concurrent **6 / 5 / 6 / 3** against a design that intends one
position, **"Recorded, not fixed."**

---

## THE RESULT

M = 193.4R. `(d)` placebo is the arm that makes `(b)` readable — without it
the delta cannot be attributed to the fix rather than to re-timing.

### Lane `champion_multi_sw10`

| | arm | n | net | R/t | PF | **maxconc** | dNet |
|---|---|---|---|---|---|---|---|
| **IS** | (a) shipped | 500 | +325.8R | +0.652 | 2.38 | **6** | — |
| | (d) placebo | 503 | +325.1R | +0.646 | 2.38 | 6 | −0.7R ✅ |
| | **(b) FIXED** | **395** | **+137.7R** | **+0.349** | **1.86** | **1** | **−188.1R** |
| | (c) +strict serial | 395 | +137.7R | +0.349 | 1.86 | 1 | −188.1R |
| **OOS** | (a) shipped | 279 | **+70.1R** | **+0.251** | **1.59** | **5** | — |
| | (d) placebo | 294 | +91.2R | +0.310 | 1.68 | 5 | +21.1R ⚠️ |
| | **(b) FIXED** | **230** | **−13.3R** | **−0.058** | **1.10** | **1** | **−83.4R** |
| | (c) +strict serial | 230 | −13.3R | −0.058 | 1.10 | 1 | −83.4R |

### Lane `utcsat_multi_sw10` — same story, independent params

| | arm | n | net | dNet |
|---|---|---|---|---|
| **IS** | (a) shipped | 454 | +359.0R | — |
| | **(b) FIXED** | 395 | +137.7R | **−221.2R → EXCEEDS M** |
| **OOS** | (a) shipped | 253 | **+60.2R** | — |
| | **(b) FIXED** | 230 | **−13.3R** | **−73.5R** |

---

## WHAT THIS MEANS

### 1. **58% of the shipped IS R is not deployable by a bot whose guard works.**

`−188.1R` of `325.8R`. Not a tail, not a regime — the single largest number
in this round, and it exceeds M on the second lane.

### 2. **Serialised, the champion loses money out-of-sample. −13.3R, PF 1.10.**

**This is not a filter question. It is the strategy.** The 3–6-deep
concurrency *is* the positioning. A working guard removes it, and what
removes it is not a worse version of the book — it is a losing one.

**The design intent was always one position at a time.** Nothing in
`+325.8R` was ever intended to be one position at a time.

### 3. The placebo did its job, and flagged something.

`(d)` is **−0.7R in IS — the fix itself is clean.** But it is **+21.1R in
OOS**, and in `utcsat` it is **−33.8R IS / +31.0R OOS**. A placebo that
moves the book by 30R means **sentinel choice has its own effect**, so the
OOS `(b)` delta carries a re-timing component of unknown size. The IS
result — the larger one, and the one that exceeds M — is placebo-clean.
**Trust IS, treat OOS as indicative.**

### 4. `(b) == (c)` exactly, in all four cells.

Enforcing `exp_max_concurrent=1` changes nothing on top of the fix. **The
two were the same policy**; the guard bug was the only thing separating
them, and it was the only thing making them differ.

---

## ⚠️ WHAT IS **NOT** CLAIMED

- **This is not an argument to ship the bug.** A broken guard is a bug.
  The pin stays as it is because this file reports a bound, not because the
  book is fine.
- **No claim that the concurrent trades are unprofitable.** Only that they
  are unavailable to correct code, or to real capital behind one account.
- **The bot's `htf_rr` re-entry design is not implicated.** The champion is
  explicitly built on `exp_mltf`/`exp_persist` re-entries; this measures
  their *account-level* cost, not their edge.
- **OOS `(b)` is contaminated by the placebo**, per §3.

---

## THE QUESTION THIS FORCES

**The engine has never run the strategy the architecture describes.**

Every number in this programme — 500t, +325.8R, PF 2.38 — comes from a book
that the code was **not supposed to be able to produce.** The honest
sequence from here is *not* another filter:

1. **Decide what a position is.** One at a time is the design and it loses.
   6-deep is the edge and it needs a guard that actually guards. **These are
   different strategies and the programme has only ever measured one.**
2. **A correct multi-position guard** — max N open, slot queue, real
   comparison — is *unbuilt*. `method/RISK_CONCURRENCY.md` deferred it. The slot
   queue was on the "next" list with no harness behind it.
3. **Until then, +325.8R should be quoted with this attached**, because the
   gap between it and deployable expectancy is 188R in IS and the full
   70R in OOS.

**This outranks P95.** P95 asked which trades are best. This asks **whether
the book that holds them can be traded at all.**
