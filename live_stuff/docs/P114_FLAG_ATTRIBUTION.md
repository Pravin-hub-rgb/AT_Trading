# P114 — which flag actually carries the champion

**Date:** 2026-09-30 · **Branch:** `agents/champion-reality-audit`
**Harness:** `live_stuff/tests/exp_v19_2x2.py`

This is the cell `reality of champion.md` L75–L76 asked for and never got:

> "Teeno ek saath port karne se aapko pata hi nahi chalega kaunsa R deta hai."
> "`exp_mltf=OFF` wala number kabhi nahi nikala gaya — matlab aapko pata nahi hai champion
> `exp_mltf` ke bina survive karta ya nahi."

Run both features independently, on both ledgers. PERSIST is added as a source patch at
two anchored sites on each of v18 and v19; the gate is already real code in each.

## Result

| arm | IS n | IS net | IS PF | conc | OOS n | OOS net |
|---|---|---|---|---|---|---|
| gate ON, persist OFF | 395 | +137.72 | 1.859 | 1 | 230 | **−13.26** |
| gate ON, persist ON | 387 | +150.40 | 1.931 | 1 | 219 | **−1.79** |
| gate OFF, persist OFF | 500 | **+325.78** | 2.384 | 6 | 279 | **+70.15** |
| gate OFF, persist ON | 500 | **+325.78** | 2.384 | 6 | 258 | +67.75 |

## Finding 1 — the champion is one flag, not two

Turning the gate off is the entire difference:

| | gate ON | gate OFF | delta |
|---|---|---|---|
| IS | +137.72R | +325.78R | **+188.06R** |
| OOS | −13.26R | +70.15R | **+83.41R** |

**And the single-position version has no out-of-sample edge at all: −13.26R over 230
trades.** On this question there is no ambiguity — the champion does not survive without
`exp_mltf`. It is not a "feature" layered on top of a strategy that also works without
it. Multi-positioning *is* the strategy, and it is the difference between a positive and
a negative OOS ledger.

This retires the framing in `reality of champion.md` L74 that said "mat port karo abhi,
kyunki teenon ek saath port karne se pata nahi chalega". The answer is known now, and
it is not close: the gate carries everything.

## Finding 2 — PERSIST=7 does nothing

With the gate off, PERSIST on the IS ledger is **bit-identical**: 500 trades, +325.78R,
PF 2.384, with it off and on. On OOS it removes 21 trades and costs 2.40R.

With the gate on, it is worth +12.68R IS and +11.47R OOS — real, but an order of
magnitude smaller than the gate, and only in the configuration that has no OOS edge to
begin with.

`exp_persist` is one of the two behaviours v19 was built around. It carries the
majority of nothing. It should not have been described as half the reason the champion
works.

## What this changes

v19's header describes two deliberate departures from v18. On this evidence only one of
them earns the description. The ratchet is unchanged from v18 in both arms, so this is
not about the exit — it is that the hysteresis block was inherited from the champion
config without ever being tested on its own.

Keeping it in the engine is defensible (it costs 2.4R OOS and nothing IS, and removing
it is a separate experiment). Describing it as co-equal with multi-positioning is not.

## Open

Whether PERSIST=7 is worth its 2.4R OOS cost is now a real question, and it is cheap to
answer: P114 already has the OFF arm, so the test is a sweep of the persistence window
against the same two ledgers. Not run here — this document is about attribution, not
tuning.

## Reproduce

    cd live_stuff/tests
    python exp_v19_2x2.py

Eight full simulations; roughly two minutes.