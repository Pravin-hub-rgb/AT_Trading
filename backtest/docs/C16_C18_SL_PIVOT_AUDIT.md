# C16-C18 - SL PIVOT LOOKAHEAD. Found by reading the chart, not by an audit.

Branch: agents/champion-reality-audit
Date: 2026-10-01. Backtesting only.

> **SUPERSEDED IN PART, 2026-10-01.** The scope note below said "the other 19 still
> carry these". That was true when written and was made false 91 minutes later by
> `203e207`, which added `pivot_rule` to `_collect_signals` and defaulted it to
> `"leg"`. Every one of those 19 engines reads that default, so all of them were
> switched from the origin pivot to the leg pivot without any caller asking. The
> doc was invalidated by the commit written to implement it.
>
> Still true here: the origin pivot IS lookahead, and every code path that
> explicitly asks for it (`pivot_rule="origin"`, the `v19_retro` dropdown book,
> the `champion_multi_sw10` registry entry) still carries the bug by choice.
>
> Now false: "the other 19 engines are broken" and "fixed in v19 only".
> `64a061a` made `pivot_rule` an explicit parameter threaded through
> `simulate_btc_trades_v7` and both `simulate_htf_ltf_streak_halt` entry points,
> so the rule is chosen per book instead of by a shared default. Measured on Bybit
> perp: origin/origin 500 trades +325.78R net, leg/leg 499 trades +239.12R net.
> On the live v18 engine the whole effect is one extra trade and +0.2 points of
> win rate.
**Scope: every engine, not just the champion.** `swing_start_px` is produced once,
in `btc_engine.py:294`, and consumed by 20 engine files. The champion was fixed
locally and the other 19 still carry these. Nothing here is closed.

---

## WHY THESE WERE MISSED

`new bugs.md:601` (the C12-C15 deep-dive) lists its verified-clean items as
"SL-before-ratchet ordering, gap fills at bar open", "trail events ... pivot
known at confirm", "entry price (signal bar close)". It then says:

> The three findings below are all in the HTF GATE path.

That was accurate. The initial-stop *ordering* was checked. The initial-stop
*provenance* - where the pivot number comes from - was not on that list, or in
P112's trade-level audit. Every later "causality proven" claim inherited the gap.

All three below were found by opening the chart on one trade and reading it
against the engine's own output.

---

## C16. The initial stop pivot is a structural pivot, not the leg's extreme - **OPEN, champion only fixed**

`btc_engine.py:294` sets `swing_start_px` from one of three branches:

| line | value | kind |
|---|---|---|
| L191 / L235 | `sl = seg_start` | structural pivot |
| L225 / L230 | `sl = min/max(lo_seg, hi_seg)` | running extreme |
| L250 | `sl = prev_end` | previous swing's end |

`seg_start` is the swing's declared origin. It is **not** the highest price of a
down leg nor the lowest of an up leg, because the leg can travel further in the
trade direction after that bar before it turns.

Read on the chart, 18 Jan 2024 13:30, SHORT, swing #803:

```
13:15   O 42870.00   H 42920.70   L 42870.00   C 42920.20
13:30   O 42920.20   H 42931.30   L 42836.70   C 42868.60   <- ENTRY
```

| | pivot | stop |
|---|---|---|
| RETRO (`seg_start`) | 42920.70 - the 13:15 candle high | 42921.47 |
| correct (running high) | 42931.30 - includes the entry candle | 42932.07 |

The retired rule set a short stop **10.60 below a price the position had already
seen on its own entry candle**. Both trades exited at 40180.00 after 547 bars;
the stop was never hit either way. The whole difference is a smaller risk
denominator producing a larger R: 2688.60/52.87 = +50.85R against
2688.60/63.47 = +42.36R. **Arithmetic, not a better trade.**

- **Affected:** all 20 engines calling `_collect_signals`
- **Fixed in:** `v19_champion.py` only, via `exp_causal_sl=1`
- **Still broken in:** the other 19
- **Falsifier for the fix:** on 18 Jan 2024 13:30 the causal stop must be 42932.07

---

## C17. The causal reset skipped every bar between the swing end and its confirmation - **FIXED in v19**

Each engine builds its own running extreme. In `v19_champion.py` the reset fired
on confirmation but read **one** candle:

