# `exp_mltf_green_r` — R-threshold on the 1m add-on: **FAILS 16/16. CLOSED.**

Date: 2026-09-28. Harness: `backtest/tests/exp_mltf_green_r.py`
→ `_mltf_green_r.json`. Path-true, no shared file edited, 169.7s.

## The question

HANDOVER §7 Phase 3. `exp_mltf` already ships in the champion and already
allows concurrent 1m add-ons. Stage 44 (`MARGINAL_PREENTRY_ATLAS.md`)
measured the green add-on cohort and found it profitable in all six cells
(champion **+109.6R IS / +42.2R OOS**), so the user's instinct was
validated. What was never run is the path-true **gate**.

`exp_mltf_green_r = k`: allow a new add-on only when the already-open
SAME-DIRECTION cohort is ≥ kR green at the decision instant. This is the
**R-threshold**, tested against the shipped **time-threshold**
(`exp_persist=7`). k = 0.25 / 0.5 / 1.0 / 1.5, pre-registered, all rungs
reported, none selected.

## Result: every cell loses, and it gets worse as k rises

| lane | k=0.25 | k=0.5 | k=1.0 | k=1.5 |
|---|---|---|---|---|
| is/champion | −17.7 | −52.7 | −52.4 | **−117.3** |
| is/utcsat | −19.9 | −53.5 | −58.4 | **−121.0** |
| oos/champion | −36.4 | −66.0 | −77.6 | −76.6 |
| oos/utcsat | −37.5 | −66.6 | −67.9 | −68.2 |

dNet vs the control book, same sign in all 16 cells. Monotone in k on both
IS lanes. **0/16.**

The gate is not inert — it blocks progressively more (champion IS 42 → 57 →
89 → 108 blocked) and the damage scales with the blocking. So this is a
real effect, not a no-op reading clean.

OOS is the worst part: at k≥0.5 both OOS lanes go **negative outright**
(oos/utcsat −6.4R, PF 0.965; oos/champion −7.5R, PF 0.958), and
**ex-best-5 is negative in 14 of 16 cells** — in OOS it is negative even at
k=0.25 (−3.6 / −10.2). The whole gain is the tail, and the gate removes
tail.

## Why this is a clean close, not a retune

1. **Controls exact.** All four reference ledgers reproduced to the trade
   before any arm was scored: 500t +325.8, 454t +358.9, 279t +70.2,
   253t +60.2.
2. **Same sign 16/16**, and monotone in k — no rung is hiding a pass.
3. **The interesting part is the SIGN of the finding.** Stage 44 said the
   green add-on cohort is *profitable in isolation*. This says **removing
   the non-green ones makes the book worse**. Both can be true, and the
   reconciliation is the cascade already documented in this repo
   (`AGENT_COORDINATION.md`, `BLEED_AUTOPSY.md`): under `exp_mltf` a
   removed entry frees concurrency, shifts the cooldown timeline and moves
   the loss streak, and that cascade is **3-5× the direct effect**. The
   blocked add-ons were not dead weight — they were occupying slots and
   suppressing worse replacements.

That is the same mechanism the wick work found by a different route
(skip −39.0R vs gray +28.1R), now confirmed on the add-on channel.

**Do not retry this as a threshold.** A different k cannot flip a monotone
16/16. If anyone wants to revisit add-on gating, the thing to test is
whether the *cascade* can be neutralised (a true GRAY that holds the slot
and advances the loss streak, Rule 18) — not a stricter entry filter. That
is a new hypothesis, not a retune of this one.

## Discipline

- **A real bug was caught by the run, not by reading.** First attempt
  crashed with `ValueError: invalid literal for int(): 'long'` — the
  engine stores `t["dir"]` as the string `"long"`/`"short"` (v18 line 725),
  not `1`/`-1`. Fixed to compare against `"long"`/`"short"`. Had I not run
  it, this would have shipped as a silent zero-gate.
- **Causality.** Marked R reads only *closed* 1m bars at the decision
  instant (`_now = ts+900`, price from `fine_ts` bisect) and only positions
  open at that instant. No trade's **final** R is ever read — the leak that
  shipped a false 4/4 once (`AGENT_COORDINATION.md` line 155).
- **R denominator** is each open trade's own `|entry − sl|`, held
  per-trade, never pooled. No cross-bucket comparison, so the
  stop-distance confound of HANDOVER §5 does not apply.
- **GRAY not skip (Rule 18).** The gate rejects a *new* entry before any
  state mutation. It cancels nothing, resizes nothing, frees no slot and
  resets no cooldown — so it cannot inherit the wick-gate failure mode.
  The cascade that hurt is the *engine's own* response to a missing trade,
  which is exactly the effect under test.

**NOTHING ADOPTED.** Production untouched, all flags default-off.
The shipped champion keeps `exp_mltf=True` with no R-gate.
