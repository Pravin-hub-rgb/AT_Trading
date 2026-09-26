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
- Worktrees for both agents have not been created yet. Until they are, assume
  every working-tree change may belong to the other agent.

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

## Causality rule (added after the Stage B retraction)

Any feature built from **prior trade outcomes** must count a trade only when
`exit_ts <= candidate entry_ts`. Folding final net R at entry order leaks
lookahead whenever positions overlap (`exp_mltf=True`, `busy_until`).

This exact bug shipped a false "4/4 PASS" once. See
`verify_bleed_causality.py` and `BLEED_AUTOPSY.md` §9.9. Run a closed-only
audit before trusting any chain- or streak-state feature.

## Message log

- 2026-09-26 — Found lookahead leak in `enrich_sequential` (203 prior-open
  observations across 178 trades). Chain-based removals retracted 4/4 → 2/4;
  the two pure market-structure removals (`wick_atr12@short`, `flips96@short`)
  unaffected, byte-identical before and after.
- 2026-09-26 — Committed 5 slices: `.gitignore` hygiene, Stage B bleed study,
  integrity-test re-anchor, docs, harness suite + scripts. Production diffs
  deliberately left uncommitted.
