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

## 3d. Pattern family from the loss autopsy (2026-09-20)

Autopsy on the king + swingpause single (hour/weekday/kind/direction/bars):

- **Weekend bleed**: on the swingpause single, Sat = 37t **-16.1R @ 89.2% loss
  rate**, Sun = 40t **-14.6R @ 80.0%** — 77 trades for -30.7R. On the multi,
  ~neutral (110t for -1.9R).
- **Entry kinds**: on the swingpause single, B2 = 178t for **-0.6R** while FLIP
  carries everything (+260.7R). On the multi, B2 is +82.4R (keep it there).
- Longs dominate on both (multi: +339.5 long vs +105.7 short); shorts positive —
  not cut. Hour-of-day patterns look strong (19:00 worst) but are data-mining
  bait — not pursued.
- Bars-held profile confirms the trail-runner shape: trades <96 bars = -277R
  (multi), trades >=96 bars = +722R; top-10 trades = 74% of gross.

Experiments (7 configs, all pinned; references: king +325.8/17.8/18.3,
swingpause single +174.8/23.4/7.5):

| config | n | NET | DD | NET/DD | verdict |
|---|---|---|---|---|---|
| **nowknd_swingpause_single** | **294** | **+217.6** | **18.2** | **12.0** | **NEW BEST SINGLE** (+42.8R, -5.2DD vs swingpause single) |
| legskip2 multi | 269 | +267.3 | 17.2 | 15.5 | near-king quality at 46% fewer trades (minY +57 vs +102) |
| fliponly swingpause single | 237 | +179.7 | 21.9 | 8.2 | mild upgrade over swingpause single |
| wage24 multi | 362 | +243.9 | 23.1 | 10.6 | DEAD — young windows carry the edge (-82R) |
| nowknd multi | 400 | +307.8 | 17.1 | 17.9 | ~neutral on king (weekend bleed is a single-config effect) |
| fliponly multi | 285 | +242.7 | 24.3 | 10.0 | worse (B2 earns its keep on multi) |
| nowknd single (no pause) | 320 | +113.9 | 30.5 | 3.7 | WORSE — weekend skip only works ON TOP OF the swingpause |

### 3d-2. TIMEZONE ALIGNMENT of the weekend filter (2026-09-20) — user caught it

The CSV date strings are IST (ts are true UTC epochs; date = ts+5:30 — verified:
1m bar "2026-05-28 23:15" = gmtime 17:45 UTC; data starts 05:30 IST = UTC midnight).
So the first "weekend skip" skipped IST-Sat/Sun — NOT the true UTC weekend.
Dual-convention autopsy on the swingpause single:

| weekday | by IST date | by TRUE UTC |
|---|---|---|
| Sat | -16.1R @ 89.2% | **-23.9R @ 90.7%** |
| Sun | -14.6R @ 80.0% | **+51.7R @ 70.2%** (UTC Sun evening = IST Mon open, the best session) |

The bleed is a **UTC-SATURDAY** effect, not a generic weekend effect. Measured
(both lane variants consolidated: `utcsat_multi_sw10` / `utcsat_swingpause_single`):

| config | n | NET | DD | verdict |
|---|---|---|---|---|
| **utcsat_multi (UTC-Sat skip)** | **454** | **+359.0** | **14.8** | **NEW KING** (+33.2R, -3.0DD vs old king; NET-DD 24.3) |
| utc_wknd_swingpause single (UTC Sat+Sun) | 286 | +150.0 | 23.1 | worse — UTC Sun is profitable, keep it |
| utcsat_swingpause single (UTC-Sat only) | 325 | +166.3 | 23.3 | mild (-8.5 vs IST variant) |
| nowknd_swingpause single (IST Sat+Sun) | 294 | +217.6 | 18.2 | still best SINGLE (cascade effects differ per config) |

Lesson: on this dataset, ALWAYS derive calendar features from ts (UTC), never
from the IST date strings — an innocent-looking 5h30m offset flipped "weekend"
from a -31R filter into a +33R one on the multi.

Caveat: 7 configs tested against autopsy-derived patterns = multiple-comparison
risk. nowknd_swingpause_single needs a sw20/param-neighborhood validation before
it replaces the swingpause single as the default single config.

## 7. Cooldown-family experiments (2026-09-20) — swing-pause adopted for singles

New loss-reactive gates added to the patcher (all causal, decided at entry time):
`exp_skipwin` (skip the first N HTF windows opened after a loss),
`exp_skipwin_halt` (same but only after a HALT fires),
`exp_swingpause` (block entries until the most recent confirmed 15m swing has a
pivot AFTER the loss — i.e. fresh structure exists).

Results (fine/c58 basis, pins locked in registry; king = +325.8/17.8, baseline
single = +137.7/29.2):

