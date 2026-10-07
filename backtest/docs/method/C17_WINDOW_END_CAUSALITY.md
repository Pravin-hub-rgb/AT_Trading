# C17 - the HTF window END was shifted, and every pin in the repo inherited it.

Date: 2026-10-07.
Engine: `backend/src/btc/engines/htf_ltf/unified.py`, the two window gates and
the interval builder.
Status: **fixed.** 214 of 215 registry pins are now stale and are being re-derived.
This file is the record of what changed, what it cost, and - importantly - the
argument that does NOT justify the fix.

## THE FINDING

The window-membership gate has been one condition applied to two numbers that
are not the same kind of number:

    if not (s + 2700 < bar_ts <= e + 2700): continue

`s` is the **open** of the 1h candle that opened the HTF trade. The window's
existence is not knowable until that candle **closes**, at `s + 3600`. So the
start needs the shift: in knowable-instant space, `s + 2700 < bar_ts` is exactly
`s + 3600 < bar_ts + 900` (2700 = 3600 - 900). That half is correct and is the
C15 fix recorded in `HTF_GATE_AUDIT_P101.md`.

`e` is the **open** of the 1m fine bar whose high/low detected the exit
(`exit_ts = fine[fk]["ts"]`, `v7_timecap.py:258`). That bar settles at `e + 60`.
`e` needs no candle to close - it *is* the touch. Applying the same 2700 shift
to it rewrites the second side as

    bar_ts + 900 <= e + 3600

which admits an LTF entry whose **decision instant is up to 59 minutes after
the window was already knowably dead**.

The engine holds its exits on 1-minute data, so the end was always trackable to
the minute. The shift threw that away.

## WHAT IT ACTUALLY COST

A signal is hindsight-lookahead if the window was already knowably dead when we
decided to enter. Counted on the shipped books, before the fix:

| book | era | entries on a dead window |
|---|---|---|
| fsent_champ_long | IS | **4** (2 long, 2 short) |
| fsent_champ_long | OOS | **3** (1 long, 2 short) |
| champion_multi_sw10_leg | IS | **8** |
| champion_multi_sw10_leg | OOS | **5** |

Examples, as (entry instant - exit-knowable instant):

    LONG  2023-07-23 19:30   +53 min   window dead for 53 minutes
    LONG  2021-01-29 14:30   +53 min
    SHORT 2026-03-07 19:15   +10 min
    SHORT 2023-04-16 01:00   +2 min

After the fix: **0 in every cell**, verified by instrumentation rather than by
algebra.

## THE FIX

The end is stored knowable at construction, and both sides of the gate then read
in the same knowable-instant space:

    _wend_settle = 60 if fine_ltf else 3600        # fine bar settles at +60
    wend = ... else int(t["exit_ts"]) + _wend_settle
    ...
    if not (s + 2700 < bar_ts+900 < e): continue   # main gate
    if (_s+2700<bar_ts+900<_e) and ...:           # union gate

`e + 60`, not bare `e`. Bare `e` is *stricter than causal* - it would reject
trades whose outcome we were entitled to know. Measured, the two forms are
numerically identical on both flagship books (zero trades affected); `e + 60` is
recorded because it is the correct one and will matter on other books.

The same bug existed in two gates that `test_experiments_craze.py` injects (the
`exp_defer_h` requeue check and the `exp_window_*_cap` budget gate). Both were
fixed identically, or the shipped engine would have kept the leak alive behind
those knobs.

`exp_tf_family.py` swept every literal `2700` in the built text and asserted the
count was 7. It is now 3, and the three that remain are all window **STARTS**.
The assertion was updated with that arithmetic, not just the number.

## THE SECOND ORDER FINDING - ext_stop_r is now provably dead

The confusion this whole thread started from had a real answer, and it was not
the one first given.

