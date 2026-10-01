# 1-MINUTE SCALPING BOOK — built, run, and it FAILS as a standalone book.
# One B1 lead survives into OOS and is worth a follow-up. Nothing adopted.

Date: 2026-09-28. Harness: `scalp_1m_engine.py` + `exp_1m_scalp.py`
→ `_1m_scalp.json`, `_1m_scalp_autopsy.json`. Path-true, 335.6s.
No production file edited.

## What the user asked for

> "1h tf bias open, 15min normal trade open, now this is also a window, now
> 1min decides to trade … 1:2 fixed trading wager … 1min mai bhi b1, b2, flip
> wagera karo … sab engine banao joh 1min mai b1, b2, flip fs kare 1min ke
> grind level pe"

Built exactly that: a **separate 1m book** running inside the same 1h
windows, alongside the untouched 15m book. Fixed 2R target, 1m swing-pivot
stop, 1m trail, all four mark kinds including **B1** (which the shipped
`_collect_signals` cannot express at all — added via in-memory rebuild).

Crucially this is **not** the blocked "Phase 1" patch. That one swapped
`swings_ltf` inside the shipped engine and is index-coupled to
`candles_ltf` (91% signal loss, 15× param rescale). A separate book has no
such coupling, which is why it was worth building.

## ⚠️ THE FIRST RUN PRINTED A FAKE +2947R — AND IT WAS MY BUG

First run, `is/champion mb10 decisive`:

    16t  net +2947.5R  WR 37.5%  PF 571.226  DD 2.6  exB5 -3.2

`PF 571` with `DD 2.6` is not a trading result. The run's own numbers said
so: 34,037 signals cleared the window gate but only **16** became trades,
and **ex-best-5 was negative** while net was +2947 — the whole book was 3
trades.

`scalp_1m_autopsy.py` measured it rather than assuming:

    n=16  net=+2947.5R  MEDIAN r = -0.105  max_r = 2942.7
    risk/ATR: median 6.33   below the 0.25x ATR floor: 0/16

So it was **not** the usual degenerate-stop trap (risk was 6.3× ATR, well
above the floor). `scalp_1m_outlier.py` then named the culprit:

    R        bars_held   outcome  entry    exit
    2942.7   1,939,865   open     16824.0  77197.0

**One trade, held for 1,939,865 bars** — a January-2023 entry marked out at
the September-2026 close. My engine exited unresolved trades at
`candles_1m[-1]` instead of at the hold cap, so `max_hold_min=240` was
decorative. The +2942.7R was arithmetic, not skill.

**Fixes applied, and they are permanent:**
- unresolved trades now close **at the cap** (`outcome="time_stop"`), never
  at the dataset end;
- `assert_hold_cap()` raises if any trade outlives the cap — it caught a
  second, off-by-one bug (`i + cap + 1` → `bars_held` 241) on the re-run;
- both the runner and the outlier script now call it.

This is HANDOVER §5 trap 1 in a new costume: *"a real harness printed avg
+19.4R, net +9700R before being caught."* The guard that would have caught
it — an unbounded-hold assertion — did not exist until it was needed.

## The real result (all 24 cells, 4/4 controls exact)

Trimmed mean, the Rule-13 judge. **IS is negative in 24/24 cells.**

| cell | IS net | IS trim | OOS net | OOS trim |
|---|---|---|---|---|
| mb10 decisive | −174.0 | −0.065 | +314.8 | −0.021 |
| mb10 b2 | −111.4 | −0.064 | +190.1 | −0.029 |
| mb10 flip | −134.3 | −0.068 | +190.6 | −0.021 |
| **mb10 b1** | −119.4 | −0.063 | **+864.4** | **+0.039** |
| mb20 b1 | −28.7 | −0.058 | **+706.6** | **+0.037** |
| mb40 b1 | +28.1 | −0.051 | +182.3 | −0.011 |
| mb40 b2 | +19.9 | −0.053 | +65.7 | −0.042 |
| *(champion lane; utcsat identical — both use sw10)* | | | | |

Shape is consistent everywhere: **WR ~35%, PF 0.98–1.06, avg ≈ −0.06R per
trade in IS.** 19,520 trades at −0.009R each. That is a coin flip with a
slightly adverse spread, not a trend system. 1m swing breaks carry no edge
on their own; the 15m book's edge lives in the *structure* of the 15m
swing, and that structure simply does not exist at 1m grind.

## Verdict

**The 1m scalping book as specified does not work. 0/24 cells clear the hit
bar**, and the reason is not the 1:2 target or the trail — it is that
PF ≈ 1.0 everywhere. No target or exit change fixes a book whose per-trade
expectancy is already zero. Do not retune `target_r` or `max_hold_min` on
this family.

## The one thing worth chasing

`b1` on 1m is the only cell whose **OOS trimmed mean is positive**:
`mb10 → +0.039` (+864.4R) and `mb20 → +0.037` (+706.6R), PF 1.147/1.142,
with the whole gain surviving ex-best-3/5 (+696.6R). That is materially
different from every other cell, and it is the *opposite* of the 15m B1
result (`B1_ENTRY.md`: B1 on 15m failed 4/4, WR 27.8%→17.2%).

It is **not** adoptable: its IS trimmed mean is −0.063, so it fails the
same-sign bar outright. But an era-flip on a *new* trigger that 15m never
had is worth one pre-registered follow-up — specifically, whether some
1m-specific state (not the R-threshold, not the time-threshold) separates
the OOS-positive B1 cohort. That is a new hypothesis, not a retune.

**NOTHING ADOPTED.** Production untouched. The 1m book is a research module
with no default that ships; the 15m champion is unchanged (controls exact
in all 4 cells).
