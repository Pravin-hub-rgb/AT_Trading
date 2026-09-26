# Pyramid / Scale-in - Phase 2 Design (variant list first)

> Created 2026-09-26. Phase 1 (CHECKLIST 24.43, LOG 36,
> `exp_pyramid_walk.py`) was an OFFLINE 1m winner-path walk: adds at
> 0.5R/1R/2R milestones, 0.5x base risk, add-SL = add-price -/+ 1R, add
> exits at add-SL or base exit. Result: 1/6 cells pass (champion 0.5R
> IS +7.6 / OOS +10.1) but FRAGILE - without the single best trade IS
> becomes -11.3 and OOS -4.1; median add -0.55R, win rate 22-29%,
> incremental DD 37R IS / 20R OOS. Verdict then: thin pass, not robust,
> Phase 2 (engine kwargs) NOT designed. This document is that design.
> **Nothing here is run or approved - this is the pre-registration
> proposal; the variant list is frozen before any code is written.**

## 1. What Phase 2 must answer

1. Does the Phase-1 thin cell survive in the REAL engine (15m bars + fine
   1m exits, real entry/exit mechanics) rather than the offline walk?
2. Does it survive a robustness gate that Phase 1 failed (single-best-trade
   dependency)?
3. Is the failure mode (median add = small loser, rare payoffs) fixable by
   a pre-registered variant (add-SL rule / trigger family), or is the
   family structurally thin?

## 2. Engine mechanics (the actual design choice)

Engine: `backend/src/btc/engines/htf_ltf/v18_streak_halt.py`,
`simulate_htf_ltf_streak_halt` - single fill per trade
(`ltf_trades.append` at line 723), exit walk with SL ratchet + fine 1m
resolution, `busy_until` blocks the next entry until exit (single-slot
semantics per base config).

| Model | Mechanism | Verdict |
|---|---|---|
| **A - child trades (RECOMMENDED)** | While a parent is open, each add-trigger creates a CHILD trade entry (own risk = 0.5x base, own SL = add-price -/+ 1R) recorded with a `parent_trade_no` link; child exits at its add-SL or at the parent's exit, whichever first. Child does NOT touch `busy_until`, does NOT consume a new slot, does not change which base entries fire. | Faithful to Phase-1 rules; identity-safe (off = byte-identical); no Study-1 cascade risk. |
| B - size multiplier on the parent | Adds fold into parent size; one combined exit | Rejected: cannot represent Phase-1's independent add-SL exit (adds would ride the parent's trail); changes r_multiple semantics of existing rows. |
| C - full independent second position | Child consumes a concurrent slot (busy_until accounting) | Rejected for Phase 2: changes WHICH trades fire (cascade class under exp_mltf, Study-1 lesson); conflates pyramid with concurrency research. If pyramid ever ships, live re-check = revisit C. |

New default-off kwargs (same `exp_*` research-flag pattern already in this
file: `exp_trail_half`, `exp_skip_decisive`, `exp_window_win_kill_*`):

- `exp_pyr_trigger` - None (off) | "r_mile" | "swing_confirm"
- `exp_pyr_levels` - tuple of R-milestones, default (0.5, 1.0, 2.0)
- `exp_pyr_size` - child risk fraction, default 0.5
- `exp_pyr_slr` - add-SL distance in R, default 1.0; `exp_pyr_sl_mode`
  = "fixed" (Phase-1) | "none" (ride parent exit)

**Ownership note:** these are edits to the shared engine file. They follow
the established default-off research-flag pattern, but per AGENT_COORDINATION
the engine is shared - explicit user go-ahead required before the code edit.

## 3. Pre-registered variant list (frozen now, all arms reported)

Lanes = Phase-1 lanes: champion_multi_sw10, utcsat_multi_sw10,
age10_dirmatch_swingpause_single_sw10; FLAT books (comparability with
Phase 1); scopes IS + OOS.

| # | Trigger | Add-SL | Levels | Role |
|---|---------|--------|--------|------|
| V0 | - | - | - | base reference (ledger assert) |
| V1 | r_mile | fixed 1R | (0.5, 1.0, 2.0) | Phase-1 parity arm (walk -> engine) |
| V2 | r_mile | fixed 1R | (0.5,) only | primary candidate (Phase-1's only passer, tail capped at +1 add) |
| V3 | r_mile | none (ride parent) | (0.5, 1.0, 2.0) | isolates the add-SL (is it cutting the payoffs?) |
| V4 | swing_confirm (fresh 15m swing in trade direction while open) | fixed 1R | max 3 adds | genuinely new trigger (backlog's suggestion) |

Sizing stays 0.5x in every arm - no size search (overfit surface; 0.5x was
Phase-1 pre-frozen).

## 4. Gates (written before the run)

- Identity: `exp_pyr_*` off -> byte-identical to shipped (gate + smoke +
  `test_v18_causal_integrity`).
- Controls: base ledgers asserted (flat refs); V1 vs Phase-1 walk numbers
  = PARITY check (directional + magnitude band, NOT bit-exact - different
  mechanics); abort if base ledgers fail.
- **PASS per arm = dNet > 0 AND curve_better TRUE in ALL 6 cells (3 lanes x
  2 eras) vs the flat book.**
- **ROBUSTNESS gate (the Phase-1 lesson, pre-registered): the arm's IS and
  OOS dNet must keep the SAME SIGN after dropping the single best trade of
  the arm's delta book. Fail = fragile, not adoptable regardless of the
  6/6 result.**
- Kill criterion: if no arm passes both gates, the family is CLOSED
  (backlog checkbox done: "tested, fragile/thin - closed").
- RESEARCH_POLICY: report all arms; no automatic adoption; sizing exemption
  does NOT apply here (adds change the book - this is engine-path work).

## 5. Runtime / effort estimate

Engine walk edits (child creation + child exit handling in the exit loop) =
the bulk; harness mirrors `exp_n3_stack.py` structure (controls + arms +
verdict). 5 arms x 3 lanes x 2 scopes = 30 engine runs (~5-10 min) plus
identity/smoke. One commit, CHECKLIST 24.85 / LOG row 90 (next numbers at
time of writing).

## 6. Open questions for the user

1. Go ahead with Model A + the 5-arm list as frozen above?
2. Engine edit = default-off research flag in shared file - approve?
3. Alternative: run V1 parity only first (cheapest kill test - if the engine
   can't reproduce the walk's thin cell, stop there), then decide on V2-V4?
