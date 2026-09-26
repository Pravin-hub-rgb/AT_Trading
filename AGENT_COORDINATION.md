# Agent Coordination — experiments/v19-plus

Created 2026-09-26 after two agents converged on one working tree.

## Shared-tree rules

- **Never `git add -A`.** Stage explicit paths only; use `git add -- <paths>`.
- **Check `.git/index.lock`** before every `git add` / `git commit`.
- One logical slice per commit. Verify with `git diff --cached --name-only`
  *before* committing.
- Validate before committing (`py_compile`, `pytest`); `git diff --check` after.
- Run research with **Python 3.12** — default `python` is 3.10 and lacks pandas:
  `C:\Users\Pravin\AppData\Local\Programs\Python\Python312\python.exe`

## Ownership

| Path | Owner |
|---|---|
| `backend/src/btc/engines/htf_ltf/v18_streak_halt.py` | other agent (production engine) |
| `backend/src/live/persistent_swing.py` | other agent (live) |
| `live_stuff/live_loop.py` | other agent (live) |
| `live_stuff/replay_harness.py` | other agent (live) |
| `live_stuff/tests/**`, `live_stuff/docs/**`, `scripts/**` | this agent (research) |

Production/live diffs are **not** committed by the research agent, even when they
compile. Their owner confirms intent and stages them.

## Open questions

- Are the production diffs (`v18_streak_halt.py` +195, `persistent_swing.py`
  +147, `live_loop.py` +95) finished and intentional? Uncommitted.
- `wick_atr12@short <= 6.03` — the standing candidate. Post-process removal
  only; engine untouched. Adoption needs a path-true engine rerun, since a
  post-process skip does not account for chain re-timing.
  **RESOLVED 2026-09-26 - RETRACTED, the rerun was run and it FAILS 0/4.**
  See the "Removal retractions" section below.
- `flips96@short 4-5` also passes 4/4 but overlaps with the above (both
  short-side). Do not stack; combination untested. **Same lever, so the same
  fate is expected - not separately rerun.**
- **RESOLVED 2026-09-26 - worktrees created.** See Worktrees below.

## Removal retractions - post-process PASS does not mean real

Stage B's 2 surviving removals were **retracted 2026-09-26** after a path-true
rerun. `exp_wick_short_pathtrue.py` patches the same super-set `build_module()`
builds, rejecting the entry *before* any state mutation (immediately after
`i=ltf_store.pos(bar_time)`, ahead of `busy_until` / cooldown / streak-halt / book).
Identity gate IDENTICAL in all 4 cells, so the numbers are trustworthy.

| cell | n | dNet path-true | dNet post-process | maxDD | curve |
|---|---|---|---|---|---|
| is\|champion | 500->389 | **-50.6** | +28.1 | 27.7->27.2 | FAIL |
| is\|utcsat | 454->362 | **-54.5** | +25.7 | 21.2->**24.7** | FAIL |
| oos\|champion | 279->216 | **-78.0** | +19.8 | 53.2->**57.6** | FAIL |
| oos\|utcsat | 253->198 | **-59.6** | +23.8 | 29.4->**31.4** | FAIL |

OOS champion goes **negative** (+70.2 -> -7.8); OOS utcsat goes to zero.
0/4 pass, every cell fails `curve_better`, maxDD worsens in 3 of 4.

This is the Study-1 cascade in full force: deleting a trade from a *finished*
ledger while the engine kept behaving as if it existed freed `busy_until` slots,
shifted the cooldown timeline and the loss streak, and that cost more than the
removed losers returned.

**Rule:** no removal candidate is adoptable on a post-process ledger skip under
`exp_mltf=True`. A post-process dNet is an UPPER BOUND. Rerun path-true first.

**Magnitude of the trap (computed, never by hand).**
Derived by `exp_wick_cascade_decomposition.py` -> `_wick_cascade_decomposition.json`
(no engine run; pure arithmetic over the two artifacts). Split each cell into
direct effect and cascade: cascade = dNet_path_true - dNet_postproc, where
dNet_postproc = -cohortR (removing a losing cohort *gains* R).
| cell | cohort R | dNet post-proc | dNet path-true | cascade | cascade / direct |
|---|---|---|---|---|---|
| is\|champion | -28.1 | +28.1 | -50.5 | **-78.6** | 280% |
| is\|utcsat | -25.7 | +25.7 | -54.5 | **-80.2** | 312% |
| oos\|champion | -19.8 | +19.8 | -78.0 | **-97.7** | 494% |
| oos\|utcsat | -23.8 | +23.8 | -59.6 | **-83.4** | 351% |
The direct effect was **correct and positive in all 4 cells** - the cohorts
really were losing money, so the descriptive FIND was sound. But the cascade is
**3-5x the direct effect**: it does not merely eat the gain, it overwhelms it.
Slot-blocking under exp_mltf is therefore not a tax on removals, it is larger
than the edge being removed. That is the quantitative case for the sizing pivot
below instead of more removal work.
The signs here are easy to get wrong - a hand-typed version of this table put
the cohort R into the dNet column and understated the cascade as 45-75% of the
total instead of 125-156%. Derive these numbers in the harness.

