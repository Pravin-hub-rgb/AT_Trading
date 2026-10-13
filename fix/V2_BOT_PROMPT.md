# V2 BOT PROMPT — copy everything below this line and paste it into the other bot

---

You are picking up **V2** of a trading indicator's core swing engine audit: **B2 and FLIP
have never been independently validated.** FS was just finished (V1, V12 closed). V2 is the
same shape of problem.

The previous bot got V13 done (one real B2 bug, fixed and owner-verified) and then got
**stuck on breadth**, and its detector was wrong four times in a row. Every failure is
written down below so you do not repeat them. **Read section 6 before writing any code —
it is the most important part of this file.**

## Repo and state

```
repo      C:\Users\Pravin\Desktop\main\AT_Trading
branch    fix/fs-and-pivot-breaks
HEAD      88ecd00  firstswing: B2 and FLIP break the standing extreme, not this candle's own
engine    backend/src/firstswing.py
chain     compute_btc_swings(...) -> 2764 swings, 7562 marks, over 129,715 15m candles
data      BTCUSDT_BYBIT, 2023-01-01 05:30 -> 2026-09-13 10:00, IST timestamps
```

Uncommitted right now — regenerated on the post-V13 chain, not yet committed:

```
 M backtest/tests/_fs_breaks_pivot.json
 M backtest/tests/_g3.json
 M backtest/tests/_two_point_missing.json
```

**Do not re-pin the registry. Do not run any book. Do not run `exp_rerun_books.py`.**
Books are frozen until the owner signs off on the marks. The V7 fingerprint in
`backtest/tests/fixtures/chain_fingerprint.json` is **stale** (it still describes the
pre-V13 chain, 2753 swings / 7505 marks). Re-pin it only after V2 is accepted.

The chart display line lives on a **different branch**, `fix/insider-zigzag-display`. Do
not merge it into the engine branch. The BTC display comes from
`backend/src/btc/btc_display_walk.py`, **not** from `frontend/src/lib/flowline.ts`.

## The open task (V2)

**Is every B2 and FLIP mark placed where the owner's rule says it should be, across the
whole chain?** Not a sample — the whole chain. B2 and FLIP drive book entries and there
are ~4,800 of them.

## The owner's rules, in his own words

These are settled. Do not reinterpret them.

### B1 and B2 share a direction; FLIP is opposite

> "B1 and B2 are of the same direction. Okay? Suppose there is a candle, a red candle. So
> high of it is an extreme and low of it is an extreme. So another candle breaks the high
> of it. So B1 is high and the direction is set to up. Okay? Now, the rule is that, the
> stuff is that now we have two new. Sorry, one is old extreme, which is the first red
> candle's low, and the new B1 is marked where is the new extreme, right? High of it.
> Okay? Now, the thing is that B1 and B2 are on the same side. If B1 is upside direction,
> the B2 also have to break the extreme on the up direction, right? If B1 have broken in
> the downward direction, so now B2 will be the one who will be breaking up on the down
> direction extreme."

> "Now flip is opposite to the B1 or B2. In some cases we have, we might be having B1,
> then B2, then a flip, then again a B2. B2 would be again on the same direction of B1 and
> B2, right? Then again a flip. This can also happen. **I have seen it multiple times. I
> cannot point it out, but this happens too.**"

### Every mark becomes the new extreme — this is V13, and it is fixed

> "new extreme breaks the previous is true, because breaking new extreme is on itself is
> marking of these B1, B2 and flip, to be honest."

### His full 2023-03-19 walkthrough

> "4:45. This is the first candle. This is red. So that red candle high is an extreme, and
> then a pivot is made at 5:15. So these are the two extreme points we are looking for.
> 6:00 breaks it. So this is a mark B1. So now as this has breached its previous extreme
> of the high side, so now this is a new extreme. Now 6:30 breaks this new extreme, so B2
> comes here. That's it. Now in later time, 5:15 is a low extreme. So now in later time, a
> candle comes, let's suppose at 12:45. This breaches, and we are inside the 50 bar marks.
> So this is a flip. Now the direction also flips. Right, and then later, after the 50th
> bar, we look for an FS. That's it. We are done here."

**Note this carefully: his 12:45 FLIP is *inside* the 50-bar window and is still a FLIP.
The 50-bar gate applies to FS only, never to B2 or FLIP.** Confirmed in the data —
swing 152 has a FLIP 44 bars after its B1, inside the window.

## What is already verified — do not redo, do not break

