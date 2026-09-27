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
- **Byte-scan every text file before commit** - check BOTH U+FFFD and control
  chars `0x00-0x08, 0x0b-0x0c, 0x0e-0x1f, 0x7f` (exclude tab/LF/CR). FFFD-only
  missed three `\a`/`\b`/`\v` escape bugs that ate branch and path names this
  session. A pure-ASCII check subsumes the control-char scan for ASCII files;
  files with non-ASCII text (like this one) need the explicit scan.
  EOL companion check: match the file's COMMITTED style - inspect the HEAD blob's
  bytes (this repo is mostly LF; some files are legitimately mixed), never the
  working tree's: core.autocrlf=true smudges checkouts to CRLF, converts pure-EOL
  files on add but skips mixed ones, and skips stat-clean files (stale index wins).
  Measure bytes with a Python subprocess, never a PowerShell pipe (pipes rewrite CR).

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
- `wick_atr12@short < 6.026` (STRICT, 1h plane) - the standing gray candidate.
  **UPDATED 2026-09-27:** the 2026-09-26 "FAILS 0/4" retraction below was
  measured on a WRONG 15m predicate (cohort swap: 112 vs 74 flagged, opposite
  sign). Corrected status: gray 4/4 proven on the real 1h gate; HOLD on the
  forward gate (5/50). See "Wick 1h gate - corrected status" below.
- `flips96@short 4-5` also passes 4/4 but overlaps with the above (both
  short-side). Do not stack; combination untested. **Same lever, so the same
  fate is expected - not separately rerun.**
- **RESOLVED 2026-09-26 - worktrees created.** See Worktrees below.

## Removal retractions - post-process PASS does not mean real

**SCOPE CORRECTION (2026-09-27): every number in this section was measured on
the 15m-plane predicate - a DIFFERENT cohort from Stage B's actual 1h gate.
The 0/4 and the -78.6R cascade describe the wrong gate (112 flagged vs 74,
opposite cohort sign). The real 1h predicate under gray mode: cascade 0.00,
seq-identical 6/6, live dNet == post-process exactly. The RULE below (a
post-process removal is an upper bound) stands unchanged for true removals.**

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

## Wick 1h gate - corrected status (2026-09-27)

Predicate: shorts only, strict `wick_atr12 < 6.026` (Stage B `bucket_of`
semantics), computed on the 1h plane - 12 CLOSED 1h bars ending at j = last
1h bar closed by cutoff, ATR14 of the 1h TR series, j >= 50; wick_atr12 =
(sum of upper + lower wicks over the window) / ATR14-1h. Single-source
flagger: `exp_gray_wick1h.py` (4f97f90).

**Status: HOLD.** Gray mechanism proven: 4/4 cells (cascade 0.00,
seq-identical 6/6, live dNet == post-process exactly); cohort robust - best
trade dropped, still negative 6/6 at 6.026. Independent audit + two harness
fixes (c18ffbb, eb12934) reproduced Stage B with parity 4/4 EXACT to 1e-3
(74/-28.057, 62/-25.674, 35/-19.781, 36/-23.775), now a hard assert.

Corrected numbers (from `_wick1h_deep.json`, strict `<`):
- ck_u both-eras window: **5.0-5.4 | 5.6-6.4** - 14 steps, NOT contiguous;
  hole at 5.5 (is/utcsat +0.95). Record windows as blocks, never ranges.
- cliff 6.4 -> 6.5 (is/champion +24.59, is/utcsat +34.13 flip together);
  flip points IS 6.4/6.4/6.1, OOS 7.2/7.2/6.6 - IS is the binding constraint.
- all-6 window: **6.1 only**, -0.29R on n22 = one trade, post-hoc picked to
  make age10 pass - NOT a recommendation.
- age10: INSUFFICIENT DATA (n=20, sum_ex_best -3.875 = a single +5.9R winner;
  oos n=7), default-off. "Structural fail" RETRACTED - nested thresholds are
  the same cohort, not independent evidence.
- RETRACTED: "cohort worse than book avg at every threshold" (cumulative 1-D
  sweep over-read).

HOLD has ONE blocker: the forward gate (5/50 untouched). Threshold value is
NOT frozen (user: "let the result decide") - 6.026 sits inside the window and
is the only pre-registered, gray-validated candidate. Adoption path: forward
5/50 -> user ruling -> engine change (pravinx0). Nothing adopted.