## Causality rule (added after the Stage B retraction)

Any feature built from **prior trade outcomes** must count a trade only when
`exit_ts <= candidate entry_ts`. Folding final net R at entry order leaks
lookahead whenever positions overlap (`exp_mltf=True`, `busy_until`).

This exact bug shipped a false "4/4 PASS" once. See
`verify_bleed_causality.py` and `BLEED_AUTOPSY.md` §9.9. Run a closed-only
audit before trusting any chain- or streak-state feature.

## Sizing exemption - post-process IS path-true here (added 2026-09-26)

The removal rule above does **not** apply to position sizing. Sizing changes R
*per trade*, never *which trades are taken*, so the trade list is identical and
a post-process sizing number is a real measurement, not an upper bound. No
engine rerun is needed to evaluate a sizing arm. Three conditions, all verified:

1. **The loss streak counts losses, not R** - `v18_streak_halt.py:714` reads
   `if r_multiple <= 0`. A positive size multiplier preserves every sign, so no
   entry is added or dropped.
2. **No R-aggregate gate is live in champion.** `window_r_cap` and
   `campaign_require_marked_r` do not appear in `experiment_registry.py`.
3. **The engine has no equity / size / notional state at all** - 0 hits for
   `equity`, `position_size`, `notional`, `qty`, `size_mult` across all 782
   lines of `v18_streak_halt.py`. There is no channel for a size change to feed
   back into trade selection.

**Caveat that voids the exemption:** `exp_campaign_require_marked_r` *exists* in
the engine (`test_experiments_craze.py:839`) and is swept by six test-only arms
in `exp_thesis_campaign_policy.py`. It is **default-off and not adopted**. If any
R-aggregate gate is ever turned on, sizing starts feeding back into selection
and every sizing result above must be re-run path-true.

`CHECKLIST.md` 24.58 says "sizes ARE engine state" and asks for a path-true M2
arm. That caution is superseded for the champion config by the three checks
above; it would still apply to a config carrying an R-gate.

## Sizing arms, re-read under the exemption (2026-09-26)

Existing artifacts, no rerun. All are sizing, so all are valid as they stand.

| arm | flag | dNet IS | dNet OOS | curve |
|---|---|---|---|---|
| **M2** `champion` | `cur_mag_atr >= 3` x1.5 | **+153.5** | **+31.5** | pass both |
| **M2** `utcsat` | same | +131.0 | +30.8 | pass both |
| **M2** `age10` | same | +117.1 | +18.8 | pass both |
| Z `champion_C` | regime-structure C | +106.5 | +32.2 | pass both |
| Z `utcsat_C` | regime-structure C | +112.3 | **+40.4** | pass both |
| Z `champion_D` / `utcsat_D` | regime-structure D | -71.5 / -67.2 | +10.8 / +23.4 | IS FAIL |
| htf-break A | - | +23.9 | +36.6 | pass both |

M2 is the strongest and the only one that passes every lane and both eras.
`regime_structure` arm C is second and passes both lanes. Arms D fail IS.
**`monster_sizing` M1 is a LEVERAGE TRAP - do not adopt** (flags 71-88% of the
book; its gain is 1.5x leverage, not selection - CHECKLIST 24.58).

None of this is adopted. The forward verdict is still sample-size blocked
(n >= 50 pre-registered, 5 trades untouched so far), and no sizing arm has
been forward-tested.

## Worktrees (created 2026-09-26)

Two agents no longer share a working tree. Created at 36fb506 and
fast-forwarded to the integration tip; re-sync with `git merge --ff-only`.

| path | branch | owner |
|---|---|---|
| C:/Users/Pravin/Desktop/main/AT_Trading | experiments/v19-plus | integration only |
| C:/Users/Pravin/Desktop/main/AT_Trading.worktrees/research | agents/research | research agent |
| C:/Users/Pravin/Desktop/main/AT_Trading.worktrees/live-engine | agents/live-engine | live/production agent |

**data/ and backend/venv are gitignored**, so a fresh worktree has neither
and every harness would fail on a missing CSV. Both are NTFS junctions into the
main tree (no copy, no duplicate disk). Recreate them if a worktree is ever
removed:

    New-Item -ItemType Junction -Path <worktree>/data -Target <main>/data
    New-Item -ItemType Junction -Path <worktree>/backend/venv -Target <main>/backend/venv

Junctions are ignored, so they do not dirty git status.

**How to work now.** Each agent commits on its own branch and never edits the
other agent's worktree. Merge into experiments/v19-plus deliberately - not by
editing files in the main tree. If you find yourself reading a file the other
agent has uncommitted, that is the old workflow; stop and check the branch.

## Message log

- 2026-09-26 — Found lookahead leak in `enrich_sequential` (203 prior-open
  observations across 178 trades). Chain-based removals retracted 4/4 → 2/4;
  the two pure market-structure removals (`wick_atr12@short`, `flips96@short`)
  unaffected, byte-identical before and after.
- 2026-09-26 — Committed 5 slices: `.gitignore` hygiene, Stage B bleed study,
  integrity-test re-anchor, docs, harness suite + scripts. Production diffs
  deliberately left uncommitted.