`ext_stop_r=3.0` and `htf_rr=3.0` are the same level: both are
`1h_entry + 3 x |1h_entry - 1h_sl|`. The window gate already removes everything
beyond it. What the knob was actually blocking was the **straddle** - a 15m bar
that opened before the 1m exit and closed after it, so its *close* crossed 3R on
a thesis that had already died.

Per-side ext distribution (this is why the threshold is 3.0 and not the v18
default of 1.5):

| | max ext | blocks at 1.5 | blocks at 3.0 |
|---|---|---|---|
| IS long | **2.847** | 96 | **0** |
| OOS long | **2.843** | 71 | **0** |
| IS short | 3.416 | 29 | 1 |
| OOS short | 3.108 | 18 | 2 |

The long side's ceiling lands just under 3.0 and the short side's outliers just
above it. 3.0 is the **long-safe threshold** - the smallest value at which the
gate stops touching the FS-long side at all. 1.5 cut 96 longs in IS and 71 in
OOS, worth -33R and -59R; that is why 1.5 was left behind.

After C17 the straddle cannot occur, so:

    ext_stop_r=3.0  vs  ext_stop_r=0.0   ->   byte-identical trade lists

in all four cells. The knob now blocks **zero** signals. It is not dead code -
it is a live guard with no work left to do.

## BLAST RADIUS

`exp_pinverify.py`, 215 books with pins, IS era:

    pin held        1   (fullstack_wage10_cd0_sig_sw10)
    pin now stale 214
    errored         0

The registry was green before this change, and that was verified rather than
assumed: the engine was rebuilt with the C17 change reverted in memory and a
12-book sample re-derived against the same pins - **12/12 held exactly**
(`champion_multi_sw10` 500/+325.78, `fsent_champ_long` 525/+528.87,
`bm05_multi_sw10` 456/+277.86, and nine others). So all 214 stale pins are
attributable to C17, and **every previously published pin in this repo was
measured with the lookahead inside it.**

Book-level movement, IS:

    trades   more 167 | same 13 | fewer 34   (mean +3.73)
    net R    up   137 | same  6 | down  71   (mean +10.75)
    aggregate  pins +45467.25  ->  engine +47767.81   (+2300.56)

Headline numbers on the two flagship books:

| book | era | pin | after C17 |
|---|---|---|---|
| fsent_champ_long | IS | 525 / +528.87 / 14.19 | 528 / **+533.37** / **13.42** |
| fsent_champ_long | OOS | 309 / +245.0 / 11.9 | 311 / **+239.6** / 11.9 |
| champion_multi_sw10_leg | IS | 499 / +239.12 / 46.85 | 503 / **+288.52** / **43.20** |
| champion_multi_sw10_leg | OOS | 280 / +72.8 / 50.6 | 288 / **+66.0** / 55.4 |
| champion_multi_sw10 (pre-C16) | IS | 500 / +325.78 / 27.72 | 502 / **+279.33** / 39.30 |

## THE ARGUMENT THAT DOES NOT JUSTIFY THIS

> "The aggregate went UP by 2300R, so the fix is right."

**That argument is wrong and must not be used.** The aggregate rising is a
consequence of the change, not evidence for it. Delete an arbitrary filter and
an aggregate moves too. 71 of 214 books lost R, and the flagship
`champion_multi_sw10` lost **46R**. A reader six months from now who sees that
line and hears "the fix made the numbers worse" will be reasoning from the
wrong quantity.

The only justification is the one the owner's ruling gave: it is lookahead, it
hurts on real capital where the leak is not available to flatter the curve, and
the measured dead-window count goes 7 to 0. That is the whole argument. If a
future change to this gate ever reduces R, that is not a reason to revert it.

## STILL OPEN

- 214 pins are stale and need re-deriving in **both** eras. `exp_pinrefresh.py`
  does not do this: it selects on `pins is None`, i.e. absent, not stale.
- Docs quoting the old pins need updating.
- `ext_stop_r` can now be removed from a book's config at zero behavioural
  cost. That is a separate decision and was deliberately not taken here.