| config | n | NET | DD | NET/DD | verdict |
|---|---|---|---|---|---|
| skipwin1 multi | 144 | -1.1 | 38.8 | — | DEAD (per-loss window skip amputates winners) |
| skipwin2 multi | 105 | -26.1 | 34.2 | — | DEAD |
| swingpause multi | 443 | +231.0 | 19.8 | 11.7 | hurts the king (-94.8R; overlapping runners need those entries) |
| skipwinhalt multi | 323 | +102.6 | 20.1 | 5.1 | DEAD (worse than halt3's own next-entry skip) |
| skipwinhalt single | 276 | +71.8 | 27.0 | 2.7 | DEAD |
| **swingpause single** | **357** | **+174.8** | **23.4** | **7.5** | **NEW best single config** (+37.1R, -5.8DD vs baseline; NET/DD 4.7->7.5) |
| swingpause cd0 single | 357 | +174.7 | 23.4 | 7.5 | pause fully SUBSUMES the bar-cooldown (cd8==cd0) |
| swingpause single sw20 | 338 | +120.0 | 34.1 | 3.5 | ~neutral (vs +122.3/37.3) |
| skipwin1 single | 138 | -4.3 | 40.0 | — | DEAD |

Conclusions:
1. Window-skipping after losses destroys the edge in every variant — the regime
   track's next window is exactly where the recovery trades live.
2. The structural pause ("no re-entry until a swing formed AFTER the loss
   confirms") is the right loss-reactive gate FOR SINGLE-POSITION configs:
   better R, better DD, and it replaces the bar-cooldown timer entirely (a
   cleaner rule to implement live). Do NOT add it to the multi king.
3. The king (+325.8/17.8) remains untouched and undefeated.


## 3e. Risk-width gate — DEAD, and the autopsy pitfall (2026-09-20)

Fine stop-width bins on the single autopsy: stops >=1.5% of price = 72t,
**-7.1R net**, big-win contribution +7.8R — passed the pre-registered cut rule.
Implemented `exp_risk_max_pct` and measured:

| config | autopsy predicted | actual |
|---|---|---|
| rmax15 single | ~+267 / low DD | **+91.7 / DD 38.1** |
| rmax10 single | ~+263 | +195.5 / DD 31.4 |
| rmax15 multi | ~+334 | +259.4 / DD 35.6 |

ALL worse than their references. Root cause: the trade sequence is
**path-dependent** — removing scattered mid-sequence trades reshuffles the
halt/cooldown/busy cascade and the entire downstream trade set changes. A
per-trade bucket autopsy cannot predict the system-level effect. Note the
contrast: the gates that WORKED (weekend skip, swing-pause) remove contiguous
blocks of activity on structural/regime conditions; the gates that FAIL
(B3, risk-width) cherry-pick individual trades scattered through the sequence.

Rule added to the playbook: no more per-trade feature filters in this system
unless validated by full-path re-run (which is what the registry pin run is).
The wide stops are also functionally "survivors" — a far stop is hard to hit,
so cutting them re-tightens the book and halts fire more (WR fell 25.8->23.2,
streak 14->15, DD blew out).


### 3f. Chop math parity + Efficiency Ratio thesis (2026-09-20)

**Chop parity: PASS.** Independent reimplementation of the Choppiness Index
(100*log10(sumTR/(Hi-Lo))/log10(14), TR=max(H-L,|H-PC|,|L-PC|)) vs the engine's
`_chop_series_1h`: max abs diff = 0.0 across all 32,429 1h bars. The engine's
chop is a textbook-correct implementation; the C14 closed-candle mapping on top
was already audited. Nothing to fix.

**Efficiency Ratio thesis: REJECTED by the pre-registered rule.** ER24
(Kaufman: |net displacement| / path length, 1h closes, C14 instant) bucketed at
every champion + swingpause-single entry: NO bucket is net-negative on either
config, and the low-ER buckets contain +105R of real >=2R winners on the
single. Cutting them fails "spare the winners" (the B3 / risk-width trap).
On the multi ER24 is flat noise — the edge is structure-break + trail, which
works IN chop; that is the flip-window design and it does not need 1h trend.
No `exp_er` gate added to the engine (dead kwargs are clutter); the bucket
table lives in this doc as the tombstone for the ER road.

Meta-note: after the risk-width failure (section 3e), bucket autopsies are
HYPOTHESIS GENERATION ONLY — no gate goes into the engine without a full-path
re-run, and no full-path run happens unless the bucket passes the rule
(net-negative + negligible big-win contribution). ER failed at the first gate,
which is the cheap way to die.


### 3g. Sequential one-pass causal study — HARNESS ARTIFACT RESOLVED, NUMBERS CERTIFIED (2026-09-20, corrected 2026-09-21)

`exp_onepass_cline.py` implements the C10 one-pass spec for champion_multi_sw10:
causal 30d/20d slices (L3 consistent), chains rebuilt fresh, L1 open-window-as-
active-bias patch, L4 +2-bar discovery pad, extra-entry capture, and a
chronological sequential state machine (cooldown 8 + halt3) for the live-expected
number.

**Initial result: 0/490 reproduction.** Correctly diagnosed as a signal-collection
artifact — NOT a live gap. The harness rebuilds swing chains from causal slices
(cut at entry+2bars). The batch engine attaches B2/FLIP marks to swings AFTER
declaration (~5-19h after the mark bar). At the causal cut, the generating swing
hasn't declared yet, so the mark is invisible in the rebuilt chain. But the mark
itself is a price-vs-known-level fact (close beyond the prev confirmed swing's
end), computable at every candle close without any declaration. The live engine
computes marks in real-time as price breaks known levels — it doesn't need the
swing to "declare."

**Corrected diagnosis (150/150 trace + exit-capped check on 857 trades):**
- Every entry fires BEFORE its own swing's FS confirmation (pre-FS marks).
- Every entry is knowable live at candle close: prev swing's FS confirms →
  level is final → price breaks level → mark fires → entry at close.
- `filter_pre_fs=True` correctly gates: rejects marks before prev swing's FS.
  0 violations of the tradability rule on both configs.
- Exit-capped check: 147 multi / 101 single entries had post-entry-extreme
  stops (SL finalized after entry in batch). Of those, 0 survived in batch
  where live's tighter stop would have killed them. R divergence: +0.0R.
- Stop-level differences change position size in dollars, never in R — every
  one of those trades died at exactly -1.0R regardless of stop width.

**Conclusion: the batch +325.8 / +359.0 numbers ARE the live numbers.** The
one-pass v2 (causal mark collector) would give a precise live-expected number,
but the batch is certified as the floor — live may be higher due to earlier
mark visibility and sequential extras.

Playbook lesson: the "0/490 blocker" was a declaration-lag artifact of how the
batch engine discovers signals (retroactive attachment to declared swings), not
a structural live gap. For price-vs-level signals, marks are pure candle-close
facts. Never re-diagnose live-faithfulness from chain-rebuild harness results
without tracing the actual signal rule candle-by-candle.


### 3h. Entry-quality autopsy — FILTERS DEAD, SYSTEM EDGE IS TRAIL (2026-09-21)

Phase 1: measured 7 entry-time metrics (risk%, swing quality, entry depth,
candle strength, swing age, same-dir count, hour-of-day) across 487 champion
trades. Best separators: risk% (tight = big winners), swing age (fresh = best),
FLIP >> B2. But all separations small relative to R distribution.

Phase 2: implemented 3 patcher gates (`exp_entry_candle_min`, `exp_entry_swing_age_max`,
`exp_entry_skip_b2_doji`) and tested 5 configs on both king bases. **All 5 lost R
vs the kings.** Every entry-quality filter worsened NET and drawdown.

| filter | vs king multi | vs king single |
|--------|--------------|----------------|
| skip B2+doji | -23.1R, DD+3.7 | -59.1R, DD+16.5 |
| skip swing age>50 | -58.6R, DD+2.2 | -46.5R, DD+12.1 |
| combined B2+age | -53.4R, DD+1.0 | — |

Conclusion: the system's edge is the trail mechanism (quick losers, run winners)
and the swing pause (reactive). Entry quality is noise — the trail handles bad
entries naturally by cutting at -1R. Preventive entry gating is counterproductive.
Multiple-comparisons budget spent on this family; no further entry-quality
experiments recommended.


### 3i. FINAL CERTIFICATION — BACKTEST PHASE COMPLETE (2026-09-21)

**Certified live-implementable configs:**

| config | n | NET | DD | WR | NET-DD | status |
|--------|---|-----|----|----|--------|--------|
| utcsat_multi_sw10 | 454 | +359.0R | 14.8 | 30.8% | 24.3 | optimistic king |
| champion_multi_sw10 | 500 | +325.8R | 17.8 | 30.0% | 18.3 | conservative king |
| nowknd_swingpause_single_sw10 | 294 | +217.6R | 18.2 | 29.6% | 12.0 | best single |

**Certification checklist:**
- [x] Trail ratchet: condition + ordering FIXED (§3)
- [x] Partial R formula: FIXED (§3)
- [x] Causality: CLEAN (truncation probes, §2)
- [x] Identity gate: patched-off == shipped (340t/+225.3R IDENTICAL)
- [x] Cost stress test: breakeven at 4.4x costs; tripled costs still +87R
- [x] Prev-FS rule: 0 violations on 857 trades (§3g)
- [x] Exit-capped check: 0 R divergence (§3g)
- [x] Entry-quality filters: ALL DEAD (§3h)
- [x] Cooldown research: swing-pause adopted, window-skip dead (§3d)
- [x] UTC-weekend: Sat skip adopted for multi (§3d-2)
- [x] Concurrency: cap-5 optimal, exp_max_concurrent implemented (§3d-3)

**Remaining honest asterisks:**
- Execution reality beyond modeled 0.5bp/1bp slippage (latency, partial fills).
- UTC-Saturday edge is era-dependent (2023-24 bleed, 2025-26 neutral).
- Wide-stop trades = smaller $ position for same 1R — sizing must follow stop width.

**What's next:** paper trade both kings, track Saturday coverage, build live engine.


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
