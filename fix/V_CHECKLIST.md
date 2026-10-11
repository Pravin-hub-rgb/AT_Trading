# V-CHECKLIST — verifying the core marks after the B1 fix

**Why this list exists.** The per-kind B1 guard was in the engine from day 1 and was
wrong the whole time. It was only found because B1 was the one mark with an
independent validator built from the owner's own words. Measured on the shipping chain
right now:

| mark | count | independently validated? |
|---|---:|---|
| B1 | 2952 | yes — four validators, validated against the owner's confirmed candles |
| B2 | 2523 | **no** |
| FLIP | 2518 | **no** |
| FS | 2952 | **no** |

That gap is the whole risk. B1 has a detector that can fail. The other three do not,
so nothing would have told us if they were wrong.

**The method, which is the only thing here that has ever worked.** The owner states the
rule in their own words; a detector is written from the RAW CANDLES and never reads
engine state; the detector is validated against the owner's confirmed cases before it
is trusted; the owner then opens the chart and looks at specific coordinates. Nothing
here is proven correct — a detector that reports zero failures means no rule violation
was found, not that the engine is right.

**Numbering.** ARM is taken to ARM26. This list uses **V1..V10**.

---

## The loop, for every remaining item

1. Owner states the rule in plain words. Recorded verbatim, never replaced with
   engine jargon.
2. Write a detector against raw candles. It must not read `SwingEngine` state — every
   previous wrong detector did, and every one produced a confident wrong number.
3. Validate the detector against the owner's confirmed cases FIRST. If it calls even
   one of them wrong, the detector is wrong, not the engine.
4. Show the owner chart coordinates.
5. Owner looks at the chart and agrees.
6. Only then is the item closed.

---

## Open

### [ ] V1 — FS has never been independently validated — **BLOCKED ON THE OWNER**

Every one of the 2952 swings is labelled `kind: "FS"`. FS is the seed of every leg: if
FS is placed wrong, B1, B2 and FLIP all shift with it. No detector exists and no rule
is recorded for what makes a swing "first".

**Blocked on exactly one thing: the owner's rule for FS, in their own words.** The
1..13 bar gap found in V4 belongs with this — whether a swing may confirm bars after
its FS is stamped is part of the same question.

### [ ] V2 — B2 has never been independently validated

2523 B2 marks. `break_kind` is B2 on 1511 of 2952 swings, so roughly half of all
swings end on a B2. No rule recorded, no detector.

### [ ] V3 — FLIP has never been independently validated

2518 FLIP marks, ending 1441 swings. Same position as B2 and the same exposure.

### [ ] V8 — no independent reimplementation of the zigzag

The strongest single check available and it does not exist. Rebuild all 2952 legs from
raw candles with a plain, obviously-correct swing finder and compare leg boundaries
against the engine's. One test would catch structural drift in FS, B2 and FLIP at
once, without needing a written-down rule for each.

### [ ] V9 — what decides whether a swing ends on B2 rather than FLIP

`break_kind` is B2 on 1511 swings and FLIP on 1441. Also note 2523 B2 marks exist but
only 1511 swings end on one, so a swing can carry a B2 and still end on a FLIP. That
selection rule is not written down anywhere.

---

## Closed

### [x] V4 — `fs_at` vs `confirmed_at` — measured, and one real defect found

    same bar                 2471 swings  (83.7%)
    differ                    481 swings  (16.3%)
    gap 1..13 bars, 45 swings at 5 or more

**DEFECT: `fs_at_time` carries no date.** All 2952 swings have `fs_at_time` as a bare
`HH:MM`; `confirmed_at_time` is a full timestamp on every one. 1454 swings have `fs_at`
and `confirmed_at` on different days, so `fs_at 05:45` does not say which 05:45.

`fs_at_idx` is intact and no data is lost, but the formatted field cannot be grouped
on or compared across days — and two probes in this session were misled by it before
the shape was checked. Not yet fixed; it is a display field, and the owner's call
whether to change it.

The gap itself is **not judged**. That is a rule question and belongs with V1.

### [x] V5 — the `sustain` source never fires — measured, owner to judge

`swing.source` is `chop` on **2952 of 2952** swings. The sustain confirmation path is
written out in `firstswing.py` — 20 mentions, `confirm_source` assigned at L657 — and
fires on **zero** swings. Either it is dead code that should be deleted, or it is
waiting on a condition that has never been tested. Owner to decide.

### [x] V6 — outside bars hit the V-reversal branch first — NOT rare

Carried over from ARM20. Measured on the live chain:

    outside bars (up_break AND down_break)   3244 of 129,715 candles  (2.5%)
    of those, carrying a mark                   250
    mark kinds on them                       B1 204   FLIP 41   B2 5

ARM20 read this as an unreachable corner. It is **one B1 in twelve**. The fix is
incomplete on a meaningful slice of the chain, not a rounding error.

204 is also exactly how many marks the G2 guard stops. Same number is either a
coincidence or the same set — unchecked.

Behaviour on these bars is preserved rather than wrong, so this is completeness, not
correctness. Whether one B1 in twelve on an untested branch is acceptable to ship is
the owner's call.

### [x] V7 — no frozen regression fixture of the chain — **built and proven**

`fixtures/` held `candles.json` and `cases.json`, and `cases.json` had **two** cases,
both about B1. There was no frozen expected chain, so any engine edit could move a
mark and nothing failed. That is why a day-one bug survived.

Built in two levels, because one was not enough:

    fixtures/frozen_marks.json        53 marks on the existing 961-candle fixture,
                                      asserted field by field
    fixtures/chain_fingerprint.json   sha256 over all 7993 marks of the full chain
    exp_v7_freeze.py                  verify by default, --write to regenerate

Proven by putting the ARM1 bug back (`if True:` in place of the seal check) and
running it. The small fixture reported IDENTICAL and **missed it**. The full-chain
fingerprint caught it at once — 7993 marks became 8011, exit code 1. The small
fixture is fast but too short to contain the bug, which is exactly why the
fingerprint exists.

### [x] V10 — warmup accounting resets per swing — measured

    engine constructions        2953
    bars_seen at construction   0 on all 2953
    minBars configured          50 on all 2953

`min_bars` is never reached inside a leg, so the warmup never applies there. It is
only compared where a leg starts. This is the behaviour that made an earlier detector
report 7463 bad marks by treating `min_bars` as a running-bar requirement.
