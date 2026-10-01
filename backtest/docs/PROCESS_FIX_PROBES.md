# THE PROCESS FIX — three assumptions, three wrong answers, and the probe
# that now runs first

Date: 2026-09-28. `backtest/tests/probe_structure.py`

## The user's point

> "tumne he galtiya... pehle haad dekhlo, phir kaam karo"

Correct, three times over. Not three separate lapses — one repeated lapse.

| what I assumed | source of the assumption | what was true | cost |
|---|---|---|---|
| 1m swing compute is memory-bound | the handover said so | it runs in **18.5s** | a whole session framed around a blocker that did not exist |
| sw10/sw20 come from the 15m stream | the handover said so | they come from the **1h** stream | propagated a known error into a brief; a second researcher caught it, not me |
| swings can be read as Elliott waves | **my own inference** | the chain is sequential, with a mean **10.3-bar gap** between swings | wrote a full P1/P2 harness, ran it, got 1 candidate in 2,900 swings, *then* read five lines of `btc_swing.py` |

## The mechanism, named

Every one of those is the same failure: **I verified SHAPE and assumed
MEANING.**

Signatures match, key names are right, the function takes what I passed,
counts are plausible — all checked. What the idea actually *rests on* was
never opened. "Swings" sounded like waves. "MB" sounded like memory. "Same
parameter name" sounded like same source.

That is why the errors survived to the point of costing a run: none of them
would have been caught by a type check, a key dump, or a count.

## The fix, implemented rather than promised

`probe_structure.py` — four probes, each answering a question that has
**already been got wrong**, or is the obvious next trap. Run it before
writing a harness that depends on a structural claim.

```
PROBE 1  swing chain: nested waves or sequential legs?
PROBE 2  which candle stream builds each swing key?
PROBE 3  which documented parameters are INERT on this lane?
PROBE 4  how big is the forward slice (size only - never run it)?
```

Output on the current repo:

- **PROBE 1** — 2,900 swings, `swing_index` 0-based, only 853/2,899
  contiguous, **mean gap 10.3 bars, max 114**, 1,714/2,899 opposite
  direction. Verdict: *chained with gaps — a sequence, not nested waves.*
- **PROBE 2** — `sw10` and `sw20` both from `_flow(c1h)`, the **1h** stream.
- **PROBE 3** — `chop_thresh=58.0` **IGNORED** under `mode="atr_high"`.
- **PROBE 4** — 1,203 15m bars, 2026-09-13 → 09-25, ~13 days, **~464
  trades** at the champion's rate. Kills candidates; confirms nothing.

## The probe caught ME being wrong again, immediately

The first version of PROBE 1 tested `contiguous_fraction > 0.9` and printed
**"NESTED — a wave ratio may be meaningful."** That was the wrong verdict
in the wrong direction: only 853/2,899 swings are contiguous, so the chain
is *not* tightly tiled, and a mean gap of 10.3 bars means the swings
**skip** bars. The correct test is the mean gap, not the contiguous
fraction. Fixed, and the wrong intermediate answer is left in the comment
so the next reader does not re-derive it.

**The probe was wrong on its first run too** — which is the honest
observation to record. A probe is not a talisman; it is five lines you read
instead of five lines you skip.

## Also corrected: the forward slice is bigger than I said

I told the user "~60-70 trades" for `data/forward/bybit/`. **Wrong.** It
holds 1,203 x 15m bars spanning ~13 days, which at the champion's ~136
trades/year is **~464 trades**. That is a materially better gate than I
described: it is big enough to rule on a candidate with real power, though
still far too small to establish one. The earlier figure came from
extrapolating 1-minute-bar counts, not 15m.

## The rule, stated so it can be enforced

1. **Probe before building.** Any idea resting on a structural claim gets
   its probe read first. Five lines.
2. **Never accept a structural fact from prose.** Not the handover, not a
   doc, not my own memory. The handover is wrong at least twice — verified
   twice today.
3. **A probe's first answer is a hypothesis.** PROBE 1 was wrong on run
   one. Read the number, not the verdict.
4. **Report the intermediate wrong answer.** Every fix above is more
   useful than if it had been right first time, because the next person
   can see what the trap looks like.
