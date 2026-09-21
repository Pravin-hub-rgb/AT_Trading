# ANCHOR BASIS AUDIT — D3 pre-live audit (2026-09-20)

Independent audit of the v18 base anchor (the foundation every experiment sits on).
Findings, fixes, and the exact reproduction matrix. Audit scripts kept in
`live_stuff/tests/exp_*_cline.py` for re-runs.

## 1. The two valid anchor bases (2x2 reproduction matrix)

| fills      | chop |  n | gross    | DD   | WR    | status |
|------------|------|----|----------|------|-------|--------|
| coarse 15m | 61.8 | 340 | +225.3R | 27.1 | 30.0% | identity-gate basis (test_experiments_craze) |
| coarse 15m | 58.0 | 351 | +211.7R | 23.4 | 27.6% | valid but unused |
| fine 1m    | 58.0 | 351 | +238.0R | 23.4 | 27.6% | **production basis** (all experiments, NET +148.0) |

- The old `_shipped_sw20` pin `{n:351, gross:225.3}` was an IMPOSSIBLE hybrid
  (n from fine+58, gross from coarse+61.8) and always FAILed. Split into
  `_shipped_coarse_618` and `_shipped_fine_58` (see experiment_registry.py).
- Fine fills change EXIT timing only — entry sets are identical between
  fine and coarse (verified: 0 entry-signature diffs).

## 2. Causality: CLEAN (no lookahead)

Truncation probe — truncate all data (chains rebuilt, fine data cut) at time T;
every pre-T trade must still exist with identical R:

| probe                        | cut 1 (2025-06) | cut 2 (2026-03) |
|------------------------------|-----------------|-----------------|
| anchor (shipped, BP, fine)   | 233/233 exact   | 307/307 exact   |
| champion multi sw10          | 318/318 exact   | 435/435 exact   |

Swing chains (15m mb50 + 1h mb20) and the signal stream are byte-identical on
the prefix between full-history and truncated data. C14 (closed-1h chop gate)
and C15 (+2700 knowable-instant window gate) verified present and effective.
v7_timecap walk: forward-sequential, cap entry-relative, SL-before-target
same-bar (conservative).

## 3. Trail ratchet — FIXED & ADOPTED (2026-09-20): condition + ordering

Two-part fix, both applied to `v18_streak_halt.py` (coarse AND fine loops):

1. **Condition fix**: the ratchet applies whenever the candidate is beyond the
   current stop — the old `cand < lo` guard DROPPED events whose activation bar
   had already traded through the new level (structural optimism; live cannot
   escape the dip).
2. **Ordering fix**: the ratchet applies BEFORE the SL check within each bar —
   the stop is armed at the activation instant (bar open) and the same bar is
   enforced against the new level. (The condition fix alone left a one-bar lag.)

**The entire champion optimism was exactly 2 trades** — t462 + t463, two
overlapping mltf shorts (2026-05-27/28) that both escaped ONE bounce on
**2026-05-28 23:15-23:16 IST** (down-swing origin 73588.90 confirmed 23:00;
breach mid-minute). Audit trail of t462's exit, each stage verified:

| engine state | exit | R | why |
|---|---|---|---|
| pre-fix (event dropped via 1m-range peek) | 2026-06-07 @ 61992.8 | +31.36 | needed the activation minute's FULL range to decide — un-implementable live |
| condition-only fix | 2026-05-28 23:16 @ 73656.5 | +4.887 | stop armed one bar late |
| **condition + ordering (final)** | **2026-05-28 23:15 @ 73588.90** | **+5.041** | armed at open, filled AT the level |

Design ruling tested and closed: "skip swings already breached at confirmation"
(strict open-based validity) was implemented and compared — **0 of 500 trades
differ** from the always-ratchet rule, because at every decision instant the
level was either valid (apply -> correct stop) or gapped (never occurs here).

Post-fix re-pin (all verified by re-run; pins exact in experiment_registry.py):

| run | pre-fix | post-fix (ADOPTED) | delta |
|-----------------|----------------------|--------------------|-------|
| anchor fine+58 | 351t +238.0 / +148.0 N | 351t +211.6 / +122.0 N | -26.5R |
| champion sw10 | 500t +486.3 / +366.1 N | 500t +445.2G / **+325.8 N** / DD 17.8 | -40.3R |
| champion sw20 | 487t / +232.6 N | 487t +322.7G / +208.4 N | -24.2R |
| single sw20 | 371t +104.0 N | 372t +180.5G / +90.1 N | -13.9R |
| single sw10 | 395t +95.9 N | 396t +178.3G / +82.0 N | -13.9R |
| baseline sw20 | 371t +148.2 N | 372t +212.8G / +122.3 N | -25.9R |
| baseline sw10 | 394t +163.6 N | 395t +233.0G / +137.7 N | -25.9R |

