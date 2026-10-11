# V12 BOT PROMPT — copy everything below this line and paste it into the other bot

---

You are picking up a live defect in a trading indicator's core swing engine. The engine
has had a bug in it since the day it was written. The owner found it by looking at a
chart. Nobody found it with a test, because there was no test.

Read all of this before touching anything. Several plausible-looking approaches have
already been tried and have already failed, and they are listed below so you do not
repeat them.

## Repo and state

```
repo      C:\Users\Pravin\Desktop\main\AT_Trading
branch    fix/fs-and-pivot-breaks
HEAD      2fcfb29
engine    backend/src/firstswing.py  (at a3a9426 - the last state the owner verified)
chain     compute_btc_swings(...) -> 2952 swings, 7993 marks, over 129,715 15m candles
data      BTCUSDT_BYBIT, 2023-01-01 05:30 -> 2026-09-13 10:00, IST timestamps
```

**Do not re-pin the registry. Do not run any book. Do not run `exp_rerun_books.py`.**
The owner was explicit: *"first thing we are going to do from here is always look at the
correct marking. Are those markings correct or not. Then only we will be wasting our
time. Then we will be running this one particular book only after I have said that
marking are correct."* The registry currently holds numbers measured on the engine as
it stands; they are expected to change once this is fixed, and that is fine.

## What the owner has already confirmed as correct — do not break these

| case | what it is | owner's verdict |
|---|---|---|
| 2024-07-16 swing 1226 | FS at 18:00 | **WRONG. Should be 19:00.** Fixed and owner-verified at one point; see the failure log. |
| 2025-07-20 swing 2049 | FS at 15:30 | **WRONG. Owner wants the FS on the pivot's own break.** Open. |
| 2026-08-14 22:45 | B1 up @ 63191.3 | correct |
| 2023-01-14 06:45 | B1 down @ 20809.5 | correct |
| 2023-02-13 04:30 | B1 up @ 21814.1 | correct |
| 2023-02-05 07:00 | must have NO mark | correct (currently none) |
| 2023-03-11 08:00 | must have NO mark | correct (currently none) |

## The owner's rules, in his own words

These are settled. Do not reinterpret them.

**The core of every mark — B1, B2, FLIP and FS alike:**

> "the fundamental core of B1, FS, flip, B2 ... What is the core? That they are
> breaking a pivot. So if any of these are marked where the previous candles have
> broken the pivot, and yet they are not marked there, and yet they are marked after
> the candle. So that is the fundamental breakdown of not following the rule."

**What a pivot is:**

> "what is a pivot? You can look any. So look at from where these flow line is coming
> from. This white flow line on the front end is coming from, these walker lines is
> coming from. So pivot is any V-shape. V-shape, a sharp V-shape. That is what a pivot
> is, upside or downside. Upside would be A-shape and downside would be a V-shape. Any
> sharp edge is a pivot. That's it."

Concretely, his own worked example on 2025-07-20: *"the white line starts from 14:30
high, goes to the bottom of 14:45, then goes to the high of 15:00. So this makes a
pivot at 14:45. Now anyone breaking it is considered as a break. Now 15:15 breaks it,
so it is considered as B1."*

**B1's two locked levels:**

> "starting calculation candle, we need the color of the first candle, because if the
> color of the first candle is green, the low is the extreme here, and then we wait
> for a pivot of the opposite side. So we need B1, then B2, then we are looking for
> FS, and FS cannot happen before a minimum 50 bar."

**The 50-bar window:**

> "if any FS comes before 50th bar, we look. We neglect it. We just going to neglect
> it. We will wait 50th bar, and we will be looking new FS after the 50th bar. If this
> is not happening, so there is something wrong here. And if we are just declaring,
> like FS is there, but it hasn't given the signal of 50th bar, and the 50th bar comes,
> then we are declaring that there is an FS. So this is wrong, because we have to
> enter at FS."