House rules added this slice (5):
1. Stage B bucket predicates are STRICT `<` - `<=` adds a trade per IS cell
   and breaks parity (the audit's first failed control).
2. A control mismatch is a hard assert: abort BEFORE printing verdicts
   (c18ffbb reported every verdict off a failed control - do not repeat).
3. Nested-threshold sweeps reuse the same cohort - one observation, not N
   (the age10 "structural" error).
4. Windows/stable sets are recorded as blocks with holes explicit - never as
   `a-b` ranges that hide a gap.
5. **Verify before writing** - any number attributed to another agent is
   checked against source before it enters a doc (two wrong attributions in
   this slice, both caught only by reading the file).

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

## HTF plane is 1h and that is a fixed assumption (added 2026-09-27)

Tested and rejected the 2h parent plane. **2h loses 6/6** and the way it loses
rules out the easy explanation. See `docs/HTF_2H_PLANE_TEST.md`, log #104.

| Cell | 1h net | 2h net | 1h DD | 2h DD |
|---|---|---|---|---|
| is/champion | +325.8 | +49.4 | 27.7 | 60.6 |
| is/utcsat | +358.9 | +59.7 | 21.2 | 46.1 |
| oos/champion | +70.2 | **−55.8** | 53.2 | 95.2 |
| oos/utcsat | +60.2 | **−56.1** | 29.4 | 80.5 |

(age10 reported separately: +435.7→+184.4 IS, +43.2→+13.6 OOS. Default-off,
structurally different single-book strategy — not evidence about live lanes.)

The objection "2h is just coarser, of course it trades less" **fails**: trade
count barely moves (−3% to −9%; age10 OOS actually gained 3) while drawdown
roughly **doubles** and PF collapses toward 1.0, with both live lanes negative
out of sample. Same number of trades, twice the pain. 2h is not a quieter view
of the same signal — it selects a *different and worse* set of trades.

**Rule 1 — changing the HTF plane requires moving the close-time constant in
the same change.** `v18_streak_halt.py:269`
`candle_ts_htf_close=[t+3600 for t in candle_ts_htf]` is the gate that decides
which parent bar has CLOSED and may be read. Feed it 2h candles while it still
says `t+3600` and the engine reads every 2h bar **one hour before it closed** —
a lookahead leak, not a bias, and it produces plausible-looking numbers. A
plane shift without this is not an experiment, it is a leak with a chart
attached. (Six other 1h constants exist but are LTF-side — `ts+900` is the 15m
close, `2700` is the window bound — and correctly stay.)

**Rule 2 — treat 1h as structural, not tunable.** Do not propose 30m/2h/4h
parent variants as sizing or smoothing ideas. The plane is load-bearing.

**Rule 3 — RESOLVED 2026-09-27 (deep follow-up, log 105). The open question
above is now CLOSED: duration matching does NOT rescue 2h.** A 5-arm run
separated the two and the answer was the opposite of the worry — the first
write-up's unproven *reason* was wrong, its direction was right.

| Arm | Plane | lookbacks | HTF:LTF ratio | IS champ | OOS champ |
|---|---|---|---|---|---|
| C0 | 1h | full | 1.6× | +325.8 | +70.2 |
| A1 | 1h | **halved** | 0.8× | +328.2 | +71.1 |
| B0 | 2h | full | 3.2× | +49.4 | −55.8 |
| A2 | 2h | **halved** | 1.6× | +53.9 | −46.4 |
| A3 | 2h | swings halved only | 1.6× | +53.9 | −46.4 |

- **Duration is inert.** A1 ≈ C0 in both eras. Halving all six lookbacks on the
  1h plane moved champion +2.4R IS / +0.9R OOS — noise, slightly positive both
  times. A1 even inverts the ratio (parent swing *shorter* than LTF swing) and
  nothing breaks.
- **Resolution is the whole story.** A2 restores duration AND the 1.6× ratio and
  recovers nothing. Both 2h arms still collapse.
- **chop/garch/ent/detect are non-binding.** A2 and A3 are bit-identical.
  Falsified as a plumbing bug: absurd `lb` 2→400 leaves the book at
  `n=490 net=+53.8630` every time, while `_chop_series_1h(lb=14)` vs `lb=2`
  returns different series. Params reach the code; they just don't move trades.

**Rule 3a — the corrected reason, cite this instead of Rule 2's wording.** The
edge needs the parent sampled at **1h** and is **indifferent to lookback
duration** and to the chop/garch feature windows. Per-bar parent structure
(swing turns, chop transitions) carries the signal, and averaging the same
window to 2h destroys it. "1h is load-bearing because the lookbacks are tuned
for it" is **false** — the lookbacks are not what is tuned.

**Rule 3b — when two arms come out bit-identical, prove it is real.** A2 == A3
could have been dropped kwargs. It was not, and the proof is cheap: drive the
parameter to an absurd value and show the book does not move, *and* show the
callee it feeds returns a different series. Do not report an inert parameter as
a finding on one observation.

**Rule 5 — do not substitute a fresher download into a controlled comparison.**
Native Bybit 2h was fetched and diffed: `open/high/low` byte-identical on
24,970/24,971 bars (99.996%), but the venue had since revised 59 OOS closes and
the file ran 10 bars past the repo's 1h snapshot. Swapping it in would have
mixed a data-vintage change into a timeframe result and looked like an effect.
Cross-check the download; keep both planes on one snapshot. Also: `close`-only
divergence is the signature of a **revision**; misalignment corrupts
`high`/`low` too, so the field breakdown is the diagnostic that separates them.


**Rule 4 — data note.** The raw CSVs stamp 1h bars at `:30`; the loader
hour-aligns to the opening boundary. Bucket on the engine's convention. Of
16,218 (IS) / 8,761 (OOS) 2h buckets, exactly 2 per scope are dropped for
having a single leg, and both are the ragged **series edges** (bucket index 0
and the last) — zero interior gaps. An edge-drop is correct behaviour, not a
data defect; do not "fix" it by admitting half-formed 2h candles.


## Message log

- 2026-09-26 — Found lookahead leak in `enrich_sequential` (203 prior-open
  observations across 178 trades). Chain-based removals retracted 4/4 → 2/4;
  the two pure market-structure removals (`wick_atr12@short`, `flips96@short`)
  unaffected, byte-identical before and after.
- 2026-09-26 — Committed 5 slices: `.gitignore` hygiene, Stage B bleed study,
  integrity-test re-anchor, docs, harness suite + scripts. Production diffs
  deliberately left uncommitted.
- 2026-09-27 - Wick 1h gate: predicate mismatch found (Stage B qualified on
  the 1h plane; all follow-ups tested 15m - wrong cohort), gray re-test PASS
- 2026-09-27 - HTF plane 1h -> 2h: first test that changed the PLANE rather than
  the flag or the size. 2h loses 6/6; both live lanes go negative OOS
  (+70.2 -> -55.8, +60.2 -> -56.1) with DD roughly doubling while trade count
  holds, so 2h picks worse trades rather than fewer. 1h is now a fixed
  structural assumption. Found the causality trap: `candle_ts_htf_close` at
  v18:269 must move with the plane or the engine reads 2h bars an hour early.
  Runtime patch only, `backend/` clean. See "HTF plane is 1h" above and
  `docs/HTF_2H_PLANE_TEST.md`.

  4/4 (4f97f90), ruling brief (b7be019), independent audit + two harness
  fixes (c18ffbb, eb12934). HOLD on the forward gate (5/50) only; age10 =
  insufficient data; threshold not frozen; nothing adopted. See "Wick 1h
  gate - corrected status" above.
- 2026-09-27 - HTF plane deep follow-up: fetched Bybit native 2h to cross-check
  our resampled plane (open/high/low byte-identical on 99.996% of bars; residue
  is close-only venue revisions = data vintage, and substitution was declined
  to keep both planes on one snapshot). Then a 5-arm run separated lookback
  DURATION from bar RESOLUTION, closing the open question from the first HTF
  write-up. Duration is inert (halving all six lookbacks on the 1h plane moves
  champion by +2.4R IS / +0.9R OOS); resolution is the whole story (2h still
  collapses at matched duration and matched 1.6x ratio). chop/garch/ent/detect
  proven non-binding by falsification, not assumption. 1h confirmed, 2h
  rejected on a different ground than first stated. No adoption; engine stays
  1h/min_bars 20. See "HTF plane is 1h" above and
  `docs/HTF_2H_PLANE_TEST.md`.