| case | verdict |
|---|---|
| `2023-03-19 06:00` B1 | **OK** |
| `2023-03-19 06:30` B2 | **OK** — this was V13, the bug, fixed by `88ecd00` |
| `2023-03-20 06:30` FLIP | **OK** |
| `2023-03-20 13:30` FLIP | **OK** (44 bars after B1, inside the window) |

Post-V13 regression state: B1 `2765 legs, 0 missing, 0 late`; FS anchors `10/10 USABLE`;
no-look-ahead `PASS`.

**Also confirmed, and this is the answer to "does B2 come back after a FLIP" — it does:**

```
FLIP,B2             343 swings
FLIP,B2,FLIP        151 swings
FLIP,B2,FLIP,B2      59 swings
FLIP,B2,FLIP,B2,FLIP 14 swings
FLIP,B2,FLIP,B2,FLIP,B2   4 swings
                   ---
swings where a B2 comes after a FLIP:  576
```

The owner said he could not point at an example of B2 returning to B1's side. **There are
576 of them.** He was right; he just could not find one.

**But `B2,FLIP,B2` is 0 swings.** The engine clears `ever_b1_dir` when B2 fires
(`firstswing.py:546`), so once a B2 has fired, a direction that gets re-broken can never
be a B2 again — only FLIPs. If the owner's "B1, B2, FLIP, then B2 again" means
**B2 → FLIP → B2**, that shape does not exist in the chain and the engine is wrong.
**That is a live question for the owner, not a bug you may fix unilaterally.**

## Code map

```
backend/src/firstswing.py
    337-338   up_break   = c.high > self.e_hi_prev.px
              down_break = c.low  < self.e_lo_prev.px
    365-373   _pending_leg_dir can cancel a break before _step sees it
    404-522   _step()  - the whole B2 / FLIP decision
    412-416   flip-born direction: a break back into a direction whose B1 never got
              its B2 IS that leg's B2, not a FLIP  (1 Sep 2026 case, already fixed)
    428-443   the down-side mirror of the above
    469-471   up_break with no B2 still standing -> _flip("up")
    472-519   dir == "up" branch
    499       _tgt = self.e_hi_prev          <- THE V13 FIX
    502       gate: _tgt.idx >= self.b1_bar_idx
    505-513   the 1-candle pivot gap for B2 (b2_gap_bars, permanent default 1)
    520-522   down_break with no B2 still standing -> _flip("down")
    539-599   _lock / _flip / _confirm_direction - where marks are appended
    546       ever_b1_dir = None  on B2 completion  <- why B2 never returns after B2
    599       break_marks.append(... px=self.locked_level ...)
    158       ever_b1_dir - direction of last B1 that never got its B2
backend/src/btc/btc_swing.py
    ~67-68    a FRESH SwingEngine per swing - per-engine state cannot see the chain
```

## ⚠ Section 6 — WHY THE PREVIOUS DETECTOR FAILED FOUR TIMES. READ THIS FIRST.

This is the single most important thing in the file. Every failure was the **detector's**
fault, never the engine's. Do not repeat them.

### 6.1 `px` SEMANTICS ARE MIXED — B2 is the exception (corrected 2026-10-13)

**The old 6.1 here was WRONG.** It claimed a mark's `px` is always the level that was
broken. That is true for B1 and FLIP and **false for B2**.

| mark | `px` recorded | is it the level broken? |
|------|---------------|------------------------|
| B1   | `self.locked_level` (`:540`) | **yes** |
| FLIP | `self.locked_level` (`:599`) | **yes** |
| B2   | `b2_pivot.px` (`:560`) | **NO — it is the candle's own new extreme** |

`_confirm_direction` records `px=b2.pivot.px`, and the B2 branch sets
`b2_pivot = Lvl(px=self.hi ...)` (`:510`) or `Lvl(px=self.lo ...)` (`:460`) — the
candle's own extreme. So a B2's px is *never* comparable to a cross:

```
2023-01-01 20:45  B2 dir=down px=16550.5   candle H 16560.5  L 16550.5
                              ^ exact equality against itself - a strict low break
                                is impossible, so the test reports a false defect
```

**Consequence:** a detector that checks B2 marks by comparing px to candle highs/lows gets
exact equality on *every single mark* and fails all of them. That is what produced the
phantom "47% wrong" and "1722 definite defects" numbers. The mark's `px` must **never** be
compared against a cross. Capture `_tgt` (= `e_hi_prev`/`e_lo_prev`) at runtime instead.

### 6.2 `_tgt` IS the running extreme — a running max IS correct (corrected 2026-10-13)

**The old 6.2 here was WRONG**, and it is what made a correct reconstruction look wrong.
It claimed `e_hi_prev` is a *sealed* extreme and that a running `max(hi[start:i])` is "a
different series". It is not. `firstswing.py:391-396`:

```python
if c.high > self.e_hi.px:
    self.e_hi = Lvl(px=c.high, idx=g_idx, time=self.t)   # plain running maximum
if c.low  < self.e_lo.px:
    self.e_lo = Lvl(px=c.low, ...)
self.e_hi_prev = Lvl(px=self.e_hi.px, ...)                # carried to the next bar
```

`_tgt = self.e_hi_prev` **is** the running extreme as of the previous bar. No retirement or
sealing modelling is needed for the target level.

The owner settled this himself, on 2023-01-10 (extreme = the 06:30 high of 17230.0):

> "the highest point is 6:30, so anyone reaching it would be marked as B2. And 12:00 is
> irrelevant because these are points inside the extreme."

Reading of that date:

```
06:30 high 17230.0   <- the running extreme, formed after B1
11:15 high 17228.0   <- did not reach 17230.0  -> no B2
12:00 low  17179.5   <- inside the extreme     -> irrelevant
13:45 high 17258.5   <- crossed 17230.0        -> B2
```

**So: B2 breaks the running extreme formed after B1 — not a sealed pivot, not B1's own
level.** A running-max reconstruction is the *right* shape. The earlier detectors' running
max was fine; only their `px` comparison was broken.

### 6.3 The three earlier failures, in order, with their wrong numbers

1. **`v2_b2.py`** — asked "does each break beat some prior candle's extreme". Result:
   `4838 MISSING`. Wrong question entirely: every extreme break retires the last one, so
   nearly every break "beats" some prior candle. The number was pure artefact.
2. **`v2_leg.py`** — used `s["seg"]["start_idx"]` as the window start. That is the leg's
   **end** extreme, which sits *after* its own B2/FLIP marks. Produced negative spans
   (`leg -23 bars`) and `3426 fails`. Fixed to window on B1→mark, spans went positive.
3. **`v2_final.py`** — hardcoded a 60-bar window. The owner killed this: *"60 bar is
   totally not worth it here. [...] the biggest candle or range that was not broken. The
   price was kept on between them."* The window is the **leg**, not a bar count.
4. **`v2_rule.py` / `v2_rule2.py`** — cross-tested against a running max, per 6.2. Gave
   `52.56% cross / 47.44% no extreme`. **That number is an artefact of 6.1 and 6.2. Do not
   quote it as a finding.**

Note `v2_rule2.py` sections 1, 2 and 4 are still useful and correct — it validates the four
dated cases, does the side census, and the pattern census. Only its section 3 is invalid.

### 6.4 Measurement traps in this repo

This repo has produced a long run of confident, wrong measurements. All of them were the
measurement's fault.

- Use `idx` and index the candle list. Never parse a formatted timestamp — `fs_at_time`
  used to be `HH:MM` with no date and 1,454 swings span midnight.
- The candle field for dates is `date`, not `ts` — `ts` is an epoch integer.
- Always drive `compute_btc_swings(flow, opts={"minBars": 50}, max_swings=len(flow)//2)`.
  Hand-building a chain with `SwingEngine` gives a different chain (it produced 5,299 marks
  instead of 7,993).
- `exp_v7_freeze.py` only detects mark **count and position** changes. It is a cheap
  regression net, not evidence of correctness — it failed to catch three deliberate edits
  during the FS work.
- The FS freshness scan in `_check_chop` is **dead code** — disabling it outright leaves
  the chain byte-identical. Do not cite it as evidence that anything works.
- The **gap rule applies to FS as well as B1/B2** — `firstswing.py:917-920` (high) and
  `:950-951` (low), inside the two FS pivot selectors. A pivot whose very next candle
  breaches it is rejected outright. Verified 2025-08-22: pivot 21:00 rejected by 21:15,
  FS correctly delayed to 21:45. That case looks "late" and is not a bug.
- FS may land **on** the minBars gate bar but never before it (owner ruling 2026-10-13,
  2023-07-02: the 07:00 candle closes at 07:15, so it is legitimately both MB-50 and FS).
- **Never infer that a rule fired from an index comparison.** A check like
  `breaks[0].idx < gate <= fs_at_idx` only shows the leg's first *emitted* mark preceded
  the gate — a suppressed break is absent from `breaks` entirely, so it cannot appear.
  This produced a false "the break at 06:15 was refused" claim on 2026-10-13; the owner
  found no break there at all. To show the gate or gap rule did work, read the actual
  candle that was skipped and show its values.
- `bars_seen` resets per leg, so `min_bars` is never reached inside a leg.

## Verification you must run before reporting anything

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\tests

