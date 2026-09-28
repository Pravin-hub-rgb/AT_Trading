# BIAS WINDOW THEORY — what closes a window is NOT what the comment implies

Answering the user's question directly. Measured, not inferred.
`probe_window_theory.py`.

## The theory, as the code actually implements it

`v18_streak_halt.py`, verified line by line:

| line | what it says |
|---|---|
| :214 | `htf_rr=3.0` — "HTF (1h) fixed R target — controls when window closes" |
| :215 | `window_end="exit"` — "exit" = HTF trade exit (SL/target/16-day cap) [default, +331R] |
| :215 | "r_touch" = first touch of `ext_stop_r` 1.5R — **[tested: +200.6R, −130R vs exit]** |
| :222 | `simulate_btc_trades_v7(..., rr_target=htf_rr, trailing="off", breakeven_r=0.0, sl_mode="swing", cap_days=16)` |

`v7_timecap.py` line 1 states it plainly: *"Time Cap for 1h Flip Fixed 3R.
Exits at market if hold > cap_days."*

So the designed theory is: **a window is one 1h swing's leg — it opens at
the swing entry and closes at +3R, at its −1R swing stop, or at 16 days.**

**And `r_touch` — closing the window early at +1.5R — was already tested
and REJECTED at −130R.** That idea is in the graveyard.

## What actually happens

| | IS (331 windows) | OOS (210) |
|---|---|---|
| **−1R stop** | **228 (68.9%)** | **156 (74.3%)** |
| **+3R target** | **81 (24.5%)** | **43 (20.5%)** |
| **16-day cap** | **22 (6.6%)** | **11 (5.2%)** |
| median days held | **1.17** | **1.06** |
| within 3 days | 70% | 76% |

**Your instinct was right on both counts.**

1. **"3R or −1R or 16 days?"** — all three exist, but they are wildly
   unequal. **The −1R stop is the dominant exit at ~69-74%.** The +3R
   target fires only 20-25%. The 16-day cap fires 5-7%.

2. **"Is it within 3 days?"** — **Yes. The MEDIAN window is ~1.1 days.**
   70-76% close inside 3 days. My earlier 76-hour mean was inflated by
   that 5-7% tail sitting on the 16-day cap; the median is the honest
   number and it is *one day*, not three.

## The consequence nobody wrote down

**The 3R target is not a target the book usually reaches. It is the
exception.** Roughly 7 windows in 10 die at −1R inside a day, and the
mean window R is **+0.08 IS / −0.09 OOS** — the HTF leg is close to a coin
flip on its own, median exactly −1.00.

That reframes the 15m layer's job. The 15m book is not "trading inside a
profitable HTF bias". It is trading inside a **window that is dead 70% of
the time**, and finding its edge among the ~25% that run. Which is
consistent with everything else measured today: the book is low win rate
and tail-concentrated, and the tail is the 1-in-4 windows that reached
+3R.

**It also means the 16-day cap is nearly decorative** — it binds on 22
windows IS / 11 OOS. Any experiment that varies `cap_days` is moving ~6%
of the book.

## What this opens

Not a new entry idea — a **characterisation** of the window distribution
that nothing in the repo records. Two things follow directly and are
untested:

- **Window duration as a feature.** Median 1.1 days, p75 ~3-3.8 days.
  A rule that fades the 15m layer late in a long window, or that
  requires the window to have already proved itself before taking the
  first trade, is testable and is not in the graveyard.
- **Why `r_touch` failed at +1.5R.** It was rejected at −130R, which is
  surprising if 25% of windows reach 3R. If the target is reached by a
  minority and the stop is the common case, closing early at 1.5R should
  have helped — so its failure is a genuine open question, not a settled
  one.

Neither is pre-registered yet, so neither has been run.
