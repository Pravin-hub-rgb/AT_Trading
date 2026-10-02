# PHASE 0 — v18/v19 characterisation. The "before" picture for the unification refactor.

Branch: agents/champion-reality-audit · 2026-10-01 · **read-only, no risk**
Measured by `difflib.SequenceMatcher` on the two source files. Every number here
was produced by that run, not carried from a plan.

## The measurement

```
v18_streak_halt.py   788 lines
v19_champion.py      887 lines
identical lines      781  (99.1% of v18)
non-equal blocks       7
```

**v19 is a fork, not a sibling.** Seven blocks differ and they are small.

## The seven blocks

| # | kind | v18 | v19 | what it is |
|---|---|---|---|---|
| 1 | REPLACE | 1–0 | 1–28 | v19's header, and its statement that `live_loop.py` is stale |
| 2 | REPLACE | 217–220 (3) | 245–261 (16) | **C16 pivot-rule comment vs v19's `exp_causal_sl` comment** |
| 3 | REPLACE | 276 | 317–318 | v19 adds `_rg_s`, `_rg_c`, `PERSIST=7` |
| 4 | REPLACE | 509 | 552–559 | v19's regime-hysteresis hold block |
| 5 | INSERT | — | 623–665 (42) | v19's causal-SL running-extreme machinery, then the comment that the one-position gate is removed |
| 6 | INSERT | — | 675–676 | v19's comment where v18:582 has the live `busy_until` guard |
| 7 | INSERT | — | 685–690 (5) | v19's `if exp_causal_sl:` branch where v18:591 hardcodes the pivot |

**Blocks 5–7 are the whole behavioural difference and they are all insertions into
v18. That is what makes unification cheap: nothing in v18 has to be deleted, only
v19's additions have to become parameters.**

## Symbol anchors

```
POSITION GATE    v18: 572, 582, 748      v19: 665, 847     (v18 arms it, v19 does not)
HYSTERESIS       v18: none               v19: 318, 552-554 exp_persist only in v19
SL PIVOT FLAG    v18: none               v19: 252, 630, 687 exp_causal_sl only in v19
PIVOT RULE       v18: 221, 227-229, 406  v19: 262, 268-270, 449
```

`pivot_rule` is **present in both** — that is C16's work, correctly applied to both
files. `exp_persist` and `exp_causal_sl` exist **only in v19**. `busy_until` exists
in both, armed in v18 and deliberately disarmed in v19.

## DELTA 5 — resolved: a misleading comment, not a behaviour difference

**This looked like a shipping bug and was not.** Traced before asserting it.

`v19:245` says:

> `0 = RETROACTIVE (default, what the champion was measured with): sl_pivot =
> sig["swing_start_px"], the swing's true origin.`

And `v19:687` does:

```python
if exp_causal_sl:  sl_pivot = _csl[i] if direction==1 else _csh[i]   # running extreme
else:              sl_pivot = sig["swing_start_px"]                  # looks retro
```

**But `sig["swing_start_px"]` is already causal under the default `pivot_rule`.**
`btc_engine.py:205` and `:282` compute it:

```python
if pivot_rule == "leg" and candles is not None:
    _lo_leg = [c["low"]  for c in candles[_sw_idx : _br_idx + 1]]   # swing start -> break bar
    ...
    sl = min(_lo_leg)                                                # longs
```

**`pivot_rule` rewrites `swing_start_px` to the leg extreme, which is knowable at
the break bar. So under the shipping book's settings — `pivot_rule="leg"`,
`exp_causal_sl` unset (0) — the LTF SL pivot is causal.** The chain holds:

```
pivot_rule="leg"  →  swing_start_px = leg extreme (causal)
exp_causal_sl=0   →  sl_pivot = swing_start_px  (therefore causal)
```

**All four combinations are causal except `pivot_rule="origin"` with
`exp_causal_sl=0`, which is the pre-C16 baseline and is exactly what it is
documented to be.**

**So delta 5 is a comment defect, not a code defect.** `v19:245` describes
`exp_causal_sl=0` as retro without mentioning that `pivot_rule` has already made
the value causal, and `v18:217` describes the same code path differently. A
reader taking either comment at face value reaches the wrong conclusion — which
is what I did on first reading, and it cost a false alarm on a shipping path.

**It is still worth fixing.** Two files describing one code path differently is
the same class as everything else Phase 0 found, and it is the kind that produces
a wrong answer under time pressure. It does not block the refactor.

## Q3 answered — `busy_until` is dead in v19

```
v19:847   busy_until = ...          (assigned)
v19:9     "busy_until stays empty and is never armed"   (comment)
grep "if busy_until" in v19  →  ZERO hits
```

**Not disarmed — removed.** The variable is computed and never read as a gate. So
`max_positions` does not need to preserve v19's `busy_until` behaviour, because
there is none to preserve. Phase 1 is smaller than it would otherwise be.

## The pin problem — the proposed gate does not work

The plan proposed verifying the refactor against two pins:

```
serial + persist=0 + leg     -> 352t / +146.55R   (claimed: v18 today)
unlimited + persist=7 + leg  -> 499t / +239.12R   (claimed: v19 today)
```

**Neither reproduces today, and they do not bracket the concurrency difference.**

`test_v18_causal_integrity.py:28` builds v18's parameters from
`get_v18_params(INSTRUMENT)` plus `V18_ENGINE`:

