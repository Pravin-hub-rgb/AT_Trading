# V-CHECKLIST — verifying the core marks after the B1 fix

**Why this list exists.** The per-kind B1 guard was in the engine from day 1 and was
wrong the whole time. It was only found because B1 was the one mark with an
independent validator built from the owner's own words. Measured on the shipping
chain right now:

| mark | count | independently validated? |
|---|---:|---|
| B1 | 2952 | yes — four validators, validated against the owner's confirmed candles |
| B2 | 2523 | **no** |
| FLIP | 2518 | **no** |
| FS | 2952 | **no** |

That gap is the whole risk. B1 has a detector that can fail. The other three do not,
so nothing would have told us if they were wrong.

**The method, which is the only thing here that has ever worked.** The owner states
the rule in their own words; a detector is written from the RAW CANDLES and never
reads engine state; the detector is validated against the owner's confirmed cases
before it is trusted; the owner then opens the chart and looks at specific
coordinates. Nothing here is proven correct — a detector that reports zero failures
means no rule violation was found, not that the engine is right.

**Numbering.** ARM is taken to ARM26. This list uses **V1..V10**.

---

## The loop, for every item

1. Owner states the rule in plain words. Recorded verbatim, never replaced with
   engine jargon.
2. Write a detector against raw candles. It must not read `SwingEngine` state —
   every previous wrong detector did, and every one produced a confident wrong
   number.
3. Validate the detector against the owner's confirmed cases FIRST. If it calls
   even one of them wrong, the detector is wrong, not the engine.
4. Show the owner chart coordinates.
5. Owner looks at the chart and agrees.
6. Only then is the item closed.

---

## Open

### [ ] V1 — FS has never been independently validated — **HIGHEST RISK**

Every one of the 2952 swings is labelled `kind: "FS"`. FS is the seed of every leg:
if FS is placed wrong, B1, B2 and FLIP all shift with it. There is no detector and
no recorded rule for what makes a swing "first".

**Owner input needed: what is the FS rule, in your words?**

### [ ] V2 — B2 has never been independently validated

2523 B2 marks. `break_kind` is B2 on 1511 of the 2952 swings, so roughly half of
all swings end on a B2. No rule recorded, no detector.

### [ ] V3 — FLIP has never been independently validated

2518 FLIP marks, ending 1441 swings. Same position as B2 and the same exposure:
untested.

### [ ] V4 — `fs_at` and `confirmed_at` disagree on 481 of 2952 swings

Measured on the live chain:

    same bar                 2471 swings
    fs_at EARLIER by 1 bar    186
                 2 bars       120
                 3 bars        91
                 4 bars        39
                 5-10 bars     43

So **16% of swings confirm their first swing somewhere other than the bar the FS is
stamped on**, and the gap runs to ten bars. Whether that is intended is not recorded
anywhere. It is either the rule working, or FS and confirmed meaning two different
things that were never compared.

### [ ] V5 — the `sustain` source never fires

`swing.source` is `chop` on **2952 of 2952** swings. The engine has a second
confirmation path (`confirm_source == "sustain"`, emitting SUS), and on this data it
never runs once. Either it is dead code that should be deleted, or it is waiting on
a condition that has never been tested. Both are worth knowing before the next engine
change.

### [ ] V6 — outside bars hit the V-reversal branch first

Carried over from ARM20, still open. When both `up_break` and `down_break` are true
on the same bar, the shipped V-reversal branch is reached first, so the B1 arming
branches are unreachable there. Behaviour is preserved rather than wrong, but the
fix is incomplete on those bars and nobody has counted how many there are.

### [ ] V7 — no frozen regression fixture of the chain

`backtest/tests/fixtures/` holds `candles.json` and `cases.json` — and `cases.json`
has **two** cases, both about B1. There is no frozen expected chain, so any future
engine edit can move a mark and nothing fails. This is the reason a day-one bug
survived: there was no tripwire.

### [ ] V8 — no independent reimplementation of the zigzag

The strongest single check available and it does not exist. Rebuild all 2952 legs
from raw candles with a plain, obviously-correct swing finder and compare leg
boundaries against the engine's. One test would catch structural drift in FS, B2
and FLIP at the same time, without needing a written-down rule for each.

### [ ] V9 — what decides whether a swing ends on B2 rather than FLIP

`break_kind` is B2 on 1511 swings and FLIP on 1441. Also note 2523 B2 marks exist
but only 1511 swings end on one, so a swing can carry a B2 and still end on a FLIP.
That selection rule is not written down anywhere.

### [ ] V10 — warmup accounting resets per swing

The engine resets `bars_seen` at the start of every swing, so it never reaches
`min_bars` inside a leg. This has already caused one wrong detector to report 7,463
bad marks. The engine-side intent is not documented and is not asserted anywhere.

---

## Done

(nothing yet — this list started after the B1 checklist was closed)