# 1. V13 must still hold - B2 on 06:30, not 07:15
python -u exp_two_point_missing.py     # expect 0 missing, 0 late B1
python -u exp_fs_breaks_pivot.py       # expect FS anchors 10/10 USABLE
python -u exp_g3_no_lookahead.py       # expect PASS
python -u exp_v7_freeze.py             # WILL report drift - stale fixture, expected
# 2. V2 B2/FLIP placement - 7 dated cases, all must pass
python -u exp_v2_b2_flip.py
```

Plus your own V2 detector, gated on **seven** dated cases before it is allowed to report a
breadth number. **If your detector gets any of them wrong, it is the detector that is wrong
— stop and fix it, do not report a percentage.**

| timestamp | mark | status |
|---|---|---|
| `2023-03-19 06:00` | B1   | V13 anchor, broke 27060.5 |
| `2023-03-19 06:30` | B2   | V13, broke 27123.1 (was 07:15 pre-V13) |
| `2023-03-20 06:30` | FLIP | broke 27715.5 |
| `2023-03-20 13:30` | FLIP | broke 28298.9, 44 bars after B1 — inside the 50-bar window |
| `2023-01-02 09:15` | B2   | **owner-confirmed** — B1 01:45 → FLIP 02:30 → B2 09:15 |
| `2023-01-06 19:15` | B2   | **owner-confirmed** — B1 13:30 → FLIP 14:30 → B2 19:15 |
| `2023-01-10 13:45` | B2   | **owner-confirmed** — B1 06:00 → FLIP 08:00 → B2 13:45 |

**Confirmed shape, 2026-10-13: `B1 → FLIP → B2`.** B2 returns to B1's side *after* the
FLIP. The owner also corrected his own note: on 2023-01-06 the low is 19:00 L 16675.0, not
18:45 (18:45 was 16675.5). Marks unaffected.

## The owner's working method — do not override it

He asked for **many examples, not one**: *"you came up with only one example, and I talked
about giving me many, many examples: look at this, look at that, and we just keep on
fixing it until there is no example."* He reads them on the chart and says yes or no.

So: **produce a list of dated cases, not one.** Narrow to a handful, show him 3–5 at a
time with full `YYYY-MM-DD HH:MM` timestamps and the candles around each, and keep going
until the list is empty. Do not narrow to one convenient example, and do not hand him a
chart with hundreds of dates on it.

He also wants the **rule stated before the detector**. He corrected the previous bot twice
for asking questions he had already answered, and once for asking a question that was not
followable. If you need to ask something, put a concrete dated example in the question and
say plainly which part of it you cannot check yourself.

## Reporting

Report in this order, and do not skip to the numbers:

1. What the rule is, in his words, as you understood it — before any code.
2. What you changed and why, in terms of the rule, not the code.
3. Your dated cases, side by side, before and after.
4. Chain counts before and after.
5. Which verification scripts you ran and their **actual output**.
6. Anything you could not make work, stated plainly.

**Do not quote a percentage unless you can explain, in one sentence, what the denominator
is and why the detector's reconstruction of the extreme matches the engine's.** Section 6
is the reason that sentence is a requirement.

If you cannot solve it, say so and leave the tree clean. That is a genuinely useful
outcome. An unverified change is worse than no change —
`git checkout backend/src/firstswing.py` returns to the last owner-verified state.

## The two questions — BOTH NOW ANSWERED by the owner (2026-10-13)

**Do not re-ask either of these.** They are closed.

1. **Does B2 come back to B1's side after a FLIP? — YES, and that is the normal shape.**
   Confirmed shape is **`B1 → FLIP → B2`**: B2 returns to B1's side *after* the FLIP.
   The chain has `FLIP,B2` (343 swings) and **zero** `B2,FLIP,B2` — which is correct, not
   a defect. Since no B2 ever sits between B1 and the FLIP, there is no `B2,FLIP,B2` shape
   to forbid. **`firstswing.py:546` clearing `ever_b1_dir` on B2 is NOT a bug. Drop it
   from the defect list.** Do not go looking for `ever_b1_dir` or that ordering again.

2. **Is the new standing extreme the candle's own high/low, or the retired level? —
   THE CANDLE'S OWN.** After a mark fires, the new standing extreme is the candle's own
   high/low (`self.e_hi`/`self.e_lo`, updated at `:391-394`). The *level that was broken*
   is the previous running extreme (`locked_level` = `e_hi_prev`/`e_lo_prev`). These are
   two different things and the mark records the broken one — except B2, which records the
   candle's own (6.1).

   This is the crux of the old 6.2 and of every raw detector's disagreement with the
   engine. Both are now settled.