Note: the coarse+chop61.8 identity anchor (340t/+225.3R) is UNCHANGED by both
fixes — that trade set never hits the drop/ordering cases — so all historical
coarse-basis docs remain valid. Trade counts shifted by +1 on the
single/baseline configs (halt/cooldown sequencing cascade). DDs unchanged.

## 3b. 1h HTF side — no trailing, nothing to fix (verified 2026-09-20)

The HTF window walk (`v7_timecap.py`) is called by v18 with `trailing="off"` and
`breakeven_r=0.0` on all three tracks (flip/decisive/b2, v18 lines 94-96):
fixed SL at the swing pivot, fixed 3R target, 16-day cap — NO ratchet exists on
the 1h side. The v7 ratchet code (the same `cand < lo` pattern) is behind
`elif trailing=="swing"` and events are only built in that mode -> DEAD CODE in
this pipeline; the D3 bug is structurally impossible there. Same-bar ordering on
the 1h side is conservative (SL checked before the 3R target). Empirical proof:
the coarse identity anchor (340t/+225.3R, full 1h HTF walk) is byte-identical
before and after the engine fix.

NOTE: v7's dead trail block is deliberately left unfixed — v7 is shared by other
historical lanes that may pass trailing="swing"; touching it would silently
change those legacy numbers. Do not enable v7 trailing without auditing this.


## 3c. Robustness probes on the final champion (2026-09-20, post-fixes)

- **1m data gapless**: 1,945,711 fine bars, ZERO missing minutes, largest gap 0.
  The walk never jumps a hole; no gap-hidden SL risk.
- **Cost stress** (champion +445.2G): x1.5 fees = +277.8N; x2 = +229.8N;
  x3 = +133.8N; x3 fees + x3 funding = +86.9N. Breakeven ~4.4x assumed costs.
- **Concurrency cap** (greedy entry-order post-filter): cap5 = 499t +446.2R
  (BETTER than uncapped — cuts one bad overlap); cap4 +442.7; cap3 +434.0;
  cap2 +404.4; cap1 +293.2. Live can cap 4-5 positions at zero edge cost.
- **No stale trades**: outcomes = {sl:187, trail:313}; last trade closes
  2026-09-09, before data end (2026-09-13).

## 4. min_bars_15m = 50 (docs once said 35 — wrong)

The 15m chain length is the most sensitive knob in the system:
mb35 -> 437t / +58.3R (collapse) vs mb50 -> 351t / +238.0R (production).
Guard added in run_experiment.py (hard assert on drift).

## 5. Cost model re-verified

fee 0.055%/side (entry+exit notional / risk), slip 0.5bp entry + 1bp exit / risk,
funding bars/32 x 0.01% x (entry/risk) = 0.01%/8h hold-weighted.
Champion totals: 96.0R fee+slip + 24.2R funding = 120.2R.

## 6. Bookkeeping fixes applied (2026-09-20)

0. **Trail-event drop fix APPLIED to the engine** (`v18_streak_halt.py`, both
   loops — see section 3). All champion/baseline pins re-pinned to post-fix
   values. Champion multi sw10: +366.1 -> **+325.5R NET / DD 17.8**.

1. Registry: `_shipped_sw20` hybrid pin split into `_shipped_coarse_618` +
   `_shipped_fine_58` (both pin-OK, verified by re-run). The old `_shipped_sw15`
   row was removed: the runner fixes the LTF chain at sw15 (mb50) and
   `cfg["swing"]` selects only the HTF window chain, so a sw15 row is not
   expressible — and `_shipped_coarse_618` IS the craze identity twin
   (340t/+225.3R, verified identical to the gate).
2. Runner: identity gate runs before ANY experiment (patched-off must equal
   shipped exactly, coarse+61.8 basis; hard-fail on divergence).
3. Runner: hard asserts on min_bars_15m=50 / min_bars_1h=20.
4. Runner: every result row labeled with fill basis + effective chop
   (`fine/c58.0` style) in evaluate()/format_row().
5. test_experiments_craze.main(): removed dead `build_module(split_mb=True)` /
   `build_module(momentum=True)` constructor kwargs (crashed after the
   superset-patcher refactor); both phases now run via runtime kwargs.