```python
_cref = _conf_evs[_cei][1] + 1
_clo = float(candles_ltf[_cref]["low"])          # <- one candle only
```

The reset fires at `confirmed_at_idx` but points back at the bar after the
finished swing. Every candle in between was never read.

30 Nov 2023, swing #692 ended 19:30, confirmed 22:15, entry 23:45:

```
19:45..22:00   running 37429.00
22:15          RESET fires, reads only the 19:45 candle
22:15..23:45   running 37633.20   <- the 21:15 low, 37515.50, never read
```

The stop went on the 22:45 low, 118 points above the 21:15 low, and a **+18.61R
winner became a -1.00R stop-out**.

- **Fix:** scan the range, not one candle -
  `_clo = min(low[k] for k in range(_cref, _ci + 1))`
- `_cref` to `_ci` is entirely past when the reset fires, so it cannot read a
  future bar. Checked across all 2900 swings: `seg_end + 1` is never after
  `confirmed_at_idx`, 0 cases.
- **Status:** fixed and verified in v19. The same defect is present wherever
  another engine builds a running extreme, and those numbers are equally wrong.

---

## C18. The causal reset pointed at the previous completed leg, not the forming swing - **FIXED in v19**

The first causal rule reset to `seg_end`, the last bar of the leg that had just
finished. For the 18 Nov 2024 04:30 long:

| | value | which candle |
|---|---|---|
| RETRO (`swing_start_px`) | 89300.10 | 04:00 |
| causal as first shipped | 88735.70 | 03:30 - the previous swing's end |
| correct (forming swing low) | 89300.10 | 04:00 |

The swing that had just finished was not the swing the position was taken in.
Resetting to its end put the stop 564 points away from anything observable inside
the forming swing - the retroactive pivot, one swing earlier.

- **Fix:** `_cref = _conf_evs[_cei][1] + 1`, the forming swing's first bar
- **Status:** fixed in v19

---

## WHAT THE FIXES ARE WORTH

IS, from the committed engine, both arms asserted against their own pins:

| | trades | net R | SL | TRAIL |
|---|---|---|---|---|
| RETRO (all three defects) | 500 | **+325.78R** | 187 | 313 |
| shipped causal (C16+C17+C18) | 500 | **+314.52R** | 187 | 313 |
| difference | 0 | **-11.26R** | | |

C17 alone was worth **+7.24R** (247.96 to 255.20). C17+C18 together were worth
**+59.32R** (255.20 to 314.52).

OOS, 2021-01-01 to 2022-12-31, both arms run explicitly:

| | trades | net R | PF | maxconc |
|---|---|---|---|---|
| RETRO | 279 | +70.15R | 1.591 | 5 |
| shipped causal | 279 | +70.15R | 1.591 | 5 |

```
trades only in retired : 0
trades only in shipped : 0
stop moved on          : 0 of 279
R changed on           : 0 of 279
```

**Not one trade differs out of sample.** The whole 11.26R is in-sample, which is
what in-sample fitting looks like. It also means the OOS pin in the registry was
correct throughout; none of this changes the out-of-sample figure.

---

## WHAT IS STILL OPEN

1. **C16 is unfixed in 19 of 20 engines.** The champion is the only engine whose
   stop is the leg's real extreme. Every other engine's SL is a structural pivot.
2. **No regression test exists for any of this.** A test asserting "at the entry
   instant the stop must be at the extreme of the swing's own bars to date" would
   have caught C16, C17 and C18. That test does not exist.
3. **The chart previously drew a different swing chain than the engine walked**
   (`minBars=20` from a master preset against the engine's 50), so marks on screen
   were not the marks the engine traded on. Fixed separately, recorded here
   because it is why reading the chart that found C16 was hard to act on.

## HOW THESE WERE FOUND

By opening the chart on one trade, reading where the stop line sat, and asking
what the engine thought the number was. Three defects, all in the initial stop.
No harness in the repo had looked at any of it: they checked structure, HTF gate
causality, R accounting and the entry price. Not one asked where the stop came
from.

Worth recording as a process note. The same chart reading had already surfaced
the missing swing marks and the 18/19 Nov entry question. The eye on the output
found things the harnesses were not looking for.