```
v18   mode=b2_vs_flip_chop  chop_thresh=61.8  cooldown=20  mcl=5  ext_stop_r=1.5
leg   mode=atr_high        chop_thresh=58.0  cooldown=8           ext_stop_r=3.0
```

**Four parameters differ. The two pins are two different strategies, not one
strategy at two concurrency levels.** The claim that "the two pins sit on opposite
sides of the concurrency difference" is false — they differ in mode, chop,
cooldown and ext_stop as well.

There is also a hard arithmetic check. P117 measured `champion_multi_sw10_leg` at
`exp_max_concurrent=1`: **388 trades IS, not 352.** Serial-on-the-leg-book is 388.
v18's 352 is serial-on-v18's-own-parameters. The two are different books.

## The gate that would actually work

Vary concurrency on **one** parameter set, which is the thing actually being
unified:

```
for a fixed param set P:
    unified(P, max_positions=1)     must equal  current_engine_v18(P)
    unified(P, max_positions=0)     must equal  current_engine_v19(P)
```

with the delta table above as the spec of *which* behaviour each position value is
supposed to select. Only then does a refactor that moves a pin by one trade prove
anything, because the pins would be measuring the same variable.

## Open questions before Phase 1

1. **Which SL pivot default ships?** v18 says `leg`. v19 says retro is the default
   and is what the champion was measured with. These cannot both be true.
2. **Is the 352-vs-388 gap a param difference or a behaviour difference?** Both
   engines, same params, concurrency 1 and 0 — if that reproduces 388, v18's pin
   is measuring a different book and its `COUNT_BAND=(348,358)` is anchored to
   that, which matters independently of this refactor.
3. **Does `busy_until` have any behaviour left in v19**, or is it fully dead? If
   dead, `max_positions` does not need to preserve it and Phase 1 is smaller.

## Open question that survived — arm A does not reproduce v18's own pin

**P122 ran the 2×2. Results:**

| arm | engine @ params | IS | verdict |
|---|---|---|---|
| A | v18 @ v18 | 349t / +177.9R | **pin says 352 / +146.55 — NOT REPRODUCED** |
| B | v19 @ leg | 499t / +239.1R | **HOLDS exactly** |
| C | v18 @ leg | 395t / +62.3R | 388 was a harness number, not a raw-engine one |
| D | v19 @ v18 | 420t / +320.1R | — |

**The pins live at different layers.** 388 and 499 were measured *through*
`test_experiments_craze.py`, which text-patches v18's source and injects
`exp_persist=7`. Raw v18 does not accept `exp_persist` — P122's signature filter
dropped it, along with `exp_mltf` and `exp_partial_r`, and printed that it did.
**So 388 was never a raw-engine number, and arm C could not have reproduced it.**

A raw-engine refactor cannot be gated on harness numbers. That is deeper than the
four-parameter problem found above.

**Arm B is the result that matters for shipping and it holds:** v19 at the leg
parameters reproduces 499 / +239.1R exactly. The patched-v18 harness and raw v19
agree on the shipping book.

**Arm A is the open item.** With `get_v18_params("BTCUSDT_BYBIT")` + `V18_ENGINE`
applied as `test_v18_causal_integrity.py:28` does, v18 returns 349 / +177.9R, not
352 / +146.55. Either the pin is stale or something in the construction was not
replicated here. **Until 352 is re-derived, the delta table must not be treated as
complete** — not because a behaviour difference was found, but because the one
number that would have detected it does not reproduce.

## Verdict on Phase 0

**The gate FAILED, as it should have.** The refactor plan assumed four deltas and
two pins that bracket them. There are five deltas including a live comment
conflict about the pivot default, and the two pins measure two different books.

Neither failure blocks the refactor's *idea* — 99.1% identity with all differences
being insertions makes unification genuinely cheap. Both failures block its
*order*. Phase 1 before these are answered picks a pivot default silently, and
that is how C16 lost half its fix the first time.

## The harness dependency, for the record

`test_experiments_craze.py:22` pins `ENGINE` to `v18_streak_halt.py` and `:23`
reads it as text. 62 anchors are asserted with `s.count(...)` and the source string
is mutated to inject ~54 knobs. Two consequences for this refactor:

- **v18 cannot become a shim until the harness is repointed.** A 5-line wrapper
  would make `read_text()` return 5 lines and every anchor would fail. The
  harness can be repointed in one line; the shim comes after.
- **Text anchors are fragile in a way real kwargs are not.** An em-dash encoding
  corruption broke an anchor once already and killed `build_module`. That is
  Phase 4's argument, and it is independent of everything above.

## Sequencing, corrected

```
Phase 0  DONE — 5 deltas measured, delta 5 blocks the refactor
Phase 0b Answer delta 5. Read which engine actually ran the shipping book.
Phase 1  unified.py — only after 0b. One default, chosen deliberately.
Phase 2  repoint craze.py:22 to unified.py (one line, all 62 anchors survive
        because the text being patched is the same text)
Phase 3  v18 and v19 become 5-line shims. 213 import sites untouched.
Phase 4  move the ~54 injected knobs from source-text to real kwargs.
        Separate effort — touches every experiment in the repo.
```

**Phases 0–3 remove the stated pain: fix a bug once instead of twice. Phase 4
removes the class of bug. They are worth doing in that order and neither is
urgent before 0b.**