And on the 50th bar itself, 2024-07-16: *"from 5:45 to 18:00 is the 50 candle length,
and FS is marked at exact 50th candle, is making this already suspicious ... And 18:00
being the 50th candle and we have just marked FS here. This clearly says that this is
wrong. So after this, as this is the 50th bar, so after this we will look for an FS and
this FS happened at 19:00. So 19:00 of 16th July would be the correct FS mark."*

**Why this matters beyond the chart:**

> "many books that we are entering on FS. And so we cannot wait for 10 to 12 bars. So
> this goes against our rule."

**There is no lookahead:** the chain ends at the swing's FS, never after it. Verified —
`seg.end_idx <= fs_at_idx` held on 2952 of 2952 swings.

## The open defect (this is the task)

### V12 — an FS can be placed on a level an earlier candle already broke

Owner, 2025-07-20, walking the chart:

> "the marking of 2025-7-20 is wrong. The marking should be at 15:15, but it is at
> 15:30 ... 14:45 is a pivot. The low of it is ... 118037.0. And then 15:00, this is
> not breaking it. Low is equals, so we cannot rule it out. Then 15:15 did break it.
> This is a pivot. And another swing B1 is also there. That means this is fundamentally
> a pivot because it is half broken, 14:45 low. And then there is no pivot here, which
> the 15:30 candle is breaking. So this is very wrong ... But 15:30 is not breaking any
> pivot. That pivot was already broken by 15:15. So there is no fresh pivot. So if B1
> is marked here, either it is from another engine. So what kind of rule is that on
> that engine? Look at it and copy it on this one."

The candles, for reference:

```
date time          open        high         low        close      mark
2025-07-20 14:30  118198.0    118328.1    118047.6    118047.7
2025-07-20 14:45  118047.7    118205.0    118037.0    118037.0    <- the owner's pivot
2025-07-20 15:00  118037.0    118148.0    118037.0    118118.1
2025-07-20 15:15  118118.1    118138.6    117938.4    117953.4    B1 down @118037.0
2025-07-20 15:30   117953.4    118043.2    117926.7    117982.8    FS  <-- owner's complaint
2025-07-20 15:45   117982.8    118027.4    117950.0    117996.1
2025-07-20 16:00   117996.1    118037.3    117985.7    118012.6
2025-07-20 16:15   118012.6    118012.6    117903.6    117926.0    B2 down @117903.6
```

The B1 at 15:15 breaks the 14:45 low and is correct. The FS at 15:30 is placed on that
same level **after it was already spent**, which is the thing to eliminate.

The owner offered two acceptable answers for this case and either is fine — the point
is that 15:30 is not:

- if the 50-bar window boundary means the 15:15 break counts, the FS belongs at 15:15;
- if it does not, the FS belongs at 16:15 on the next fresh pivot (the 15:30 high
  118043.2, sealed when price comes back through it, broken by 16:15's low 117903.6).

### The other reference case — 2024-07-16, which must land on 19:00

```
2024-07-16 05:45   leg / calculation candle starts here
2024-07-16 10:30   FLIP down
2024-07-16 17:15   H=63845.8   pivot sealed
2024-07-16 17:30   H=63819.9   pivot ALREADY broken  (63819.9 < 63845.8)
2024-07-16 17:45   H=64127.0   re-cross of the same spent pivot
2024-07-16 18:00   H=64268.7   the 50th bar; FS currently lands here - WRONG
2024-07-16 18:15   H=64080.0   new pivot forms
2024-07-16 18:30   H=63891.9   that pivot seals
2024-07-16 19:00   H=64084.9   breaks it  -> FS  (owner-verified correct)
```

**This one was fixed once and the owner confirmed 19:00 was right.** It regressed when
the working tree was reverted. Any fix for 2025-07-20 must not break it. Both cases
must be checked on every single attempt.

## The most likely cause, already localised

`backend/src/firstswing.py`, `_check_chop()` builds the FS target via
`_chop_target_high()` / `_chop_target_low()`. Those read `latest_sealed_high` /
`latest_sealed_low`, which the **walker** populates. The walker only seals a pivot once
price has subsequently traded back through it.

That is the wrong timing for the owner's definition. On 2025-07-20 at 15:15 the chop
path returned `target = None` — the pivot did not exist yet in its view — while the B1
path, which reads `e_lo_prev` / `e_hi_prev` (assigned at the top of `process_bar`), had
already caught the same V. Instrumented output:

```
bar     bs   target        pivot sealed at
14:45   48   None          -
15:00   49   None          -
15:15   50   None          -          <- B1 catches the V here; the chop path cannot see it
15:30   51   118037.0      14:45      <- seal arrives, cross fires, FS lands here
```

So the FS is one seal-lag late, and lands on a level the B1 already broke.

The owner's instruction for the fix is explicit: **find the rule the B1 engine uses and
apply it here.** B1 has no gates at all:

```python
# firstswing.py:349-350
up_break   = c.high > self.e_hi_prev.px
down_break = c.low  < self.e_lo_prev.px
```

`e_hi_prev` / `e_lo_prev` are the running extreme as it stood **before** the current
bar, so the moment the running extreme flips, the old extreme *is* the V and it is
available immediately.

The obstacle: `e_hi_prev` / `e_lo_prev` alone are wrong as an FS target, because for an
up leg `e_lo_prev` is the leg's own seed low, which price never comes back to — the
walker pivot is what makes the target **advance** to each successive pullback. Only the
*timing* of recognising it is wrong, not the idea.

## Approaches already tried, and exactly how each failed

Do not repeat these.

**1. Point `_chop_target_*` straight at `e_hi_prev` / `e_lo_prev`.**
Chain went to **0 swings, 0 marks**. The seed-low problem above: the target never
advances, so no leg ever completes.

**2. Keep `e_hi_prev` / `e_lo_prev` but drop the walker-era gates** (the
`dir_established` rule, the 1-candle gap rule, and the "pivot must be ≥2 bars old"
rule). Still **0 swings**. All three gates were written on the assumption that a walker
pivot is already behind price; they are not statements that make sense about a V corner.
Note this for whoever removes them later — they are load-bearing for the walker path.

**3. Track a V corner explicitly** — record `_v_corner_low` when a new high forms (the
low that stood just before it is a V) and `_v_corner_high` when a new low forms, then
have the chop targets prefer the corner over the walker pivot. The corner *was* exposed
correctly at 15:15. Chain still went to **0 swings**, because the remaining gates
rejected the corner. Short-circuiting every gate for the corner also gave 0 swings. This
is the most promising direction and it is **not** solved — the interaction between the
corner and the walker gates is what actually needs working out.

**4. Chain-wide spent-level ledger keyed on price.** The existing per-pivot ledger
(`_crossed_high_pivots`, keyed on `(idx, px)`) cannot see a B1 break, because B1 breaks
`self.locked_level` which is `e_hi_prev.px` / `e_lo_prev.px` — a price with **no pivot
index**. Worse, the ledger was per-engine, and `compute_btc_swings` builds a **fresh
`SwingEngine` per swing**, so a B1 that spent a level on one leg could never be seen by
the FS on the next leg. A chain-wide set passed into every engine did block the 15:30
re-break, but **re-applied on top of the committed 50-bar fix it stopped reproducing the
2024-07-16 19:00 case**. Reverted rather than left half-applied.

**5. The 50-bar window gate itself.** Currently `_check_chop` sets
`_inside_window = self.bars_seen < self.min_bars` and returns early. Note carefully:
the dead-pivot ledger has to be updated for crosses *inside* the window too (a pivot
broken at bar 45 is spent), so this must be a flag checked in the cross branch, not a
bare early return. Both `<` and `<=` have been tried against the owner's wording and
`<` is the one that matches it.

## Code map

```
backend/src/firstswing.py
    ~119-120   e_hi_prev / e_lo_prev declared  (the V B1 uses)
    ~232-233   e_hi_prev / e_lo_prev assigned  (previous bar's running extremes)
    ~349-350   up_break / down_break  <- B1's rule, no gates
    ~386-396   running extremes update
    ~501       B1 mark appended
    ~513-517   B2 mark appended
    ~558       FLIP / B2 mark appended
    ~552+      _check_chop()  - the 50-bar window gate and the cross
    ~605-640   _chop_target_high() / _chop_target_low()  <- the FS target, THE PLACE TO FIX
backend/src/btc/btc_swing.py
    ~67-68     `eng = SwingEngine(_opts)` inside the while loop - a fresh engine per
               swing, which is why per-engine state cannot work
    ~90-111    fs_at_idx is taken from eng.last_chop_cross_idx, with the comment that
               fs_at_time used to be stripped to HH:MM (already fixed)
```

## Measurement discipline — this matters more than it looks

This repo has produced a long run of confident, wrong measurements. All of them were the
measurement's fault, never the engine's. Known traps, all of which bit during this work:

- `fs_at_time` was `HH:MM` with no date on all 2952 swings; 1454 of them have `fs_at`
  and `confirmed_at` on different days. Use `fs_at_idx` and index the candles, never
  the formatted string. (Already fixed.)
- Re-deriving `_chop_target_*` outside the snapshot swap that `_check_chop` performs
  reads a **different, older** pivot. It produced a confident "389 FS have no target,
  447 do not breach their target" that was entirely an artefact. **If you need to know
  what the engine used, wrap `_chop_target_high` / `_chop_target_low` themselves.**
- `bars_seen` resets to 0 for every leg, so `min_bars` is never reached inside a leg. A
  detector that treats `min_bars` as a running-bar requirement reported 7,463 bad marks.
- Chain-building by hand with `SwingEngine` produces a different chain from
  `compute_btc_swings` (it gave 5299 marks instead of 7993). Always drive
  `compute_btc_swings(flow, opts={"minBars": 50}, max_swings=len(flow)//2)`.
- The candle field for dates is `date`, not `ts` — `ts` is an epoch integer.

## Verification you must run before reporting anything

```powershell
cd C:\Users\Pravin\Desktop\main\AT_Trading\backtest\tests

# 1. the two reference cases - BOTH must be right, every time
python -u exp_fs_at_before_after.py

# 2. B1 must not have regressed
python -u exp_two_point_missing.py
#    expect: confirmed candles this test calls wrong : 0
#            first crossing has its B1 : (all legs)
#            level crossed, NO B1 : 0
#            level crossed, B1 LATE : 0

# 3. no look-ahead must still hold
python -u exp_g3_no_lookahead.py

# 4. the tripwire - it WILL report drift, that is expected, but tell me the new numbers
python -u exp_v7_freeze.py
```

`exp_fs_at_before_after.py` takes the owner's four reference dates and prints the
fs_at before and after the working-tree change, so a regression on 2024-07-16 is
impossible to miss.

There is also a frozen fingerprint in `backtest/tests/fixtures/chain_fingerprint.json`
covering all 7993 marks. It was proven to catch the ARM1 bug when that bug was
deliberately reintroduced.

## What "done" looks like

1. **2025-07-20**: the FS is on 15:15 or on 16:15 — the owner's pivot break, or the
   next fresh pivot — and **not** on 15:30.
2. **2024-07-16**: the FS is on **19:00**, unchanged from what the owner confirmed.
3. The owner's eight confirmed candles are untouched, including the two that must carry
   no mark at all (2023-02-05 07:00 and 2023-03-11 08:00).
4. `exp_two_point_missing.py` still reports zero missing and zero late B1s.
5. `exp_g3_no_lookahead.py` still passes at all five cut points.
6. The owner looks at both dates on the chart and agrees **before** anything is measured
   for P&L.

## Reporting

Report in this order, and do not skip to the numbers:

1. What you changed and why, in terms of the owner's rule, not in terms of the code.
2. The two reference cases, side by side, before and after.
3. The chain counts before and after.
4. Which verification scripts you ran and their actual output.
5. Anything you could not make work, stated plainly. Do not leave a half-applied change
   in the tree — `git checkout backend/src/firstswing.py backend/src/btc/btc_swing.py`
   returns to the last owner-verified state, and that is always better than an
   unverified edit.

If you cannot solve it, say so and leave the tree clean. That is a genuinely useful
outcome. A change that is not verified against both dates is worse than no change.

---

## ADDITIONAL OWNER CASES, 2026-07-20 ? read these before starting

The owner walked two legs on the chart in detail. Both are now the acceptance
criteria, alongside 2024-07-16.

### Case A ? 2023-01-03, the leg that starts at 05:45

Owner's walkthrough, his own words:

> "5:45, this is a red candle. As it's a red candle, the extreme is the top of the red
> candle, and 6:00 breaks the top of it, so B1 is marked here at 6:00. Then also the
> low of 5:45 is also an extreme. This also gets broken by 6:30, so flip is marked over
> here. Then later B2 is marked at 11:00 ... FS is marked at 23:30. But why FS is not
> marked before here? Because the 50 candle is somewhere around 17:00 ... and there are
> many down breaks, but low breaks happened at 20:00, some happened at 18:15 too. So
> why these are not marked? Is there a rule that there should be a one candle gap,
> something like that, just like B2 have a rule that this must be a one candle gap rule
> for B2. So is there a rule for FS too? ... So then this flip happens at 20:15. So now
> from here we are looking for an FS, which is upside direction. And so if that's the
> case, then 21:30 is the right candidate to mark an FS. But that doesn't happen. But
> finally, the FS is marked at 23:30. So what is going on?"

**He does not accept 23:30. He wants 21:30.**

The candles:

```
time     open       high         low        close
05:45    (leg start, RED candle)
06:00    B1  - breaks the top of the 05:45 red candle
06:30    FLIP - breaks the low of 05:45
11:00    B2
~18:00   the 50th bar from 05:45
18:15    price breaks lower - owner asks why no FS. There is no pivot here.
20:00    price breaks lower - owner asks why no FS. There is no pivot here.
20:15    FLIP - direction becomes down
20:30    high 16680.0  - owner sees a clear A-shape corner on the white flow line
21:30    high 16686.0  - breaks 20:30's high. Owner says FS belongs HERE.
22:15    high 16654.0  - breaks 16686.0? owner asks about this one too
23:30    pivot 16635.5 breaks - this is where the engine puts the FS today
```

Answer to one of his questions, which is confirmed in the code: **yes, there is a
one-candle-gap rule for the FS/chop target**, the same shape as the B2 rule -
`gap_high = self.bar_highs.get(p.idx + 1); if gap_high is None or gap_high > p.px:
return None`. There are also two more: the pivot must be at least two bars old, and
it must have formed after the leg's direction was established.

What is NOT known: why 21:30 gets nothing. A trace of the committed engine shows the
candidate pivot at 21:30 is 16680.0 and that the raw low-level candidate is rejected,
but the trace conflates "the walker has no pivot" with "a gate rejected the pivot the
walker had", so it does not actually answer it. **Reproduce with the gates separated
before forming any theory.**

### What was already tried for this, and what it cost

An attempt was made to fix 2024-07-16 by letting a cross inside the 50-bar window still
spend its level without arming, plus a spent-level ledger keyed on price and shared
across the chain. It moved 2024-07-16 from 18:00 to 19:00 - the owner's answer - and
kept B1 at 2892/2892 with no missing and no late marks and no look-ahead.

It was reverted because it moved the chain from 2952 swings / 7993 marks to
2891 / 7853 and removed 486 marks while adding 346, and because Case A above was not
checked. Making it per-engine instead of chain-wide did not move Case A either - the
FS stayed at 23:30 - so the ledger was not the reason 21:30 is blocked, though it may
still be too broad: a chain-wide set keyed on bare price treats every occurrence of
16680.0 as the same level, and that price recurs across 129,715 candles.

## The owner's working method, which the prompt should not override

He asked for many examples, not one: "you came up with only one example, and I talked
about giving me many, many examples: look at this, look at that, and we just keep on
fixing it until there is no example." He reads them on the chart and says yes or no.
So: produce a list of dates, not a single case, and keep going until the list is
empty. Do not narrow down to one convenient example.
